# 简历项目描述

## 项目名称

DrawIOAgent 跨系统接口自动化测试

## 项目描述

针对 AI 绘图助手 DrawIOAgent 与拼团交易系统 group-buy-market，
使用 pytest 搭建接口自动化测试工程，覆盖智能体配置、会话创建、额度校验、
拼团锁单与结算、成团回调、额度发放及跨系统端到端链路，并使用 Allure
生成可追溯的测试报告。

## 技术栈

Python、pytest、requests、JSON Schema、Allure、GitHub Actions、
ThreadPoolExecutor

## 简历职责与成果

- 基于 pytest fixture 封装多服务 API Client、环境参数和动态测试数据，
  支持通过命令行切换 DrawIOAgent 与拼团服务地址。
- 设计并实现 37 个接口自动化用例，覆盖正常流程、异常校验、参数化、
  顺序幂等、并发幂等以及三人拼团购买额度的跨系统 E2E 链路。
- 覆盖“购买额度—创建会话—AI 对话/图片解析—额度扣减”端到端链路，
  验证相同 requestId 重复请求时消费额度不被重复扣减，并验证失效
  sessionId 自动恢复、跨用户 sessionId 隔离后仍能正确完成对话与
  额度消费。
- 使用 JSON Schema 校验接口响应契约，使用 Decimal 校验金额关系，
  通过轮询与超时机制验证异步成团回调后的额度到账结果。
- 使用 ThreadPoolExecutor 与 Barrier 模拟 5 个并发重复通知，
  验证数据库唯一约束下额度仅发放一次，账户累计发放额度保持为 100。
- 使用 xfail(strict=True) 管理已知缺陷，发现并记录无效 agentId
  错误码不符合约定、成团通知 teamId 与订单不一致仍发放额度、
  负支付金额仍可购买额度、跨用户复用 requestId 可逃避扣费、
  聊天必填参数错误被额度校验掩盖、流式聊天绕过额度校验且不记账、
  非法图片请求仅返回未知失败、图片 requestId 跨用户复用可逃避扣费
  以及未认证调用方可伪造 userId 消耗其他用户额度等问题。
- 接入 Allure 的 Epic、Feature、Story、Severity 和 HTTP 请求/响应附件，
  最近一次全量回归结果为 26 passed、11 xfailed、0 unexpected failures。
- 编写 PowerShell 一键回归脚本，并通过 GitHub Actions 将静态 Allure
  报告发布至 GitHub Pages。

## 面试时可以重点说明

1. 为什么重复通知既需要测顺序幂等，也需要测并发幂等。
2. 业务状态判断、数据库唯一索引和事务分别解决什么问题。
3. 为什么共享 requests.Session 不适合直接用于多线程并发测试。
4. 异步到账为什么使用有限次数轮询，而不是固定 sleep。
5. xfail 与普通失败的区别，以及为什么使用 strict=True。
6. GitHub 云端无法访问本机服务时，为什么选择本地执行测试、Pages
   只负责发布静态报告。

> 发布到 GitHub 后，在简历项目名称旁补充仓库地址和 Allure Pages 地址。
