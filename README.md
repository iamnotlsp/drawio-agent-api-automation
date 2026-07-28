# DrawIOAgent API Automation

基于 `pytest + requests + JSON Schema + Allure` 搭建的接口自动化测试项目，
覆盖 DrawIOAgent、group-buy-market 以及“拼团购买额度”的跨系统业务链路。

## 测试结果

最近一次本地全量回归：

| 指标 | 结果 |
|---|---:|
| 收集用例 | 30 |
| 通过 | 22 |
| 已知缺陷（xfail） | 8 |
| 非预期失败 | 0 |
| Allure 请求/响应及日志附件 | 290 |

> 8 个 xfail 来自 5 个已确认缺陷，其中“无效智能体 ID”使用了 2 组参数化数据，“聊天必填参数校验”使用了 3 组参数化数据。

Allure 在线报告发布到 GitHub Pages 后，可从仓库主页的 Pages 地址访问。
本地报告入口为 `docs/index.html`。

## 覆盖范围

### DrawIOAgent

- 查询智能体配置并进行 JSON Schema 契约校验
- 使用有效/无效智能体 ID 创建会话
- 无额度用户发起对话
- 聊天 userId、agentId、message 必填参数校验
- 购买额度后发起 AI 对话并校验消费额度
- 相同 requestId 重复聊天时额度扣减幂等
- 拼团成功额度发放
- 普通购买额度与重复购买幂等
- 同一订单号的用户、额度冲突校验
- 非法额度数量和支付金额边界
- 用户额度订单列表查询
- 顺序重复通知幂等
- 5 个并发重复通知幂等
- 未知订单号、空订单列表、teamId 不一致等异常通知

### group-buy-market

- 查询拼团活动和商品价格关系
- 锁定、查询、取消拼团订单
- 支付结算及状态校验
- 重复结算不重复增加拼团人数
- 订单查询、取消的用户数据隔离
- 已支付订单不可取消
- 三名用户依次支付并完成拼团

### 跨系统 E2E

```text
查询活动
  → 三名用户锁单
  → DrawIOAgent 创建 WAIT_GROUP 额度订单
  → 三名用户依次支付
  → 拼团系统异步回调
  → 轮询订单与账户
  → 三名用户额度全部到账
```

```text
普通购买额度
  → 创建 AI 会话
  → 发起聊天
  → 校验额度扣减
  → 使用相同 requestId 重复聊天
  → 校验账户额度不再减少
```

## 已发现问题

| 编号 | 问题 | 当前处理 |
|---|---|---|
| BUG-001 | 无效 agentId 返回 `0001/未知失败`，未返回约定的 `E0001` | `xfail(strict=True)` |
| BUG-002 | 成团通知的 teamId 与额度订单不一致时仍然发放额度 | `xfail(strict=True)` |
| BUG-003 | 普通购买传入负支付金额时仍创建订单并发放额度 | `xfail(strict=True)` |
| BUG-004 | requestId 未绑定 userId，不同用户复用相同 requestId 时第二个用户调用模型但不扣额度 | `xfail(strict=True)` |
| BUG-005 | 聊天缺少必填参数时未返回参数错误，而是被“额度不足”响应掩盖 | `xfail(strict=True)` 参数化覆盖 3 个字段 |
| OPT-001 | 并发重复通知被唯一索引挡住后，部分响应仍显示在 `grantedOutTradeNoList` | 保留数据层幂等断言并记录待优化 |
| OPT-002 | 相同 requestId 的重复聊天不会重复扣额度，但仍会再次调用 AI 模型 | 额度幂等已验证，建议在模型调用前判断 requestId |

## 项目结构

```text
DrawIOAgentApiTest/
├── api_client.py              # HTTP 客户端、日志、脱敏、Allure 附件
├── conftest.py                # pytest 参数和 fixture
├── schemas.py                 # JSON Schema 契约
├── testdata.py                # 公共测试数据
├── tests/
│   ├── drawio_agent/          # DrawIOAgent 接口测试
│   ├── group_buy_market/      # 拼团系统接口测试
│   └── e2e/                   # 跨系统端到端测试
├── scripts/
│   └── run_allure.ps1         # 一键回归并生成报告
├── requirements.txt
└── pytest.ini
```

## 环境准备

- Python 3.13
- DrawIOAgent：默认 `http://127.0.0.1:8091`
- group-buy-market：默认 `http://127.0.0.1:8092`
- Java 运行环境（Allure Commandline 使用）
- Allure Commandline

安装 Python 依赖：

```powershell
python -m pip install -r requirements.txt
```

安装 Allure Commandline：

```powershell
npm install --global allure-commandline
```

## 执行测试

执行全量测试：

```powershell
python -m pytest -v
```

执行冒烟测试：

```powershell
python -m pytest -m smoke -v
```

指定测试环境：

```powershell
python -m pytest `
  --base-url http://127.0.0.1:8091 `
  --group-buy-base-url http://127.0.0.1:8092
```

生成 Allure 报告：

```powershell
.\scripts\run_allure.ps1
```

本地临时查看：

```powershell
allure open docs
```

## 发布 GitHub Pages

仓库内的 `.github/workflows/deploy-pages.yml` 会在 `docs/` 更新并推送到
`main` 分支后发布 Allure 静态报告。

首次发布时，在 GitHub 仓库中进入：

```text
Settings → Pages → Build and deployment → Source → GitHub Actions
```

然后在 `Actions` 页面运行 `Deploy Allure Report`，或再次推送 `docs/` 变更。

由于测试服务运行在本机 `8091/8092`，GitHub 托管运行器无法直接访问，
因此当前流程是在真实本地测试环境执行回归，再由 GitHub Actions 部署已经生成的
静态报告。后续具备独立测试环境或自托管 Runner 后，可以将测试执行也迁入 CI。

## 技术特点

- fixture 管理客户端、环境地址和业务前置数据
- marker 区分 smoke、regression、negative、e2e、slow
- 参数化覆盖多组异常输入
- xfail 记录已知缺陷，`strict=True` 防止修复后被静默忽略
- JSON Schema 校验响应契约
- `Decimal` 避免金额浮点精度问题
- `ThreadPoolExecutor + Barrier` 模拟并发重复通知
- 轮询等待异步额度到账，设置超时防止无限等待
- 自动脱敏并向 Allure 附加请求、响应、耗时和运行环境
