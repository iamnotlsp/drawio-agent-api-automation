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
@allure.feature("拼团交易")
class TestMarketOrderApi:

    @pytest.mark.regression
    @allure.story("订单锁定")
    @allure.title("成功锁定并查询拼团订单")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_lock_market_pay_order_success(
            self,
            group_buy_api_client
    ):
        user_id = f"pytest-lock-{uuid4().hex[:8]}"
        out_trade_no = f"{uuid4().int % 10**12:012d}"

        config_response = group_buy_api_client.post(
            "/api/v1/gbm/index/query_group_buy_market_config",
            json={
                "userId": user_id,
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

        lock_response = group_buy_api_client.post(
            "/api/v1/gbm/trade/lock_market_pay_order",
            json={
                "userId": user_id,
                "teamId": None,
                "activityId": activity_id,
                "goodsId": GROUP_BUY_GOODS_ID,
                "source": GROUP_BUY_SOURCE,
                "channel": GROUP_BUY_CHANNEL,
                "outTradeNo": out_trade_no,
                "notifyConfigVO": {
                    "notifyType": "MQ"
                }
            }
        )

        assert lock_response.status_code == 200

        result = lock_response.json()
        lock_created = (
                result.get("code") == "0000"
                and result.get("data") is not None
        )

        try:
            assert result["code"] == "0000"
            assert result["data"] is not None

            order = result["data"]

            assert isinstance(order["orderId"], str)
            assert len(order["orderId"].strip()) > 0
            assert order["tradeOrderStatus"] == 0
            assert order["payPrice"] > 0

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

            assert order_detail["userId"] == user_id
            assert order_detail["outTradeNo"] == out_trade_no
            assert order_detail["orderId"] == order["orderId"]
            assert order_detail["goodsId"] == GROUP_BUY_GOODS_ID
            assert order_detail["tradeOrderStatus"] == 0
            assert order_detail["paid"] is False
            assert order_detail["groupSuccess"] is False
            assert order_detail["quotaGrantable"] is False
        finally:
            if lock_created:
                cancel_response = group_buy_api_client.post(
                    "/api/v1/gbm/trade/cancel_market_pay_order",
                    json={
                        "userId": user_id,
                        "source": GROUP_BUY_SOURCE,
                        "channel": GROUP_BUY_CHANNEL,
                        "outTradeNo": out_trade_no
                    }
                )

                assert cancel_response.status_code == 200

                cancel_result = cancel_response.json()
                assert cancel_result["code"] == "0000"
                assert cancel_result["data"] is not None
                assert cancel_result["data"]["canceled"] is True

    @pytest.mark.regression
    @allure.story("订单结算")
    @allure.title("成功结算拼团订单并更新支付状态")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_settlement_market_pay_order_success(
            self,
            group_buy_api_client
    ):
        user_id = f"pytest-pay-{uuid4().hex[:8]}"
        out_trade_no = f"{uuid4().int % 10**12:012d}"

        config_response = group_buy_api_client.post(
            "/api/v1/gbm/index/query_group_buy_market_config",
            json={
                "userId": user_id,
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

        lock_response = group_buy_api_client.post(
            "/api/v1/gbm/trade/lock_market_pay_order",
            json={
                "userId": user_id,
                "teamId": None,
                "activityId": activity_id,
                "goodsId": GROUP_BUY_GOODS_ID,
                "source": GROUP_BUY_SOURCE,
                "channel": GROUP_BUY_CHANNEL,
                "outTradeNo": out_trade_no,
                "notifyConfigVO": {
                    "notifyType": "MQ"
                }
            }
        )

        assert lock_response.status_code == 200

        lock_result = lock_response.json()
        assert lock_result["code"] == "0000"
        assert lock_result["data"] is not None

        settlement_response = group_buy_api_client.post(
            "/api/v1/gbm/trade/settlement_market_pay_order",
            json={
                "userId": user_id,
                "source": GROUP_BUY_SOURCE,
                "channel": GROUP_BUY_CHANNEL,
                "outTradeNo": out_trade_no,
                "outTradeTime": datetime.now(timezone.utc).isoformat()
            }
        )

        assert settlement_response.status_code == 200

        settlement_result = settlement_response.json()
        assert settlement_result["code"] == "0000"
        assert settlement_result["data"] is not None
        assert settlement_result["data"]["userId"] == user_id
        assert settlement_result["data"]["outTradeNo"] == out_trade_no

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

        assert order_detail["userId"] == user_id
        assert order_detail["outTradeNo"] == out_trade_no
        assert order_detail["goodsId"] == GROUP_BUY_GOODS_ID
        assert order_detail["tradeOrderStatus"] == 1
        assert order_detail["paid"] is True
        assert order_detail["groupSuccess"] is False
        assert order_detail["quotaGrantable"] is False

    @pytest.mark.regression
    @allure.story("重复结算")
    @allure.title("重复支付结算被拒绝且不重复增加拼团完成人数")
    @allure.severity(allure.severity_level.BLOCKER)
    def test_duplicate_settlement_does_not_increment_team_twice(
            self,
            group_buy_api_client
    ):
        user_id = f"pytest-pay-duplicate-{uuid4().hex[:8]}"
        out_trade_no = f"{uuid4().int % 10**12:012d}"

        config_response = group_buy_api_client.post(
            "/api/v1/gbm/index/query_group_buy_market_config",
            json={
                "userId": user_id,
                "source": GROUP_BUY_SOURCE,
                "channel": GROUP_BUY_CHANNEL,
                "goodsId": GROUP_BUY_GOODS_ID
            }
        )

        assert config_response.status_code == 200

        config_result = config_response.json()
        assert config_result["code"] == "0000"
        activity_id = config_result["data"]["activityId"]

        lock_response = group_buy_api_client.post(
            "/api/v1/gbm/trade/lock_market_pay_order",
            json={
                "userId": user_id,
                "teamId": None,
                "activityId": activity_id,
                "goodsId": GROUP_BUY_GOODS_ID,
                "source": GROUP_BUY_SOURCE,
                "channel": GROUP_BUY_CHANNEL,
                "outTradeNo": out_trade_no,
                "notifyConfigVO": {
                    "notifyType": "MQ"
                }
            }
        )

        assert lock_response.status_code == 200
        assert lock_response.json()["code"] == "0000"

        settlement_request = {
            "userId": user_id,
            "source": GROUP_BUY_SOURCE,
            "channel": GROUP_BUY_CHANNEL,
            "outTradeNo": out_trade_no,
            "outTradeTime": datetime.now(timezone.utc).isoformat()
        }

        first_response = group_buy_api_client.post(
            "/api/v1/gbm/trade/settlement_market_pay_order",
            json=settlement_request
        )

        assert first_response.status_code == 200
        assert first_response.json()["code"] == "0000"

        query_request = {
            "userId": user_id,
            "outTradeNo": out_trade_no
        }
        first_query_response = group_buy_api_client.post(
            "/api/v1/gbm/trade/query_market_pay_order",
            json=query_request
        )

        assert first_query_response.status_code == 200

        first_query_result = first_query_response.json()
        assert first_query_result["code"] == "0000"
        first_complete_count = first_query_result[
            "data"
        ]["completeCount"]

        assert first_complete_count == 1
        assert first_query_result["data"]["paid"] is True

        second_response = group_buy_api_client.post(
            "/api/v1/gbm/trade/settlement_market_pay_order",
            json=settlement_request
        )

        assert second_response.status_code == 200

        second_result = second_response.json()
        assert second_result["code"] == "E0104"
        assert second_result["info"] == (
            "不存在的外部交易单号或用户已退单"
        )
        assert second_result["data"] is None

        final_query_response = group_buy_api_client.post(
            "/api/v1/gbm/trade/query_market_pay_order",
            json=query_request
        )

        assert final_query_response.status_code == 200

        final_query_result = final_query_response.json()
        assert final_query_result["code"] == "0000"
        assert final_query_result["data"]["completeCount"] == (
            first_complete_count
        )
        assert final_query_result["data"]["paid"] is True
        assert final_query_result["data"]["groupSuccess"] is False

    @pytest.mark.negative
    @pytest.mark.regression
    @allure.story("订单数据隔离")
    @allure.title("其他用户不能查询或取消本人拼团订单")
    @allure.severity(allure.severity_level.BLOCKER)
    def test_other_user_cannot_query_or_cancel_market_order(
            self,
            group_buy_api_client
    ):
        owner_user_id = f"pytest-owner-{uuid4().hex[:8]}"
        other_user_id = f"pytest-other-{uuid4().hex[:8]}"
        out_trade_no = f"{uuid4().int % 10**12:012d}"

        config_response = group_buy_api_client.post(
            "/api/v1/gbm/index/query_group_buy_market_config",
            json={
                "userId": owner_user_id,
                "source": GROUP_BUY_SOURCE,
                "channel": GROUP_BUY_CHANNEL,
                "goodsId": GROUP_BUY_GOODS_ID
            }
        )

        assert config_response.status_code == 200

        config_result = config_response.json()
        assert config_result["code"] == "0000"
        activity_id = config_result["data"]["activityId"]

        lock_response = group_buy_api_client.post(
            "/api/v1/gbm/trade/lock_market_pay_order",
            json={
                "userId": owner_user_id,
                "teamId": None,
                "activityId": activity_id,
                "goodsId": GROUP_BUY_GOODS_ID,
                "source": GROUP_BUY_SOURCE,
                "channel": GROUP_BUY_CHANNEL,
                "outTradeNo": out_trade_no,
                "notifyConfigVO": {
                    "notifyType": "MQ"
                }
            }
        )

        assert lock_response.status_code == 200
        assert lock_response.json()["code"] == "0000"

        try:
            other_query_response = group_buy_api_client.post(
                "/api/v1/gbm/trade/query_market_pay_order",
                json={
                    "userId": other_user_id,
                    "outTradeNo": out_trade_no
                }
            )

            assert other_query_response.status_code == 200

            other_query_result = other_query_response.json()
            assert other_query_result["code"] == "E0104"
            assert other_query_result["data"] is None

            other_cancel_response = group_buy_api_client.post(
                "/api/v1/gbm/trade/cancel_market_pay_order",
                json={
                    "userId": other_user_id,
                    "source": GROUP_BUY_SOURCE,
                    "channel": GROUP_BUY_CHANNEL,
                    "outTradeNo": out_trade_no
                }
            )

            assert other_cancel_response.status_code == 200

            other_cancel_result = other_cancel_response.json()
            assert other_cancel_result["code"] == "E0104"
            assert other_cancel_result["data"] is None

            owner_query_response = group_buy_api_client.post(
                "/api/v1/gbm/trade/query_market_pay_order",
                json={
                    "userId": owner_user_id,
                    "outTradeNo": out_trade_no
                }
            )

            assert owner_query_response.status_code == 200

            owner_query_result = owner_query_response.json()
            assert owner_query_result["code"] == "0000"
            assert owner_query_result["data"]["userId"] == (
                owner_user_id
            )
            assert owner_query_result["data"][
                "tradeOrderStatus"
            ] == 0
            assert owner_query_result["data"]["paid"] is False
        finally:
            group_buy_api_client.post(
                "/api/v1/gbm/trade/cancel_market_pay_order",
                json={
                    "userId": owner_user_id,
                    "source": GROUP_BUY_SOURCE,
                    "channel": GROUP_BUY_CHANNEL,
                    "outTradeNo": out_trade_no
                }
            )

    @pytest.mark.negative
    @pytest.mark.regression
    @allure.story("订单状态保护")
    @allure.title("已支付拼团订单不能再取消锁单")
    @allure.severity(allure.severity_level.BLOCKER)
    def test_paid_market_order_cannot_be_canceled(
            self,
            group_buy_api_client
    ):
        user_id = f"pytest-paid-cancel-{uuid4().hex[:8]}"
        out_trade_no = f"{uuid4().int % 10**12:012d}"

        config_response = group_buy_api_client.post(
            "/api/v1/gbm/index/query_group_buy_market_config",
            json={
                "userId": user_id,
                "source": GROUP_BUY_SOURCE,
                "channel": GROUP_BUY_CHANNEL,
                "goodsId": GROUP_BUY_GOODS_ID
            }
        )

        assert config_response.status_code == 200

        config_result = config_response.json()
        assert config_result["code"] == "0000"
        activity_id = config_result["data"]["activityId"]

        lock_response = group_buy_api_client.post(
            "/api/v1/gbm/trade/lock_market_pay_order",
            json={
                "userId": user_id,
                "teamId": None,
                "activityId": activity_id,
                "goodsId": GROUP_BUY_GOODS_ID,
                "source": GROUP_BUY_SOURCE,
                "channel": GROUP_BUY_CHANNEL,
                "outTradeNo": out_trade_no,
                "notifyConfigVO": {
                    "notifyType": "MQ"
                }
            }
        )

        assert lock_response.status_code == 200
        assert lock_response.json()["code"] == "0000"

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
        assert settlement_response.json()["code"] == "0000"

        cancel_response = group_buy_api_client.post(
            "/api/v1/gbm/trade/cancel_market_pay_order",
            json={
                "userId": user_id,
                "source": GROUP_BUY_SOURCE,
                "channel": GROUP_BUY_CHANNEL,
                "outTradeNo": out_trade_no
            }
        )

        assert cancel_response.status_code == 200

        cancel_result = cancel_response.json()
        assert cancel_result["code"] == "E0104"
        assert cancel_result["data"] is None

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
        assert query_result["data"]["tradeOrderStatus"] == 1
        assert query_result["data"]["paid"] is True
        assert query_result["data"]["completeCount"] == 1
