from datetime import datetime, timezone
from uuid import uuid4

import allure
import pytest

from testdata import (
    GROUP_BUY_ACTIVITY_ID,
    GROUP_BUY_CHANNEL,
    GROUP_BUY_GOODS_ID,
    GROUP_BUY_SOURCE,
)


@allure.epic("Group Buy Market 接口自动化")
@allure.feature("拼团交易")
class TestMarketOrderApi:

    @pytest.mark.negative
    @pytest.mark.regression
    @pytest.mark.parametrize(
        "missing_field",
        [
            pytest.param("userId", id="missing-user-id"),
            pytest.param("source", id="missing-source"),
            pytest.param("channel", id="missing-channel"),
            pytest.param("goodsId", id="missing-goods-id"),
            pytest.param("activityId", id="missing-activity-id"),
        ]
    )
    @allure.story("订单锁定参数校验")
    @allure.title("缺少锁单必填字段时应返回非法参数")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_lock_market_pay_order_missing_required_field(
            self,
            group_buy_api_client,
            missing_field
    ):
        request_body = {
            "userId": f"pytest-lock-{uuid4().hex[:8]}",
            "teamId": None,
            "activityId": GROUP_BUY_ACTIVITY_ID,
            "goodsId": GROUP_BUY_GOODS_ID,
            "source": GROUP_BUY_SOURCE,
            "channel": GROUP_BUY_CHANNEL,
            "outTradeNo": f"{uuid4().int % 10**12:012d}",
            "notifyConfigVO": {
                "notifyType": "MQ"
            }
        }
        request_body.pop(missing_field)

        response = group_buy_api_client.post(
            "/api/v1/gbm/trade/lock_market_pay_order",
            json=request_body
        )

        assert response.status_code == 200

        result = response.json()
        assert result["code"] == "0002"
        assert result["info"] == "非法参数"
        assert result["data"] is None

    @pytest.mark.negative
    @pytest.mark.regression
    @pytest.mark.parametrize(
        "missing_field",
        [
            pytest.param(
                "outTradeNo",
                id="missing-out-trade-no"
            ),
            pytest.param(
                "notifyConfigVO",
                id="missing-notify-config"
            ),
        ]
    )
    @pytest.mark.xfail(
        strict=True,
        reason=(
            "已知缺陷：锁单缺少 outTradeNo 或 notifyConfigVO 时"
            "返回 0001/未知失败，而不是 0002/非法参数"
        )
    )
    @allure.story("订单锁定参数校验")
    @allure.title("缺少交易号或通知配置时应返回非法参数")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_lock_market_pay_order_missing_trade_or_notify_field(
            self,
            group_buy_api_client,
            missing_field
    ):
        request_body = {
            "userId": f"pytest-lock-{uuid4().hex[:8]}",
            "teamId": None,
            "activityId": GROUP_BUY_ACTIVITY_ID,
            "goodsId": GROUP_BUY_GOODS_ID,
            "source": GROUP_BUY_SOURCE,
            "channel": GROUP_BUY_CHANNEL,
            "outTradeNo": f"{uuid4().int % 10**12:012d}",
            "notifyConfigVO": {
                "notifyType": "MQ"
            }
        }
        request_body.pop(missing_field)

        response = group_buy_api_client.post(
            "/api/v1/gbm/trade/lock_market_pay_order",
            json=request_body
        )

        assert response.status_code == 200

        result = response.json()
        assert result["code"] == "0002"
        assert result["info"] == "非法参数"
        assert result["data"] is None

    @pytest.mark.negative
    @pytest.mark.regression
    @allure.story("订单锁定通知配置")
    @allure.title("HTTP 通知缺少回调地址时应返回非法参数")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_lock_market_pay_order_http_notify_without_url(
            self,
            group_buy_api_client
    ):
        response = group_buy_api_client.post(
            "/api/v1/gbm/trade/lock_market_pay_order",
            json={
                "userId": f"pytest-lock-{uuid4().hex[:8]}",
                "teamId": None,
                "activityId": GROUP_BUY_ACTIVITY_ID,
                "goodsId": GROUP_BUY_GOODS_ID,
                "source": GROUP_BUY_SOURCE,
                "channel": GROUP_BUY_CHANNEL,
                "outTradeNo": f"{uuid4().int % 10**12:012d}",
                "notifyConfigVO": {
                    "notifyType": "HTTP"
                }
            }
        )

        assert response.status_code == 200

        result = response.json()
        assert result["code"] == "0002"
        assert result["info"] == "非法参数"
        assert result["data"] is None

    @pytest.mark.negative
    @pytest.mark.regression
    @pytest.mark.xfail(
        strict=True,
        reason=(
            "已知缺陷：不支持的通知类型未在入口校验，"
            "返回 0001/未知失败，而不是 0002/非法参数"
        )
    )
    @allure.story("订单锁定通知配置")
    @allure.title("不支持的通知类型应返回非法参数")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_lock_market_pay_order_with_unsupported_notify_type(
            self,
            group_buy_api_client
    ):
        response = group_buy_api_client.post(
            "/api/v1/gbm/trade/lock_market_pay_order",
            json={
                "userId": f"pytest-lock-{uuid4().hex[:8]}",
                "teamId": None,
                "activityId": GROUP_BUY_ACTIVITY_ID,
                "goodsId": GROUP_BUY_GOODS_ID,
                "source": GROUP_BUY_SOURCE,
                "channel": GROUP_BUY_CHANNEL,
                "outTradeNo": f"{uuid4().int % 10**12:012d}",
                "notifyConfigVO": {
                    "notifyType": "EMAIL"
                }
            }
        )

        assert response.status_code == 200

        result = response.json()
        assert result["code"] == "0002"
        assert result["info"] == "非法参数"
        assert result["data"] is None

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
    @allure.story("订单锁定幂等")
    @allure.title("相同外部交易号重复锁单应返回同一订单")
    @allure.severity(allure.severity_level.BLOCKER)
    def test_duplicate_lock_returns_same_order_without_reoccupying_team(
            self,
            group_buy_api_client
    ):
        user_id = f"pytest-lock-idempotent-{uuid4().hex[:8]}"
        out_trade_no = f"{uuid4().int % 10**12:012d}"
        request_body = {
            "userId": user_id,
            "teamId": None,
            "activityId": GROUP_BUY_ACTIVITY_ID,
            "goodsId": GROUP_BUY_GOODS_ID,
            "source": GROUP_BUY_SOURCE,
            "channel": GROUP_BUY_CHANNEL,
            "outTradeNo": out_trade_no,
            "notifyConfigVO": {
                "notifyType": "MQ"
            }
        }
        lock_created = False

        try:
            first_response = group_buy_api_client.post(
                "/api/v1/gbm/trade/lock_market_pay_order",
                json=request_body
            )

            assert first_response.status_code == 200

            first_result = first_response.json()
            assert first_result["code"] == "0000"
            assert first_result["data"] is not None
            lock_created = True

            first_order = first_result["data"]

            first_query_response = group_buy_api_client.post(
                "/api/v1/gbm/trade/query_market_pay_order",
                json={
                    "userId": user_id,
                    "outTradeNo": out_trade_no
                }
            )

            assert first_query_response.status_code == 200

            first_query_result = first_query_response.json()
            assert first_query_result["code"] == "0000"
            first_lock_count = first_query_result[
                "data"
            ]["lockCount"]

            second_response = group_buy_api_client.post(
                "/api/v1/gbm/trade/lock_market_pay_order",
                json=request_body
            )

            assert second_response.status_code == 200

            second_result = second_response.json()
            assert second_result["code"] == "0000"
            assert second_result["data"] is not None

            second_order = second_result["data"]
            assert second_order["orderId"] == first_order["orderId"]
            assert second_order["tradeOrderStatus"] == (
                first_order["tradeOrderStatus"]
            )
            assert second_order["payPrice"] == first_order["payPrice"]

            final_query_response = group_buy_api_client.post(
                "/api/v1/gbm/trade/query_market_pay_order",
                json={
                    "userId": user_id,
                    "outTradeNo": out_trade_no
                }
            )

            assert final_query_response.status_code == 200

            final_query_result = final_query_response.json()
            assert final_query_result["code"] == "0000"
            assert final_query_result["data"]["orderId"] == (
                first_order["orderId"]
            )
            assert final_query_result["data"]["lockCount"] == (
                first_lock_count
            )
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
                assert cancel_response.json()["code"] == "0000"

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
