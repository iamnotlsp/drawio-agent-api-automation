from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import allure
import pytest

from helpers.waiters import wait_until
from testdata import (
    GROUP_BUY_CHANNEL,
    GROUP_BUY_CREDITS,
    GROUP_BUY_GOODS_ID,
    GROUP_BUY_GOODS_NAME,
    GROUP_BUY_SOURCE,
)


@pytest.mark.e2e
@pytest.mark.slow
@allure.epic("跨系统端到端测试")
@allure.feature("拼团购买额度")
class TestCreditPurchaseFlow:

    @allure.story("三人拼团到账")
    @allure.title("三人拼团成功后 DrawIOAgent 异步发放额度")
    @allure.severity(allure.severity_level.BLOCKER)
    def test_group_buy_success_grants_credits(
            self,
            api_client,
            drawio_callback_base_url,
            group_buy_api_client
    ):
        users = [
            f"pytest-e2e-{uuid4().hex[:8]}"
            for _ in range(3)
        ]
        out_trade_nos = [
            f"{uuid4().int % 10**12:012d}"
            for _ in range(3)
        ]
        notify_url = (
            f"{drawio_callback_base_url}"
            "/api/v1/credit/grant_group_buy_success"
        )

        config_response = group_buy_api_client.post(
            "/api/v1/gbm/index/query_group_buy_market_config",
            json={
                "userId": users[0],
                "source": GROUP_BUY_SOURCE,
                "channel": GROUP_BUY_CHANNEL,
                "goodsId": GROUP_BUY_GOODS_ID
            }
        )

        assert config_response.status_code == 200

        config_result = config_response.json()
        assert config_result["code"] == "0000"
        assert config_result["data"] is not None

        activity_id = config_result["data"]["activityId"]
        team_id = None
        purchases = []

        # 先锁定三笔订单，并准备 DrawIOAgent 的额度订单。
        # 这样成团回调执行时，下游订单一定已经存在。
        for user_id, out_trade_no in zip(users, out_trade_nos):
            lock_response = group_buy_api_client.post(
                "/api/v1/gbm/trade/lock_market_pay_order",
                json={
                    "userId": user_id,
                    "teamId": team_id,
                    "activityId": activity_id,
                    "goodsId": GROUP_BUY_GOODS_ID,
                    "source": GROUP_BUY_SOURCE,
                    "channel": GROUP_BUY_CHANNEL,
                    "outTradeNo": out_trade_no,
                    "notifyConfigVO": {
                        "notifyType": "HTTP",
                        "notifyUrl": notify_url
                    }
                }
            )

            assert lock_response.status_code == 200

            lock_result = lock_response.json()
            assert lock_result["code"] == "0000"
            assert lock_result["data"] is not None

            lock_data = lock_result["data"]

            query_response = group_buy_api_client.post(
                "/api/v1/gbm/trade/query_market_pay_order",
                json={
                    "userId": user_id,
                    "outTradeNo": out_trade_no
                }
            )

            assert query_response.status_code == 200

            query_result = query_response.json()
            assert query_result["code"] == "0000"
            assert query_result["data"] is not None

            current_team_id = query_result["data"]["teamId"]

            if team_id is None:
                team_id = current_team_id
            else:
                assert current_team_id == team_id

            paid_time = datetime.now(timezone.utc)
            credit_order_response = api_client.post(
                "/api/v1/credit/create_credit_order",
                json={
                    "userId": user_id,
                    "teamId": team_id,
                    "orderId": lock_data["orderId"],
                    "outTradeNo": out_trade_no,
                    "goodsId": GROUP_BUY_GOODS_ID,
                    "goodsName": GROUP_BUY_GOODS_NAME,
                    "credits": GROUP_BUY_CREDITS,
                    "payPrice": lock_data["payPrice"],
                    "status": "WAIT_GROUP",
                    "paidTime": paid_time.replace(
                        tzinfo=None
                    ).isoformat(timespec="milliseconds")
                }
            )

            assert credit_order_response.status_code == 200

            credit_order_result = credit_order_response.json()
            assert credit_order_result["code"] == "0000"
            assert credit_order_result["data"] is True

            purchases.append({
                "userId": user_id,
                "outTradeNo": out_trade_no
            })

        assert team_id is not None

        # 三人依次支付；第三人支付后触发异步成团回调。
        for purchase in purchases:
            settlement_response = group_buy_api_client.post(
                "/api/v1/gbm/trade/settlement_market_pay_order",
                json={
                    "userId": purchase["userId"],
                    "source": GROUP_BUY_SOURCE,
                    "channel": GROUP_BUY_CHANNEL,
                    "outTradeNo": purchase["outTradeNo"],
                    "outTradeTime": datetime.now(
                        timezone.utc
                    ).isoformat()
                }
            )

            assert settlement_response.status_code == 200

            settlement_result = settlement_response.json()
            assert settlement_result["code"] == "0000"
            assert settlement_result["data"] is not None
            assert settlement_result["data"]["teamId"] == team_id

        def fetch_credit_state():
            state = {}

            for purchase in purchases:
                user_id = purchase["userId"]
                out_trade_no = purchase["outTradeNo"]

                order_response = api_client.get(
                    f"/api/v1/credit/query_credit_order/{out_trade_no}"
                )
                account_response = api_client.get(
                    f"/api/v1/credit/query_credit_account/{user_id}"
                )

                state[user_id] = {
                    "orderHttpStatus": order_response.status_code,
                    "order": order_response.json(),
                    "accountHttpStatus": account_response.status_code,
                    "account": account_response.json()
                }

            return state

        def all_credits_granted(state):
            for user_state in state.values():
                order_result = user_state["order"]
                account_result = user_state["account"]

                if (
                        user_state["orderHttpStatus"] != 200
                        or order_result.get("code") != "0000"
                        or order_result.get("data") is None
                        or order_result["data"].get("status")
                        != "CREDIT_GRANTED"
                ):
                    return False

                if (
                        user_state["accountHttpStatus"] != 200
                        or account_result.get("code") != "0000"
                        or account_result.get("data") is None
                ):
                    return False

                available_credits = Decimal(str(
                    account_result["data"]["availableCredits"]
                ))
                if available_credits != Decimal(
                        str(GROUP_BUY_CREDITS)
                ):
                    return False

            return True

        final_state = wait_until(
            fetch_credit_state,
            all_credits_granted,
            timeout=30,
            interval=1,
            description="三人拼团额度到账"
        )

        assert len(final_state) == 3
