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
@allure.feature("身份认证与授权")
class TestAuthorizationApi:

    @pytest.mark.e2e
    @pytest.mark.slow
    @pytest.mark.negative
    @pytest.mark.regression
    @pytest.mark.xfail(
        strict=True,
        reason=(
            "已知缺陷：创建会话和聊天接口没有认证机制，"
            "调用方可伪造 userId 消耗其他用户额度"
        )
    )
    @allure.story("用户身份防伪造")
    @allure.title("未认证调用方不得冒用其他用户身份发起聊天")
    @allure.severity(allure.severity_level.BLOCKER)
    def test_unauthenticated_caller_cannot_spend_other_user_credit(
            self,
            api_client,
            drawio_agent_id,
            request_id
    ):
        victim_user_id = f"pytest-auth-victim-{uuid4().hex[:8]}"

        with allure.step("为测试受害者创建 100 点额度"):
            purchase_response = api_client.post(
                "/api/v1/credit/purchase_credit_order",
                json={
                    "userId": victim_user_id,
                    "teamId": None,
                    "orderId": f"{uuid4().int % 10**12:012d}",
                    "outTradeNo": (
                        f"{uuid4().int % 10**12:012d}"
                    ),
                    "goodsId": GROUP_BUY_GOODS_ID,
                    "goodsName": GROUP_BUY_GOODS_NAME,
                    "credits": GROUP_BUY_CREDITS,
                    "payPrice": 12.9,
                    "status": None,
                    "paidTime": datetime.now().isoformat(
                        timespec="milliseconds"
                    )
                }
            )

            assert purchase_response.status_code == 200
            assert purchase_response.json()["code"] == "0000"

            before_response = api_client.get(
                f"/api/v1/credit/query_credit_account/"
                f"{victim_user_id}"
            )
            assert before_response.status_code == 200
            available_before = Decimal(str(
                before_response.json()["data"]["availableCredits"]
            ))

        with allure.step(
            "不携带 Token，冒用受害者 userId 创建会话"
        ):
            session_response = api_client.post(
                "/api/v1/create_session",
                json={
                    "agentId": drawio_agent_id,
                    "userId": victim_user_id
                }
            )

        chat_response = None

        if session_response.status_code == 200:
            session_result = session_response.json()
            if session_result.get("code") == "0000":
                with allure.step(
                    "继续冒用受害者 userId 发起 AI 对话"
                ):
                    chat_response = api_client.post(
                        "/api/v1/chat",
                        json={
                            "agentId": drawio_agent_id,
                            "userId": victim_user_id,
                            "sessionId": (
                                session_result["data"]["sessionId"]
                            ),
                            "requestId": request_id,
                            "message": "请只回复：OK"
                        },
                        timeout=60
                    )

        with allure.step("验证未认证请求被拒绝且受害者额度不变"):
            after_response = api_client.get(
                f"/api/v1/credit/query_credit_account/"
                f"{victim_user_id}"
            )
            assert after_response.status_code == 200

            available_after = Decimal(str(
                after_response.json()["data"]["availableCredits"]
            ))

            session_rejected = (
                session_response.status_code in (401, 403)
            )
            chat_rejected = (
                chat_response is None
                or chat_response.status_code in (401, 403)
            )

            assert (
                session_rejected
                and chat_rejected
                and available_after == available_before
            ), (
                "未认证身份冒用成功："
                f"session_status={session_response.status_code}, "
                f"chat_status={getattr(chat_response, 'status_code', None)}, "
                f"credits={available_before}->{available_after}"
            )
