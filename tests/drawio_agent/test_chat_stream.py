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
@allure.feature("AI 流式对话")
class TestChatStreamApi:

    @pytest.mark.e2e
    @pytest.mark.slow
    @pytest.mark.negative
    @pytest.mark.regression
    @pytest.mark.xfail(
        strict=True,
        reason=(
            "已知缺陷：chat_stream 未校验可用额度，无额度用户仍会"
            "调用 AI 并收到流式结果"
        )
    )
    @allure.story("流式对话额度校验")
    @allure.title("无额度用户应在调用模型前被流式聊天接口拒绝")
    @allure.severity(allure.severity_level.BLOCKER)
    def test_chat_stream_without_credit_is_rejected(
            self,
            api_client,
            no_credit_chat_context,
            request_id
    ):
        response = api_client.post(
            "/api/v1/chat_stream",
            headers={
                "Accept": "text/event-stream"
            },
            json={
                "agentId": no_credit_chat_context["agent_id"],
                "userId": no_credit_chat_context["user_id"],
                "sessionId": (
                    no_credit_chat_context["session_id"]
                ),
                "requestId": request_id,
                "message": "请只回复：OK"
            },
            timeout=60
        )

        assert response.status_code == 200
        assert "额度不足" in response.text

    @pytest.mark.e2e
    @pytest.mark.slow
    @pytest.mark.regression
    @pytest.mark.xfail(
        strict=True,
        reason=(
            "已知缺陷：chat_stream 完成 AI 调用后未记录消费，"
            "用户额度不会减少"
        )
    )
    @allure.story("流式对话额度消费")
    @allure.title("有额度用户完成流式聊天后应扣减并记录消费额度")
    @allure.severity(allure.severity_level.BLOCKER)
    def test_chat_stream_consumes_credit(
            self,
            api_client,
            drawio_agent_id
    ):
        user_id = f"pytest-stream-credit-{uuid4().hex[:8]}"

        purchase_response = api_client.post(
            "/api/v1/credit/purchase_credit_order",
            json={
                "userId": user_id,
                "teamId": None,
                "orderId": f"{uuid4().int % 10**12:012d}",
                "outTradeNo": f"{uuid4().int % 10**12:012d}",
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

        session_response = api_client.post(
            "/api/v1/create_session",
            json={
                "agentId": drawio_agent_id,
                "userId": user_id
            }
        )

        assert session_response.status_code == 200
        session_result = session_response.json()
        assert session_result["code"] == "0000"
        session_id = session_result["data"]["sessionId"]

        stream_response = api_client.post(
            "/api/v1/chat_stream",
            headers={
                "Accept": "text/event-stream"
            },
            json={
                "agentId": drawio_agent_id,
                "userId": user_id,
                "sessionId": session_id,
                "requestId": f"pytest-stream-{uuid4().hex}",
                "message": "请只回复：OK"
            },
            timeout=60
        )

        assert stream_response.status_code == 200
        assert "text/event-stream" in (
            stream_response.headers.get("Content-Type", "")
        )
        assert stream_response.text.strip()

        account_response = api_client.get(
            f"/api/v1/credit/query_credit_account/{user_id}"
        )

        assert account_response.status_code == 200
        account_result = account_response.json()
        assert account_result["code"] == "0000"

        available_credits = Decimal(str(
            account_result["data"]["availableCredits"]
        ))
        total_used_credits = Decimal(str(
            account_result["data"]["totalUsedCredits"]
        ))

        assert total_used_credits >= Decimal("1")
        assert available_credits == (
            Decimal(str(GROUP_BUY_CREDITS))
            - total_used_credits
        )
