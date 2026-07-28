from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from decimal import Decimal
from threading import Barrier
from uuid import uuid4

import allure
import pytest

from api_client import ApiClient
from testdata import (
    GROUP_BUY_CREDITS,
    GROUP_BUY_GOODS_ID,
    GROUP_BUY_GOODS_NAME,
)


@allure.epic("DrawIOAgent 接口自动化")
@allure.feature("额度发放")
class TestCreditApi:

    @pytest.mark.regression
    @allure.story("通知幂等")
    @allure.title("重复成团通知只发放一次额度")
    @allure.severity(allure.severity_level.BLOCKER)
    def test_duplicate_group_buy_notification_is_idempotent(
            self,
            api_client
    ):
        user_id = f"pytest-credit-{uuid4().hex[:8]}"
        team_id = f"{uuid4().int % 10**8:08d}"
        order_id = f"{uuid4().int % 10**12:012d}"
        out_trade_no = f"{uuid4().int % 10**12:012d}"

        create_response = api_client.post(
            "/api/v1/credit/create_credit_order",
            json={
                "userId": user_id,
                "teamId": team_id,
                "orderId": order_id,
                "outTradeNo": out_trade_no,
                "goodsId": GROUP_BUY_GOODS_ID,
                "goodsName": GROUP_BUY_GOODS_NAME,
                "credits": GROUP_BUY_CREDITS,
                "payPrice": 2.9,
                "status": "WAIT_GROUP",
                "paidTime": datetime.now().isoformat(
                    timespec="milliseconds"
                )
            }
        )

        assert create_response.status_code == 200

        create_result = create_response.json()
        assert create_result["code"] == "0000"
        assert create_result["data"] is True

        notification = {
            "teamId": team_id,
            "outTradeNoList": [out_trade_no]
        }

        first_grant_response = api_client.post(
            "/api/v1/credit/grant_group_buy_success",
            json=notification
        )

        assert first_grant_response.status_code == 200

        first_grant_result = first_grant_response.json()
        assert first_grant_result["code"] == "0000"
        assert first_grant_result["data"] is not None
        assert first_grant_result["data"][
            "grantedOutTradeNoList"
        ] == [out_trade_no]
        assert first_grant_result["data"][
            "skippedOutTradeNoList"
        ] == []
        assert first_grant_result["data"][
            "failedOutTradeNoList"
        ] == []

        first_account_response = api_client.get(
            f"/api/v1/credit/query_credit_account/{user_id}"
        )

        assert first_account_response.status_code == 200

        first_account_result = first_account_response.json()
        assert first_account_result["code"] == "0000"
        assert first_account_result["data"] is not None

        first_available_credits = Decimal(str(
            first_account_result["data"]["availableCredits"]
        ))
        assert first_available_credits == Decimal(
            str(GROUP_BUY_CREDITS)
        )

        second_grant_response = api_client.post(
            "/api/v1/credit/grant_group_buy_success",
            json=notification
        )

        assert second_grant_response.status_code == 200

        second_grant_result = second_grant_response.json()
        assert second_grant_result["code"] == "0000"
        assert second_grant_result["data"] is not None
        assert second_grant_result["data"][
            "grantedOutTradeNoList"
        ] == []
        assert second_grant_result["data"][
            "skippedOutTradeNoList"
        ] == [out_trade_no]
        assert second_grant_result["data"][
            "failedOutTradeNoList"
        ] == []

        second_account_response = api_client.get(
            f"/api/v1/credit/query_credit_account/{user_id}"
        )

        assert second_account_response.status_code == 200

        second_account_result = second_account_response.json()
        assert second_account_result["code"] == "0000"
        assert second_account_result["data"] is not None

        second_available_credits = Decimal(str(
            second_account_result["data"]["availableCredits"]
        ))

        assert second_available_credits == first_available_credits
        assert second_available_credits == Decimal(
            str(GROUP_BUY_CREDITS)
        )

        order_response = api_client.get(
            f"/api/v1/credit/query_credit_order/{out_trade_no}"
        )

        assert order_response.status_code == 200

        order_result = order_response.json()
        assert order_result["code"] == "0000"
        assert order_result["data"] is not None
        assert order_result["data"]["status"] == "CREDIT_GRANTED"

    @pytest.mark.regression
    @allure.story("并发幂等")
    @allure.title("五个并发成团通知只发放一次额度")
    @allure.severity(allure.severity_level.BLOCKER)
    def test_concurrent_duplicate_group_buy_notifications_are_idempotent(
            self,
            api_client,
            base_url
    ):
        user_id = f"pytest-concurrent-{uuid4().hex[:8]}"
        team_id = f"{uuid4().int % 10**8:08d}"
        order_id = f"{uuid4().int % 10**12:012d}"
        out_trade_no = f"{uuid4().int % 10**12:012d}"

        create_response = api_client.post(
            "/api/v1/credit/create_credit_order",
            json={
                "userId": user_id,
                "teamId": team_id,
                "orderId": order_id,
                "outTradeNo": out_trade_no,
                "goodsId": GROUP_BUY_GOODS_ID,
                "goodsName": GROUP_BUY_GOODS_NAME,
                "credits": GROUP_BUY_CREDITS,
                "payPrice": 2.9,
                "status": "WAIT_GROUP",
                "paidTime": datetime.now().isoformat(
                    timespec="milliseconds"
                )
            }
        )

        assert create_response.status_code == 200

        create_result = create_response.json()
        assert create_result["code"] == "0000"
        assert create_result["data"] is True

        notification = {
            "teamId": team_id,
            "outTradeNoList": [out_trade_no]
        }
        concurrent_request_count = 5
        start_barrier = Barrier(concurrent_request_count)

        def send_notification():
            client = ApiClient(
                base_url=base_url,
                timeout=5
            )

            try:
                start_barrier.wait(timeout=10)
                response = client.post(
                    "/api/v1/credit/grant_group_buy_success",
                    json=notification
                )
                return response.status_code, response.json()
            finally:
                client.close()

        with ThreadPoolExecutor(
                max_workers=concurrent_request_count
        ) as executor:
            futures = [
                executor.submit(send_notification)
                for _ in range(concurrent_request_count)
            ]
            concurrent_results = [
                future.result(timeout=15)
                for future in futures
            ]

        for status_code, result in concurrent_results:
            assert status_code == 200
            assert result["code"] == "0000"
            assert result["data"] is not None
            assert result["data"]["failedOutTradeNoList"] == []

            handled_out_trade_nos = (
                result["data"]["grantedOutTradeNoList"]
                + result["data"]["skippedOutTradeNoList"]
            )
            assert out_trade_no in handled_out_trade_nos

        account_response = api_client.get(
            f"/api/v1/credit/query_credit_account/{user_id}"
        )

        assert account_response.status_code == 200

        account_result = account_response.json()
        assert account_result["code"] == "0000"
        assert account_result["data"] is not None

        available_credits = Decimal(str(
            account_result["data"]["availableCredits"]
        ))
        total_granted_credits = Decimal(str(
            account_result["data"]["totalGrantedCredits"]
        ))
        assert available_credits == Decimal(
            str(GROUP_BUY_CREDITS)
        )
        assert total_granted_credits == Decimal(
            str(GROUP_BUY_CREDITS)
        )

        order_response = api_client.get(
            f"/api/v1/credit/query_credit_order/{out_trade_no}"
        )

        assert order_response.status_code == 200

        order_result = order_response.json()
        assert order_result["code"] == "0000"
        assert order_result["data"] is not None
        assert order_result["data"]["status"] == "CREDIT_GRANTED"

    @pytest.mark.negative
    @pytest.mark.xfail(
        reason=(
            "已知缺陷：成团通知的 teamId 与额度订单不一致时，"
            "接口仍会发放额度"
        ),
        strict=True
    )
    @allure.story("通知数据校验")
    @allure.title("成团通知 teamId 与订单不一致时拒绝发放")
    @allure.severity(allure.severity_level.BLOCKER)
    def test_group_buy_notification_with_mismatched_team_id_is_rejected(
            self,
            api_client
    ):
        user_id = f"pytest-team-mismatch-{uuid4().hex[:8]}"
        order_team_id = f"{uuid4().int % 10**8:08d}"
        notification_team_id = f"{uuid4().int % 10**8:08d}"
        order_id = f"{uuid4().int % 10**12:012d}"
        out_trade_no = f"{uuid4().int % 10**12:012d}"

        assert notification_team_id != order_team_id

        create_response = api_client.post(
            "/api/v1/credit/create_credit_order",
            json={
                "userId": user_id,
                "teamId": order_team_id,
                "orderId": order_id,
                "outTradeNo": out_trade_no,
                "goodsId": GROUP_BUY_GOODS_ID,
                "goodsName": GROUP_BUY_GOODS_NAME,
                "credits": GROUP_BUY_CREDITS,
                "payPrice": 2.9,
                "status": "WAIT_GROUP",
                "paidTime": datetime.now().isoformat(
                    timespec="milliseconds"
                )
            }
        )

        assert create_response.status_code == 200

        create_result = create_response.json()
        assert create_result["code"] == "0000"
        assert create_result["data"] is True

        grant_response = api_client.post(
            "/api/v1/credit/grant_group_buy_success",
            json={
                "teamId": notification_team_id,
                "outTradeNoList": [out_trade_no]
            }
        )

        assert grant_response.status_code == 200

        grant_result = grant_response.json()
        assert grant_result["code"] == "0000"
        assert grant_result["data"] is not None
        assert grant_result["data"]["grantedOutTradeNoList"] == []
        assert grant_result["data"]["skippedOutTradeNoList"] == []
        assert grant_result["data"]["failedOutTradeNoList"] == [
            out_trade_no
        ]

        order_response = api_client.get(
            f"/api/v1/credit/query_credit_order/{out_trade_no}"
        )

        assert order_response.status_code == 200

        order_result = order_response.json()
        assert order_result["code"] == "0000"
        assert order_result["data"] is not None
        assert order_result["data"]["status"] == "WAIT_GROUP"

    @pytest.mark.negative
    @allure.story("通知数据校验")
    @allure.title("不存在的订单号进入发放失败列表")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_group_buy_notification_with_unknown_out_trade_no_is_failed(
            self,
            api_client
    ):
        team_id = f"{uuid4().int % 10**8:08d}"
        unknown_out_trade_no = (
            f"unknown-{uuid4().hex}"
        )

        response = api_client.post(
            "/api/v1/credit/grant_group_buy_success",
            json={
                "teamId": team_id,
                "outTradeNoList": [unknown_out_trade_no]
            }
        )

        assert response.status_code == 200

        result = response.json()
        assert result["code"] == "0000"
        assert result["data"] is not None
        assert result["data"]["teamId"] == team_id
        assert result["data"]["grantedOutTradeNoList"] == []
        assert result["data"]["skippedOutTradeNoList"] == []
        assert result["data"]["failedOutTradeNoList"] == [
            unknown_out_trade_no
        ]

    @pytest.mark.negative
    @allure.story("通知数据校验")
    @allure.title("空订单列表通知作为安全空操作处理")
    @allure.severity(allure.severity_level.NORMAL)
    def test_group_buy_notification_with_empty_order_list_is_noop(
            self,
            api_client
    ):
        team_id = f"{uuid4().int % 10**8:08d}"

        response = api_client.post(
            "/api/v1/credit/grant_group_buy_success",
            json={
                "teamId": team_id,
                "outTradeNoList": []
            }
        )

        assert response.status_code == 200

        result = response.json()
        assert result["code"] == "0000"
        assert result["data"] is not None
        assert result["data"]["teamId"] == team_id
        assert result["data"]["grantedOutTradeNoList"] == []
        assert result["data"]["skippedOutTradeNoList"] == []
        assert result["data"]["failedOutTradeNoList"] == []
