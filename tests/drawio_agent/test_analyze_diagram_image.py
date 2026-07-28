from datetime import datetime
from uuid import uuid4

import allure
import pytest

from testdata import (
    GROUP_BUY_CREDITS,
    GROUP_BUY_GOODS_ID,
    GROUP_BUY_GOODS_NAME,
)


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
