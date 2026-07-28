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
@allure.feature("额度消费端到端链路")
class TestChatCreditFlow:

    @pytest.mark.e2e
    @pytest.mark.slow
    @pytest.mark.regression
    @allure.story("聊天消费额度")
    @allure.title("购买额度后聊天成功且重复 requestId 不重复扣减")
    @allure.severity(allure.severity_level.BLOCKER)
    def test_chat_consumes_credit_and_duplicate_request_is_idempotent(
            self,
            api_client,
            drawio_agent_id
    ):
        user_id = f"pytest-chat-credit-{uuid4().hex[:8]}"
        order_id = f"{uuid4().int % 10**12:012d}"
        out_trade_no = f"{uuid4().int % 10**12:012d}"
        request_id = f"pytest-chat-{uuid4().hex}"

        with allure.step("购买测试额度"):
            purchase_response = api_client.post(
                "/api/v1/credit/purchase_credit_order",
                json={
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
            )

            assert purchase_response.status_code == 200
            assert purchase_response.json()["code"] == "0000"

        with allure.step("创建聊天会话"):
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

        chat_request = {
            "agentId": drawio_agent_id,
            "userId": user_id,
            "sessionId": session_id,
            "requestId": request_id,
            "message": "请只回复：OK"
        }

        with allure.step("第一次聊天并验证额度扣减"):
            first_chat_response = api_client.post(
                "/api/v1/chat",
                json=chat_request,
                timeout=60
            )

            assert first_chat_response.status_code == 200

            first_chat_result = first_chat_response.json()
            assert first_chat_result["code"] == "0000"
            assert first_chat_result["data"] is not None
            assert first_chat_result["data"]["requestId"] == request_id

            cost_credits = Decimal(str(
                first_chat_result["data"]["costCredits"]
            ))
            first_remaining_credits = Decimal(str(
                first_chat_result["data"]["remainingCredits"]
            ))

            assert cost_credits >= Decimal("1")
            assert first_remaining_credits == (
                Decimal(str(GROUP_BUY_CREDITS)) - cost_credits
            )

            first_account_response = api_client.get(
                f"/api/v1/credit/query_credit_account/{user_id}"
            )
            first_account_result = first_account_response.json()

            assert first_account_result["code"] == "0000"
            assert Decimal(str(
                first_account_result["data"]["availableCredits"]
            )) == first_remaining_credits
            assert Decimal(str(
                first_account_result["data"]["totalUsedCredits"]
            )) == cost_credits

        with allure.step("重复相同 requestId 并验证不重复扣减"):
            duplicate_chat_response = api_client.post(
                "/api/v1/chat",
                json=chat_request,
                timeout=60
            )

            assert duplicate_chat_response.status_code == 200

            duplicate_chat_result = duplicate_chat_response.json()
            assert duplicate_chat_result["code"] == "0000"
            assert duplicate_chat_result["data"] is not None
            assert duplicate_chat_result["data"]["requestId"] == request_id
            assert Decimal(str(
                duplicate_chat_result["data"]["costCredits"]
            )) == cost_credits
            assert Decimal(str(
                duplicate_chat_result["data"]["remainingCredits"]
            )) == first_remaining_credits

            final_account_response = api_client.get(
                f"/api/v1/credit/query_credit_account/{user_id}"
            )
            final_account_result = final_account_response.json()

            assert final_account_result["code"] == "0000"
            assert Decimal(str(
                final_account_result["data"]["availableCredits"]
            )) == first_remaining_credits
            assert Decimal(str(
                final_account_result["data"]["totalUsedCredits"]
            )) == cost_credits

    @pytest.mark.e2e
    @pytest.mark.slow
    @pytest.mark.negative
    @pytest.mark.regression
    @pytest.mark.xfail(
        strict=True,
        reason=(
            "已知缺陷：requestId 未绑定 userId，不同用户复用相同 "
            "requestId 时第二个用户调用模型但不扣额度"
        )
    )
    @allure.story("消费幂等隔离")
    @allure.title("不同用户使用相同 requestId 时应分别扣减各自额度")
    @allure.severity(allure.severity_level.BLOCKER)
    def test_same_request_id_is_isolated_between_users(
            self,
            api_client,
            drawio_agent_id
    ):
        shared_request_id = f"pytest-shared-{uuid4().hex}"
        users = [
            f"pytest-chat-owner-{uuid4().hex[:8]}",
            f"pytest-chat-other-{uuid4().hex[:8]}"
        ]
        sessions = {}

        for user_id in users:
            with allure.step(f"为用户 {user_id} 购买测试额度"):
                purchase_response = api_client.post(
                    "/api/v1/credit/purchase_credit_order",
                    json={
                        "userId": user_id,
                        "teamId": None,
                        "orderId": (
                            f"{uuid4().int % 10**12:012d}"
                        ),
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

            with allure.step(f"为用户 {user_id} 创建会话"):
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
                sessions[user_id] = (
                    session_result["data"]["sessionId"]
                )

        for user_id in users:
            with allure.step(
                f"用户 {user_id} 使用相同 requestId 发起聊天"
            ):
                chat_response = api_client.post(
                    "/api/v1/chat",
                    json={
                        "agentId": drawio_agent_id,
                        "userId": user_id,
                        "sessionId": sessions[user_id],
                        "requestId": shared_request_id,
                        "message": "请只回复：OK"
                    },
                    timeout=60
                )

                assert chat_response.status_code == 200
                chat_result = chat_response.json()
                assert chat_result["code"] == "0000"
                assert chat_result["data"] is not None

        for user_id in users:
            with allure.step(
                f"验证用户 {user_id} 的额度被独立扣减"
            ):
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
