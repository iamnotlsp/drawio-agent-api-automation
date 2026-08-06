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
@allure.feature("AI 多轮对话")
class TestChatContextApi:

    @pytest.mark.e2e
    @pytest.mark.slow
    @pytest.mark.regression
    @pytest.mark.ai_quality
    @allure.story("会话上下文记忆")
    @allure.title("同一会话的第二轮对话应记住第一轮测试代号")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_chat_remembers_previous_turn_context(
            self,
            api_client,
            drawio_agent_id
    ):
        user_id = f"pytest-context-{uuid4().hex[:8]}"
        context_code = f"CTX-{uuid4().hex[:8].upper()}"

        with allure.step("为多轮对话测试用户购买额度"):
            purchase_response = api_client.post(
                "/api/v1/credit/purchase_credit_order",
                json={
                    "userId": user_id,
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

        with allure.step("创建多轮对话会话"):
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

        with allure.step("第一轮告知智能体随机测试代号"):
            first_response = api_client.post(
                "/api/v1/chat",
                json={
                    "agentId": drawio_agent_id,
                    "userId": user_id,
                    "sessionId": session_id,
                    "requestId": f"pytest-context-1-{uuid4().hex}",
                    "message": (
                        "Create a simple two-node Draw.io flowchart "
                        f"for project code {context_code}. The diagram "
                        "title and start node must contain the exact "
                        "project code."
                    )
                },
                timeout=120
            )

            assert first_response.status_code == 200
            first_result = first_response.json()
            assert first_result["code"] == "0000"
            assert first_result["data"]["sessionId"] == session_id
            assert context_code in str(
                first_result["data"]["content"]
            )

        with allure.step("第二轮询问第一轮保存的测试代号"):
            second_response = api_client.post(
                "/api/v1/chat",
                json={
                    "agentId": drawio_agent_id,
                    "userId": user_id,
                    "sessionId": session_id,
                    "requestId": f"pytest-context-2-{uuid4().hex}",
                    "message": (
                        "Modify the previous flowchart by adding an end "
                        "node. Preserve the exact project code from the "
                        "previous turn in the diagram title. Return the "
                        "complete Draw.io diagram."
                    )
                },
                timeout=120
            )

            assert second_response.status_code == 200
            second_result = second_response.json()
            assert second_result["code"] == "0000"
            assert second_result["data"]["sessionId"] == session_id
            assert context_code in str(
                second_result["data"]["content"]
            )

        with allure.step("验证两轮对话的额度消费"):
            first_cost = Decimal(str(
                first_result["data"]["costCredits"]
            ))
            second_cost = Decimal(str(
                second_result["data"]["costCredits"]
            ))
            expected_total_used = first_cost + second_cost

            assert first_cost >= Decimal("1")
            assert second_cost >= Decimal("1")

            account_response = api_client.get(
                f"/api/v1/credit/query_credit_account/{user_id}"
            )

            assert account_response.status_code == 200
            account_result = account_response.json()
            assert account_result["code"] == "0000"
            assert Decimal(str(
                account_result["data"]["totalUsedCredits"]
            )) == expected_total_used
            assert Decimal(str(
                account_result["data"]["availableCredits"]
            )) == (
                Decimal(str(GROUP_BUY_CREDITS))
                - expected_total_used
            )
