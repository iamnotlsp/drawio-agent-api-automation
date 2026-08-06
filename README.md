# DrawIOAgent API Automation

基于 `pytest + requests + JSON Schema + Allure + Docker Compose + GitHub Actions`
搭建的接口自动化测试项目，覆盖 DrawIOAgent、group-buy-market 以及
“拼团购买额度”的跨系统业务链路。

项目使用 Windows self-hosted runner 在本机自动完成 Java 构建、测试环境创建、
接口回归、Allure 报告生成、环境清理和 GitHub Pages 发布。

[![API Regression](https://github.com/iamnotlsp/drawio-agent-api-automation/actions/workflows/api-regression-self-hosted.yml/badge.svg)](https://github.com/iamnotlsp/drawio-agent-api-automation/actions/workflows/api-regression-self-hosted.yml)

[在线查看 Allure 测试报告](https://iamnotlsp.github.io/drawio-agent-api-automation/)

## 测试结果

最近一次 GitHub Actions 全量回归：

| 指标 | 结果 |
|---|---:|
| 测试套件用例 | 61 |
| CI 执行用例 | 60 |
| 通过 | 39 |
| 预期失败（xfail） | 21 |
| 非预期失败 | 0 |
| AI 质量手动评测 | 1 |
| 执行耗时 | 3 分 1 秒 |
| Allure 请求/响应及日志附件 | 452 |

> 21 个 xfail 包含 14 类已确认缺陷对应的 20 个用例，以及
> 1 个 Demo 身份认证设计边界用例。

> 多轮对话上下文效果依赖真实大模型输出及响应时间，已标记为 `ai_quality`，
> 保留为手动效果评测，不作为稳定 CI 回归的阻断条件。

Allure 在线报告已发布到 GitHub Pages，可通过上方链接直接访问。
本地报告入口为 `docs/index.html`。

## 覆盖范围

### DrawIOAgent

- 查询智能体配置并进行 JSON Schema 契约校验
- 使用有效/无效智能体 ID 创建会话
- 无额度用户发起对话
- 聊天 userId、agentId、message 必填参数校验
- 购买额度后发起 AI 对话并校验消费额度
- 相同 requestId 重复聊天时额度扣减幂等
- sessionId 失效时自动重建会话并正常扣减额度
- 跨用户复用 sessionId 时自动创建独立会话，避免接入他人上下文
- 同一 sessionId 下的多轮对话上下文效果评测（`ai_quality` 手动执行）
- 流式聊天的无额度拦截与消费记账
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
| BUG-006 | chat_stream 未校验可用额度，无额度用户仍可调用 AI | `xfail(strict=True)` |
| BUG-007 | chat_stream 调用完成后未记录消费，用户额度不会减少 | `xfail(strict=True)` |
| BUG-008 | 图片 Data URL 非法时返回 `0001/未知失败`，未返回明确的非法参数错误 | `xfail(strict=True)` |
| BUG-009 | 图片解析 requestId 未绑定 userId，不同用户复用时第二个用户调用视觉模型但不扣额度 | `xfail(strict=True)` |
| BUG-010 | 拼团商品、来源或渠道无活动配置时，`E0002/无拼团营销配置` 被控制器转换为 `0001/未知失败` | `xfail(strict=True)` 参数化覆盖 3 个场景 |
| BUG-011 | 拼团锁单缺少 `outTradeNo` 或 `notifyConfigVO` 时未在入口校验，返回 `0001/未知失败` | `xfail(strict=True)` 参数化覆盖 2 个字段 |
| BUG-012 | 拼团锁单传入不支持的通知类型时未在入口校验，返回 `0001/未知失败` | `xfail(strict=True)` |
| BUG-013 | 拼团锁单未校验 `activityId` 与 `goodsId` 的绑定关系，可套用其他商品活动并产生负折扣金额 | `xfail(strict=True)`，用例自动取消异常订单 |
| BUG-014 | 加入已有拼团队伍时未校验 `teamId` 所属活动，同一队伍可混入其他活动、商品和价格的订单 | `xfail(strict=True)`，用例自动取消两笔订单 |
| LIMIT-001 | Demo 暂未接入身份认证，调用方可以直接传入 userId | 作为生产化改造项，不计为当前 Demo 阻断缺陷 |
| OPT-001 | 并发重复通知被唯一索引挡住后，部分响应仍显示在 `grantedOutTradeNoList` | 保留数据层幂等断言并记录待优化 |
| OPT-002 | 相同 requestId 的重复聊天不会重复扣额度，但仍会再次调用 AI 模型 | 额度幂等已验证，建议在模型调用前判断 requestId |
| OPT-003 | 相同 requestId 的重复图片解析不会重复扣额度，但仍会再次调用视觉模型 | 额度幂等已验证，建议缓存首次结果或在模型调用前判断 requestId |
| RISK-001 | 拼团订单表未对 `out_trade_no` 建立唯一索引，并发重复锁单可能绕过先查后写的幂等判断 | 待独立可重置测试库或增加唯一约束后执行并发验证 |

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
├── docker-compose.test.yml     # 隔离的跨系统测试环境
├── .github/workflows/
│   └── api-regression-self-hosted.yml
├── requirements.txt
└── pytest.ini
```

## 环境准备

- Python 3.13
- Maven 与 Java 8/17 项目构建环境
- Docker Desktop 与 Docker Compose
- Allure Commandline
- GitHub Actions Windows self-hosted runner

本机项目目录（可通过工作流环境变量调整）：

```text
E:/javaProject/DrawIOAgent
E:/javaProject/group-buy-market
```

GitHub Actions 需要配置仓库 Secret：

```text
DASHSCOPE_API_KEY
```

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

执行稳定回归（排除真实模型效果评测）：

```powershell
python -m pytest -m "not ai_quality" -v
```

单独执行 AI 多轮对话效果评测：

```powershell
python -m pytest -m ai_quality -v -s
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

### 使用 Docker Compose 执行跨系统回归

Docker 环境使用宿主机端口 `18091/18092`，容器间 HTTP 回调使用
Compose 服务名 `drawio-agent:8091`：

```powershell
docker compose -f docker-compose.test.yml up -d --build

python -m pytest `
  --base-url http://127.0.0.1:18091 `
  --group-buy-base-url http://127.0.0.1:18092 `
  --drawio-callback-base-url http://drawio-agent:8091 `
  -m "not ai_quality" `
  -v

docker compose -f docker-compose.test.yml down -v --remove-orphans
```

`down -v` 会删除本轮 MySQL 测试数据卷，保证下一轮从干净数据开始。

## 发布 GitHub Pages

仓库内的 `.github/workflows/api-regression-self-hosted.yml` 使用 Windows
self-hosted runner 执行回归。工作流支持 `main` 分支 push 自动触发，也支持
`workflow_dispatch` 手动触发。

执行链路：

```text
测试代码提交到 main（AUTO_API_REGRESSION=true）或手动触发
  → Runner 检出测试仓库
  → Maven 构建本机 DrawIOAgent 与 group-buy-market
  → Docker Compose 创建 MySQL、Redis、RabbitMQ 和两个业务服务
  → 等待 18091/18092 业务接口就绪
  → pytest 执行稳定回归并生成 Allure
  → always() 清理容器、网络和测试数据卷
  → 上传 Allure Artifacts
  → 提交最新 docs 报告
  → GitHub 托管运行器部署 GitHub Pages
```

首次发布时，在 GitHub 仓库中进入：

```text
Settings → Pages → Build and deployment → Source → GitHub Actions
```

然后启动本机 Runner。可以在 `Actions` 页面手动运行
`API Regression on Self-hosted Runner`；是否在 push 到 `main` 时自动执行，
由仓库变量 `AUTO_API_REGRESSION` 控制。

在 GitHub 仓库中进入：

```text
Settings → Secrets and variables → Actions → Variables
```

创建变量：

```text
AUTO_API_REGRESSION=false  # push 不执行，仅允许手动 Run workflow
AUTO_API_REGRESSION=true   # push 自动执行，也可以手动执行
```

变量未配置时等同于 `false`。关闭状态下，push 触发记录中的回归 Job 会显示
`Skipped`，不会执行 Maven、Docker 或 pytest；`workflow_dispatch` 手动触发始终执行。

由于 Java 源码和 Docker Desktop 位于本机，构建与测试阶段使用 self-hosted
runner；Allure 静态页面由 GitHub 托管运行器发布。机器人只更新 `docs/**` 的
报告提交会被 `paths-ignore` 忽略，避免工作流循环触发。

## 技术特点

- fixture 管理客户端、环境地址和业务前置数据
- marker 区分 smoke、regression、negative、e2e、slow、ai_quality
- 参数化覆盖多组异常输入
- xfail 记录已知缺陷，`strict=True` 防止修复后被静默忽略
- JSON Schema 校验响应契约
- `Decimal` 避免金额浮点精度问题
- `ThreadPoolExecutor + Barrier` 模拟并发重复通知
- 轮询等待异步额度到账，设置超时防止无限等待
- 自动脱敏并向 Allure 附加请求、响应、耗时和运行环境
- Docker Compose 每轮创建并销毁独立测试基础设施和数据卷
- GitHub Actions 支持 push/手动触发、失败后自动清理及 Pages 发布
