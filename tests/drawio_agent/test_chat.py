from datetime import datetime
from decimal import Decimal
from uuid import uuid4

import allure
import pytest

from testdata import (
    DEFAULT_CHAT_MESSAGE,
    GROUP_BUY_CREDITS,
    GROUP_BUY_GOODS_ID,
    GROUP_BUY_GOODS_NAME,
)


@allure.epic("DrawIOAgent 接口自动化")
@allure.feature("AI 对话")
class TestChatApi:

    @pytest.mark.negative
    @pytest.mark.regression
    @allure.story("额度校验")
    @allure.title("无可用额度时拒绝发起 AI 对话")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_chat_without_credit(
            self,
            api_client,
            no_credit_chat_context,
            request_id
    ):
        agent_id = no_credit_chat_context["agent_id"]
        user_id = no_credit_chat_context["user_id"]
        session_id = no_credit_chat_context["session_id"]

        response = api_client.post(
            "/api/v1/chat",
            json={
                "agentId": agent_id,
                "userId": user_id,
                "sessionId": session_id,
                "requestId": request_id,
                "message": DEFAULT_CHAT_MESSAGE
            },
            timeout=10
        )

        assert response.status_code == 200

        result = response.json()

        assert result["code"] == "0002"
        assert result["info"] == "额度不足，请购买额度后继续使用"
        assert result["data"] is None

    @pytest.mark.negative
    @pytest.mark.regression
    @pytest.mark.parametrize(
        "missing_field",
        [
            pytest.param("userId", id="missing-user-id"),
            pytest.param("agentId", id="missing-agent-id"),
            pytest.param("message", id="missing-message"),
        ]
    )
    @pytest.mark.xfail(
        strict=True,
        reason=(
            "已知缺陷：聊天接口未先校验必填参数，错误请求被额度不足"
            "响应掩盖"
        )
    )
    @allure.story("请求参数校验")
    @allure.title("缺少聊天必填字段时应在调用模型前返回参数错误")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_chat_missing_required_field_is_rejected(
            self,
            api_client,
            no_credit_chat_context,
            request_id,
            missing_field
    ):
        request_body = {
            "agentId": no_credit_chat_context["agent_id"],
            "userId": no_credit_chat_context["user_id"],
            "sessionId": no_credit_chat_context["session_id"],
            "requestId": request_id,
            "message": DEFAULT_CHAT_MESSAGE
        }
        request_body.pop(missing_field)

        response = api_client.post(
            "/api/v1/chat",
            json=request_body,
            timeout=10
        )

        assert response.status_code == 200

        result = response.json()

        assert result["code"] == "0002"
        assert result["data"] is None
        assert result["info"] != "额度不足，请购买额度后继续使用"

    @pytest.mark.e2e
    @pytest.mark.slow
    @pytest.mark.regression
    @allure.story("会话用户隔离")
    @allure.title("其他用户使用已有 sessionId 时不得接入原会话")
    @allure.severity(allure.severity_level.BLOCKER)
    def test_chat_session_is_isolated_between_users(
            self,
            api_client,
            drawio_agent_id,
            request_id
    ):
        owner_user_id = f"pytest-session-owner-{uuid4().hex[:8]}"
        other_user_id = f"pytest-session-other-{uuid4().hex[:8]}"

        with allure.step("用户 A 创建会话"):
            session_response = api_client.post(
                "/api/v1/create_session",
                json={
                    "agentId": drawio_agent_id,
                    "userId": owner_user_id
                }
            )

            assert session_response.status_code == 200
            session_result = session_response.json()
            assert session_result["code"] == "0000"
            owner_session_id = session_result["data"]["sessionId"]

        with allure.step("为用户 B 购买额度"):
            purchase_response = api_client.post(
                "/api/v1/credit/purchase_credit_order",
                json={
                    "userId": other_user_id,
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

        with allure.step("用户 B 携带用户 A 的 sessionId 发起聊天"):
            chat_response = api_client.post(
                "/api/v1/chat",
                json={
                    "agentId": drawio_agent_id,
                    "userId": other_user_id,
                    "sessionId": owner_session_id,
                    "requestId": request_id,
                    "message": "请只回复：OK"
                },
                timeout=60
            )

            assert chat_response.status_code == 200
            chat_result = chat_response.json()
            assert chat_result["code"] == "0000"
            assert chat_result["data"] is not None

            other_session_id = chat_result["data"]["sessionId"]
            cost_credits = Decimal(str(
                chat_result["data"]["costCredits"]
            ))

            assert other_session_id
            assert other_session_id != owner_session_id
            assert cost_credits >= Decimal("1")

        with allure.step("验证消费记录属于用户 B"):
            account_response = api_client.get(
                f"/api/v1/credit/query_credit_account/"
                f"{other_user_id}"
            )

            assert account_response.status_code == 200
            account_result = account_response.json()
            assert account_result["code"] == "0000"
            assert Decimal(str(
                account_result["data"]["totalUsedCredits"]
            )) == cost_credits
