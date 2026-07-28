from datetime import datetime
from decimal import Decimal
from uuid import uuid4

import allure
import pytest

from testdata import (
    GROUP_BUY_CREDITS,
    GROUP_BUY_GOODS_ID,
    GROUP_BUY_GOODS_NAME,
)


@allure.epic("DrawIOAgent 接口自动化")
@allure.feature("普通购买额度")
class TestCreditPurchaseApi:

    @pytest.mark.smoke
    @pytest.mark.regression
    @allure.story("购买额度")
    @allure.title("普通购买成功且重复请求不重复发放额度")
    @allure.severity(allure.severity_level.BLOCKER)
    def test_direct_purchase_success_and_idempotent(
            self,
            api_client
    ):
        user_id = f"pytest-direct-{uuid4().hex[:8]}"
        order_id = f"{uuid4().int % 10**12:012d}"
        out_trade_no = f"{uuid4().int % 10**12:012d}"
        purchase_request = {
            "userId": user_id,
            "teamId": None,
            "orderId": order_id,
            "outTradeNo": out_trade_no,
            "goodsId": GROUP_BUY_GOODS_ID,
            "goodsName": GROUP_BUY_GOODS_NAME,
            "credits": GROUP_BUY_CREDITS,
            "payPrice": 12.9,
            "status": None,
            "paidTime": datetime.now().isoformat(
                timespec="milliseconds"
            )
        }

        first_response = api_client.post(
            "/api/v1/credit/purchase_credit_order",
            json=purchase_request
        )

        assert first_response.status_code == 200

        first_result = first_response.json()
        assert first_result["code"] == "0000"
        assert first_result["data"] is not None
        assert first_result["data"]["userId"] == user_id
        assert first_result["data"]["teamId"] is None
        assert first_result["data"]["orderId"] == order_id
        assert first_result["data"]["outTradeNo"] == out_trade_no
        assert first_result["data"]["status"] == "CREDIT_GRANTED"

        account_response = api_client.get(
            f"/api/v1/credit/query_credit_account/{user_id}"
        )

        assert account_response.status_code == 200

        account_result = account_response.json()
        assert account_result["code"] == "0000"
        assert account_result["data"] is not None

        first_available_credits = Decimal(str(
            account_result["data"]["availableCredits"]
        ))
        first_total_granted_credits = Decimal(str(
            account_result["data"]["totalGrantedCredits"]
        ))
        expected_credits = Decimal(str(GROUP_BUY_CREDITS))

        assert first_available_credits == expected_credits
        assert first_total_granted_credits == expected_credits

        list_response = api_client.get(
            f"/api/v1/credit/query_credit_order_list/{user_id}"
        )

        assert list_response.status_code == 200

        list_result = list_response.json()
        assert list_result["code"] == "0000"
        assert isinstance(list_result["data"], list)

        matched_orders = [
            order
            for order in list_result["data"]
            if order["outTradeNo"] == out_trade_no
        ]

        assert len(matched_orders) == 1
        assert matched_orders[0]["status"] == "CREDIT_GRANTED"

        second_response = api_client.post(
            "/api/v1/credit/purchase_credit_order",
            json=purchase_request
        )

        assert second_response.status_code == 200

        second_result = second_response.json()
        assert second_result["code"] == "0000"
        assert second_result["data"] is not None
        assert second_result["data"]["outTradeNo"] == out_trade_no
        assert second_result["data"]["status"] == "CREDIT_GRANTED"

        final_account_response = api_client.get(
            f"/api/v1/credit/query_credit_account/{user_id}"
        )

        assert final_account_response.status_code == 200

        final_account_result = final_account_response.json()
        assert final_account_result["code"] == "0000"
        assert final_account_result["data"] is not None

        final_available_credits = Decimal(str(
            final_account_result["data"]["availableCredits"]
        ))
        final_total_granted_credits = Decimal(str(
            final_account_result["data"]["totalGrantedCredits"]
        ))

        assert final_available_credits == first_available_credits
        assert final_total_granted_credits == (
            first_total_granted_credits
        )

    @pytest.mark.negative
    @pytest.mark.regression
    @pytest.mark.parametrize(
        "changed_field",
        [
            "userId",
            "credits"
        ],
        ids=[
            "different-user",
            "different-credits"
        ]
    )
    @allure.story("购买幂等校验")
    @allure.title(
        "相同订单号但 {changed_field} 不一致时拒绝重复购买"
    )
    @allure.severity(allure.severity_level.BLOCKER)
    def test_same_out_trade_no_with_different_order_is_rejected(
            self,
            api_client,
            changed_field
    ):
        user_id = f"pytest-direct-conflict-{uuid4().hex[:8]}"
        out_trade_no = f"{uuid4().int % 10**12:012d}"
        purchase_request = {
            "userId": user_id,
            "teamId": None,
            "orderId": f"{uuid4().int % 10**12:012d}",
            "outTradeNo": out_trade_no,
            "goodsId": GROUP_BUY_GOODS_ID,
            "goodsName": GROUP_BUY_GOODS_NAME,
            "credits": GROUP_BUY_CREDITS,
            "payPrice": 12.9,
            "status": None,
            "paidTime": datetime.now().isoformat(
                timespec="milliseconds"
            )
        }

        first_response = api_client.post(
            "/api/v1/credit/purchase_credit_order",
            json=purchase_request
        )

        assert first_response.status_code == 200
        assert first_response.json()["code"] == "0000"

        conflicting_request = purchase_request.copy()
        if changed_field == "userId":
            conflicting_request["userId"] = (
                f"pytest-other-{uuid4().hex[:8]}"
            )
        else:
            conflicting_request["credits"] = (
                GROUP_BUY_CREDITS + 100
            )

        conflict_response = api_client.post(
            "/api/v1/credit/purchase_credit_order",
            json=conflicting_request
        )

        assert conflict_response.status_code == 200

        conflict_result = conflict_response.json()
        assert conflict_result["code"] == "0002"
        assert conflict_result["info"] == (
            "outTradeNo already exists with different credit order"
        )
        assert conflict_result["data"] is None

        account_response = api_client.get(
            f"/api/v1/credit/query_credit_account/{user_id}"
        )

        assert account_response.status_code == 200

        account_result = account_response.json()
        assert account_result["code"] == "0000"
        assert account_result["data"] is not None
        assert Decimal(str(
            account_result["data"]["availableCredits"]
        )) == Decimal(str(GROUP_BUY_CREDITS))
        assert Decimal(str(
            account_result["data"]["totalGrantedCredits"]
        )) == Decimal(str(GROUP_BUY_CREDITS))

    @pytest.mark.negative
    @pytest.mark.regression
    @pytest.mark.parametrize(
        "invalid_credits",
        [
            None,
            0,
            -1
        ],
        ids=[
            "none",
            "zero",
            "negative"
        ]
    )
    @allure.story("购买参数校验")
    @allure.title("额度数量非法时拒绝购买：{invalid_credits}")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_direct_purchase_with_invalid_credits_is_rejected(
            self,
            api_client,
            invalid_credits
    ):
        user_id = f"pytest-invalid-credit-{uuid4().hex[:8]}"
        out_trade_no = f"{uuid4().int % 10**12:012d}"

        response = api_client.post(
            "/api/v1/credit/purchase_credit_order",
            json={
                "userId": user_id,
                "teamId": None,
                "orderId": f"{uuid4().int % 10**12:012d}",
                "outTradeNo": out_trade_no,
                "goodsId": GROUP_BUY_GOODS_ID,
                "goodsName": GROUP_BUY_GOODS_NAME,
                "credits": invalid_credits,
                "payPrice": 12.9,
                "status": None,
                "paidTime": datetime.now().isoformat(
                    timespec="milliseconds"
                )
            }
        )

        assert response.status_code == 200

        result = response.json()
        assert result["code"] == "0002"
        assert result["info"] == "credits must be greater than zero"
        assert result["data"] is None

        order_response = api_client.get(
            f"/api/v1/credit/query_credit_order/{out_trade_no}"
        )
        account_response = api_client.get(
            f"/api/v1/credit/query_credit_account/{user_id}"
        )

        assert order_response.status_code == 200
        assert order_response.json()["code"] == "0000"
        assert order_response.json()["data"] is None

        assert account_response.status_code == 200
        assert account_response.json()["code"] == "0000"
        assert account_response.json()["data"] is None

    @pytest.mark.negative
    @pytest.mark.regression
    @pytest.mark.xfail(
        reason=(
            "已知缺陷：普通购买传入负支付金额时，"
            "接口仍创建订单并发放额度"
        ),
        strict=True
    )
    @allure.story("购买参数校验")
    @allure.title("支付金额为负数时拒绝购买额度")
    @allure.severity(allure.severity_level.BLOCKER)
    def test_direct_purchase_with_negative_price_is_rejected(
            self,
            api_client
    ):
        user_id = f"pytest-negative-price-{uuid4().hex[:8]}"
        out_trade_no = f"{uuid4().int % 10**12:012d}"

        response = api_client.post(
            "/api/v1/credit/purchase_credit_order",
            json={
                "userId": user_id,
                "teamId": None,
                "orderId": f"{uuid4().int % 10**12:012d}",
                "outTradeNo": out_trade_no,
                "goodsId": GROUP_BUY_GOODS_ID,
                "goodsName": GROUP_BUY_GOODS_NAME,
                "credits": GROUP_BUY_CREDITS,
                "payPrice": -0.01,
                "status": None,
                "paidTime": datetime.now().isoformat(
                    timespec="milliseconds"
                )
            }
        )

        assert response.status_code == 200

        result = response.json()
        assert result["code"] == "0002"
        assert result["data"] is None

        order_response = api_client.get(
            f"/api/v1/credit/query_credit_order/{out_trade_no}"
        )
        account_response = api_client.get(
            f"/api/v1/credit/query_credit_account/{user_id}"
        )

        assert order_response.status_code == 200
        assert order_response.json()["data"] is None
        assert account_response.status_code == 200
        assert account_response.json()["data"] is None
