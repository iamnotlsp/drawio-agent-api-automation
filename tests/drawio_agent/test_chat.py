import allure
import pytest

from testdata import DEFAULT_CHAT_MESSAGE


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
