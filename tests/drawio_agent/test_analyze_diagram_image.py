import base64
import struct
import zlib
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


def _build_simple_flowchart_data_url():
    width = 240
    height = 120
    pixels = bytearray([255] * width * height * 3)

    def set_black(x, y):
        offset = (y * width + x) * 3
        pixels[offset:offset + 3] = b"\x00\x00\x00"

    def draw_rectangle(left, top, right, bottom):
        for x in range(left, right + 1):
            set_black(x, top)
            set_black(x, bottom)
        for y in range(top, bottom + 1):
            set_black(left, y)
            set_black(right, y)

    draw_rectangle(15, 35, 85, 85)
    draw_rectangle(155, 35, 225, 85)

    for x in range(86, 155):
        set_black(x, 60)
    for offset in range(10):
        set_black(154 - offset, 60 - offset)
        set_black(154 - offset, 60 + offset)

    raw_rows = b"".join(
        b"\x00" + bytes(
            pixels[y * width * 3:(y + 1) * width * 3]
        )
        for y in range(height)
    )

    def png_chunk(chunk_type, data):
        return (
            struct.pack(">I", len(data))
            + chunk_type
            + data
            + struct.pack(
                ">I",
                zlib.crc32(chunk_type + data) & 0xFFFFFFFF
            )
        )

    png = (
        b"\x89PNG\r\n\x1a\n"
        + png_chunk(
            b"IHDR",
            struct.pack(
                ">IIBBBBB",
                width,
                height,
                8,
                2,
                0,
                0,
                0
            )
        )
        + png_chunk(b"IDAT", zlib.compress(raw_rows))
        + png_chunk(b"IEND", b"")
    )

    encoded = base64.b64encode(png).decode("ascii")
    return f"data:image/png;base64,{encoded}"


@allure.epic("DrawIOAgent 接口自动化")
@allure.feature("图片解析")
class TestAnalyzeDiagramImageApi:

    @pytest.mark.negative
    @pytest.mark.regression
    @allure.story("视觉模型额度校验")
    @allure.title("无额度用户应在解析图片和调用视觉模型前被拒绝")
    @allure.severity(allure.severity_level.BLOCKER)
    def test_analyze_image_without_credit_is_rejected(
            self,
            api_client,
            vision_drawio_agent_id,
            no_credit_user_id,
            request_id
    ):
        response = api_client.post(
            "/api/v1/analyze_diagram_image",
            json={
                "agentId": vision_drawio_agent_id,
                "userId": no_credit_user_id,
                "sessionId": None,
                "requestId": request_id,
                "message": "请分析这张流程图",
                "imageDataUrl": "not-a-valid-image"
            }
        )

        assert response.status_code == 200

        result = response.json()
        assert result["code"] == "0002"
        assert result["info"] == "额度不足，请购买额度后继续使用"
        assert result["data"] is None

    @pytest.mark.e2e
    @pytest.mark.slow
    @pytest.mark.regression
    @allure.story("图片解析额度消费")
    @allure.title("有效流程图解析成功后应扣减并记录额度")
    @allure.severity(allure.severity_level.BLOCKER)
    def test_analyze_valid_image_consumes_credit(
            self,
            api_client,
            vision_drawio_agent_id,
            request_id
    ):
        user_id = f"pytest-image-credit-{uuid4().hex[:8]}"

        with allure.step("为图片解析测试用户购买额度"):
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

        with allure.step("提交有效流程图并调用视觉模型"):
            response = api_client.post(
                "/api/v1/analyze_diagram_image",
                json={
                    "agentId": vision_drawio_agent_id,
                    "userId": user_id,
                    "sessionId": None,
                    "requestId": request_id,
                    "message": "请简要描述图片中的流程关系",
                    "imageDataUrl": (
                        _build_simple_flowchart_data_url()
                    )
                },
                timeout=60
            )

            assert response.status_code == 200

            result = response.json()
            assert result["code"] == "0000"
            assert result["data"] is not None

            data = result["data"]
            assert data["content"]
            assert data["sessionId"]
            assert data["requestId"] == request_id

            cost_credits = Decimal(str(data["costCredits"]))
            remaining_credits = Decimal(str(
                data["remainingCredits"]
            ))

            assert cost_credits >= Decimal("1")
            assert remaining_credits == (
                Decimal(str(GROUP_BUY_CREDITS))
                - cost_credits
            )

        with allure.step("查询账户并验证额度消费已持久化"):
            account_response = api_client.get(
                f"/api/v1/credit/query_credit_account/{user_id}"
            )

            assert account_response.status_code == 200

            account_result = account_response.json()
            assert account_result["code"] == "0000"
            assert Decimal(str(
                account_result["data"]["availableCredits"]
            )) == remaining_credits
            assert Decimal(str(
                account_result["data"]["totalUsedCredits"]
            )) == cost_credits

    @pytest.mark.negative
    @pytest.mark.regression
    @pytest.mark.xfail(
        strict=True,
        reason=(
            "已知缺陷：有额度用户提交非法图片 Data URL 时，"
            "接口返回未知失败 0001，而不是非法参数 0002"
        )
    )
    @allure.story("图片参数校验")
    @allure.title("非法图片 Data URL 应返回明确的非法参数错误")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_analyze_image_with_invalid_data_url_returns_parameter_error(
            self,
            api_client,
            vision_drawio_agent_id,
            request_id
    ):
        user_id = f"pytest-image-invalid-{uuid4().hex[:8]}"

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

        response = api_client.post(
            "/api/v1/analyze_diagram_image",
            json={
                "agentId": vision_drawio_agent_id,
                "userId": user_id,
                "sessionId": None,
                "requestId": request_id,
                "message": "请分析这张流程图",
                "imageDataUrl": "not-a-valid-image"
            }
        )

        assert response.status_code == 200

        result = response.json()
        assert result["code"] == "0002"
        assert result["info"] == "非法参数"
        assert result["data"] is None
