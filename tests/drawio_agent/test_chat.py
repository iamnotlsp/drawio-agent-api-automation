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
