from datetime import datetime, timezone
from uuid import uuid4

import allure
import pytest

from testdata import (
    GROUP_BUY_CHANNEL,
    GROUP_BUY_GOODS_ID,
    GROUP_BUY_SOURCE,
)


@allure.epic("Group Buy Market 接口自动化")
@allure.feature("拼团成团")
class TestGroupSuccessApi:

    @pytest.mark.regression
    @allure.story("三人成团")
    @allure.title("三名用户支付后拼团状态变为成功")
    @allure.severity(allure.severity_level.BLOCKER)
    def test_group_buy_success_after_three_users_paid(
            self,
            group_buy_api_client
    ):
        users = [
            f"pytest-team-{uuid4().hex[:8]}"
            for _ in range(3)
        ]
        out_trade_nos = [
            f"{uuid4().int % 10**12:012d}"
            for _ in range(3)
        ]

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
        paid_orders = []

        for index, (user_id, out_trade_no) in enumerate(
                zip(users, out_trade_nos),
                start=1
        ):
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
                        "notifyUrl": (
                            "http://127.0.0.1:8092"
                            "/api/v1/test/group_buy_notify"
                        )
                    }
                }
            )

            assert lock_response.status_code == 200

            lock_result = lock_response.json()
            assert lock_result["code"] == "0000"
            assert lock_result["data"] is not None
            assert lock_result["data"]["tradeOrderStatus"] == 0

            settlement_response = group_buy_api_client.post(
                "/api/v1/gbm/trade/settlement_market_pay_order",
                json={
                    "userId": user_id,
                    "source": GROUP_BUY_SOURCE,
                    "channel": GROUP_BUY_CHANNEL,
                    "outTradeNo": out_trade_no,
                    "outTradeTime": datetime.now(
                        timezone.utc
                    ).isoformat()
                }
            )

            assert settlement_response.status_code == 200

            settlement_result = settlement_response.json()
            assert settlement_result["code"] == "0000"
            assert settlement_result["data"] is not None

            current_team_id = settlement_result["data"]["teamId"]

            if team_id is None:
                team_id = current_team_id
            else:
                assert current_team_id == team_id

            paid_orders.append({
                "userId": user_id,
                "outTradeNo": out_trade_no
            })

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

            order_detail = query_result["data"]
            expected_success = index == 3

            assert order_detail["teamId"] == team_id
            assert order_detail["targetCount"] == 3
            assert order_detail["completeCount"] == index
            assert order_detail["paid"] is True
            assert order_detail["groupSuccess"] is expected_success
            assert order_detail["quotaGrantable"] is expected_success

        assert team_id is not None

        for paid_order in paid_orders:
            query_response = group_buy_api_client.post(
                "/api/v1/gbm/trade/query_market_pay_order",
                json=paid_order
            )

            assert query_response.status_code == 200

            query_result = query_response.json()
            assert query_result["code"] == "0000"
            assert query_result["data"] is not None

            order_detail = query_result["data"]

            assert order_detail["teamId"] == team_id
            assert order_detail["completeCount"] == 3
            assert order_detail["paid"] is True
            assert order_detail["groupSuccess"] is True
            assert order_detail["quotaGrantable"] is True
