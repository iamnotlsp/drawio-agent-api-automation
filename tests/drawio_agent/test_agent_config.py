import allure
import pytest

from jsonschema import validate

from schemas import AGENT_CONFIG_RESPONSE_SCHEMA


@pytest.mark.smoke
@pytest.mark.regression
@allure.epic("DrawIOAgent 接口自动化")
@allure.feature("智能体配置")
@allure.story("查询智能体列表")
@allure.title("成功查询智能体配置列表")
@allure.severity(allure.severity_level.CRITICAL)
def test_query_agent_config_success(api_client):
    response = api_client.get(
        "/api/v1/query_ai_agent_config_list"
    )

    assert response.status_code == 200

    result = response.json()

    validate(
        instance=result,
        schema=AGENT_CONFIG_RESPONSE_SCHEMA
    )

    assert result["code"] == "0000"
    assert result["info"] == "成功"
    assert isinstance(result["data"], list)
    assert len(result["data"]) > 0

    agents = {
        agent["agentId"]: agent
        for agent in result["data"]
    }

    assert "300000" in agents
    assert "300001" in agents

    assert agents["300000"]["agentName"] == "drawIoAgent"
    assert agents["300000"]["agentDesc"] == "Draw.io diagram assistant"

    assert agents["300001"]["agentName"] == "visionDrawIoAgent"
