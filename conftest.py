import platform
from importlib.metadata import version
from pathlib import Path
from uuid import uuid4

import pytest

from api_client import ApiClient
from testdata import NO_CREDIT_USER_PREFIX


def pytest_addoption(parser):
    parser.addoption(
        "--base-url",
        action="store",
        default="http://127.0.0.1:8091",
        help="DrawIOAgent 服务的基础地址"
    )
    parser.addoption(
        "--group-buy-base-url",
        action="store",
        default="http://127.0.0.1:8092",
        help="拼团服务基础地址"
    )
    parser.addoption(
        "--drawio-callback-base-url",
        action="store",
        default=None,
        help="拼团服务回调 DrawIOAgent 时使用的内部地址"
    )


def pytest_sessionfinish(session, exitstatus):
    report_dir = getattr(
        session.config.option,
        "allure_report_dir",
        None
    )
    if not report_dir:
        return

    result_dir = Path(report_dir)
    result_dir.mkdir(parents=True, exist_ok=True)

    properties = {
        "Project": "DrawIOAgent API Automation",
        "Python": platform.python_version(),
        "Pytest": version("pytest"),
        "Operating System": platform.platform(),
        "DrawIOAgent Base URL": session.config.getoption(
            "--base-url"
        ),
        "Group Buy Base URL": session.config.getoption(
            "--group-buy-base-url"
        ),
        "DrawIOAgent Callback Base URL": (
            session.config.getoption("--drawio-callback-base-url")
            or session.config.getoption("--base-url")
        ),
        "Exit Status": exitstatus
    }

    content = "\n".join(
        f"{key}={value}"
        for key, value in properties.items()
    )
    (result_dir / "environment.properties").write_text(
        content,
        encoding="utf-8"
    )


@pytest.fixture(scope="session")
def group_buy_base_url(pytestconfig):
    url = pytestconfig.getoption("--group-buy-base-url")
    return url.rstrip("/")


@pytest.fixture(scope="session")
def group_buy_api_client(group_buy_base_url):
    client = ApiClient(
        base_url=group_buy_base_url,
        timeout=5
    )

    yield client
    client.close()


@pytest.fixture(scope="session")
def base_url(pytestconfig):
    url = pytestconfig.getoption("--base-url")
    return url.rstrip("/")


@pytest.fixture(scope="session")
def drawio_callback_base_url(pytestconfig, base_url):
    url = pytestconfig.getoption("--drawio-callback-base-url")
    return (url or base_url).rstrip("/")


@pytest.fixture(scope="session")
def api_client(base_url):
    client = ApiClient(
        base_url=base_url,
        timeout=5
    )

    yield client

    client.close()


@pytest.fixture(scope="session")
def drawio_agent_id(api_client):
    return _query_agent_id(api_client, "drawIoAgent")


@pytest.fixture(scope="session")
def vision_drawio_agent_id(api_client):
    return _query_agent_id(api_client, "visionDrawIoAgent")


def _query_agent_id(api_client, agent_name):
    response = api_client.get(
        "/api/v1/query_ai_agent_config_list"
    )

    assert response.status_code == 200

    result = response.json()
    assert result["code"] == "0000"

    matched_agent = None

    for agent in result["data"]:
        if agent["agentName"] == agent_name:
            matched_agent = agent
            break

    assert matched_agent is not None

    return matched_agent["agentId"]


@pytest.fixture
def no_credit_chat_context(
    api_client,
    drawio_agent_id,
    no_credit_user_id
):
    response = api_client.post(
        "/api/v1/create_session",
        json={
            "agentId": drawio_agent_id,
            "userId": no_credit_user_id
        }
    )

    assert response.status_code == 200

    result = response.json()

    assert result["code"] == "0000"
    assert result["data"] is not None

    session_id = result["data"]["sessionId"]

    return {
        "agent_id": drawio_agent_id,
        "user_id": no_credit_user_id,
        "session_id": session_id
    }


@pytest.fixture
def no_credit_user_id():
    return (
        f"{NO_CREDIT_USER_PREFIX}-"
        f"{uuid4().hex[:8]}"
    )


@pytest.fixture
def request_id():
    return f"pytest-{uuid4().hex}"
