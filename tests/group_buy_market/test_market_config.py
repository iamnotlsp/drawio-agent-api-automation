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

        statistic = data["teamStatistic"]
        assert statistic is not None
        assert statistic["allTeamCount"] >= 0
        assert statistic["allTeamCompleteCount"] >= 0
        assert statistic["allTeamUserCount"] >= 0
        assert (
            statistic["allTeamCompleteCount"]
            <= statistic["allTeamCount"]
        )

        for team in data["teamList"]:
            assert team["teamId"]
            assert team["activityId"] == data["activityId"]
            assert team["targetCount"] > 0
            assert 0 <= team["completeCount"] <= team["targetCount"]
            assert 0 <= team["lockCount"] <= team["targetCount"]
            assert team["validStartTime"]
            assert team["validEndTime"]
            assert team["validTimeCountdown"]

    @pytest.mark.negative
    @pytest.mark.regression
    @pytest.mark.parametrize(
        "missing_field",
        [
            pytest.param("userId", id="missing-user-id"),
            pytest.param("source", id="missing-source"),
            pytest.param("channel", id="missing-channel"),
            pytest.param("goodsId", id="missing-goods-id"),
        ]
    )
    @allure.story("活动查询参数校验")
    @allure.title("缺少活动查询必填字段时应返回非法参数")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_query_market_config_missing_required_field(
            self,
            group_buy_api_client,
            missing_field
    ):
        request_body = {
            "userId": f"pytest-market-{uuid4().hex[:8]}",
            "source": GROUP_BUY_SOURCE,
            "channel": GROUP_BUY_CHANNEL,
            "goodsId": GROUP_BUY_GOODS_ID
        }
        request_body.pop(missing_field)

        response = group_buy_api_client.post(
            "/api/v1/gbm/index/query_group_buy_market_config",
            json=request_body
        )

        assert response.status_code == 200

        result = response.json()
        assert result["code"] == "0002"
        assert result["info"] == "非法参数"
        assert result["data"] is None

    @pytest.mark.negative
    @pytest.mark.regression
    @pytest.mark.xfail(
        strict=True,
        reason=(
            "已知缺陷：无拼团营销配置的 E0002 被控制器统一转换为"
            " 0001/未知失败"
        )
    )
    @allure.story("活动查询业务校验")
    @allure.title("查询不存在的商品时应返回无拼团营销配置")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_query_market_config_with_unknown_goods_id(
            self,
            group_buy_api_client
    ):
        response = group_buy_api_client.post(
            "/api/v1/gbm/index/query_group_buy_market_config",
            json={
                "userId": f"pytest-market-{uuid4().hex[:8]}",
                "source": GROUP_BUY_SOURCE,
                "channel": GROUP_BUY_CHANNEL,
                "goodsId": "goods-not-exist"
            }
        )

        assert response.status_code == 200

        result = response.json()
        assert result["code"] == "E0002"
        assert result["info"] == "无拼团营销配置"
        assert result["data"] is None
