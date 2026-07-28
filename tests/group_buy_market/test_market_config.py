from decimal import Decimal
from uuid import uuid4

import allure
import pytest

from testdata import (
    GROUP_BUY_ACTIVITY_ID,
    GROUP_BUY_CHANNEL,
    GROUP_BUY_GOODS_ID,
    GROUP_BUY_SOURCE,
)


@allure.epic("Group Buy Market 接口自动化")
@allure.feature("拼团活动")
class TestMarketConfigApi:

    @pytest.mark.smoke
    @pytest.mark.regression
    @allure.story("活动配置")
    @allure.title("成功查询商品的有效拼团活动")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_query_group_buy_market_config_success(
            self,
            group_buy_api_client
    ):
        user_id = f"pytest-market-{uuid4().hex[:8]}"

        response = group_buy_api_client.post(
            "/api/v1/gbm/index/query_group_buy_market_config",
            json={
                "userId": user_id,
                "source": GROUP_BUY_SOURCE,
                "channel": GROUP_BUY_CHANNEL,
                "goodsId": GROUP_BUY_GOODS_ID
            }
        )

        assert response.status_code == 200

        result = response.json()

        assert result["code"] == "0000"
        assert result["info"] == "成功"
        assert result["data"] is not None

        data = result["data"]

        assert data["activityId"] == GROUP_BUY_ACTIVITY_ID
        assert data["goods"]["goodsId"] == GROUP_BUY_GOODS_ID

        goods = data["goods"]
        original_price = Decimal(str(goods["originalPrice"]))
        deduction_price = Decimal(str(goods["deductionPrice"]))
        pay_price = Decimal(str(goods["payPrice"]))

        assert original_price > 0
        assert deduction_price >= 0
        assert pay_price >= 0
        assert pay_price == original_price - deduction_price
        assert pay_price < original_price
        assert isinstance(data["teamList"], list)
