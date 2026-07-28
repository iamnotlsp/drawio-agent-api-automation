import allure
import pytest
from jsonschema import validate
from uuid import UUID

from schemas import CREATE_SESSION_RESPONSE_SCHEMA
from testdata import DEFAULT_USER_ID, INVALID_AGENT_IDS


@pytest.mark.smoke
@pytest.mark.regression
@allure.epic("DrawIOAgent 接口自动化")
@allure.feature("会话管理")
@allure.story("创建会话")
@allure.title("使用有效智能体成功创建会话")
@allure.severity(allure.severity_level.CRITICAL)
def test_create_session_success(api_client, drawio_agent_id):
    response = api_client.post(
        "/api/v1/create_session",
        json={
            "agentId": drawio_agent_id,
            "userId": DEFAULT_USER_ID
        }
    )

    assert response.status_code == 200

    result = response.json()

    assert result["code"] == "0000"
    assert result["info"] == "成功"
    assert result["data"] is not None
    assert "sessionId" in result["data"]

    session_id = result["data"]["sessionId"]

    assert isinstance(session_id, str)
    assert len(session_id.strip()) > 0

    parsed_session_id = UUID(session_id)

    assert str(parsed_session_id) == session_id.lower()


@pytest.mark.negative
@pytest.mark.regression
@pytest.mark.parametrize(
    "invalid_agent_id",
    INVALID_AGENT_IDS
)
@pytest.mark.xfail(
    reason="已知缺陷：无效 agentId 被返回为 0001，而不是 E0001",
    strict=True
)
@allure.epic("DrawIOAgent 接口自动化")
@allure.feature("会话管理")
@allure.story("创建会话异常校验")
@allure.title("使用无效智能体 ID 创建会话：{invalid_agent_id}")
@allure.severity(allure.severity_level.NORMAL)
def test_create_session_with_invalid_agent_id(
    api_client,
    invalid_agent_id
):
    response = api_client.post(
        "/api/v1/create_session",
        json={
            "agentId": invalid_agent_id,
            "userId": "pytest-user-001"
        }
    )

    assert response.status_code == 200

    result = response.json()

    validate(
        instance=result,
        schema=CREATE_SESSION_RESPONSE_SCHEMA
    )

    assert result["code"] == "E0001"
    assert result["info"] == "智能体ID不存在"
    assert result["data"] is None
