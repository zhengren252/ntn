模组十二：TACoreService - A.C.R.E. 审计与修复协议
模组核心特性 (Contextualize)
首先，我们必须明确TACoreService的上下文信息，这些信息综合自所有项目文档：


核心职责: 作为TradingAgents-CN库的唯一、统一的服务化封装，通过高性能的负载均衡架构，为其他所有模组提供稳定、可扩展的AI交易能力（如市场扫描、订单执行、风险评估） 。

语言/框架: Python, ZeroMQ。

关键文件与结构:

main.py: ZMQ前端/代理 (ROUTER)，负责接收所有外部请求，并将其分发给后端的多个工作进程。

worker.py: ZMQ后端/工作进程 (DEALER)，实际执行AI计算任务（调用TradingAgents-CN库），可水平扩展。

Dockerfile: 包含构建服务和工作进程镜像的指令。


核心架构: 采用ZeroMQ的 ROUTER/DEALER 模式，实现请求的自动负载均衡 。

docker-compose.yml中应包含两个服务：tacore_service (运行main.py) 和 tacore_worker (运行worker.py，且可设置多副本replicas) 。

通信协议:

提供服务: 对内提供ZeroMQ REQ/REP 服务模式的接口。


核心服务: scan.market, execute.order, evaluate.risk 。

核心依赖:

TradingAgents-CN库: 核心AI能力的来源。


模组一 (APIForge): 用于获取认证后的交易所实例 。

Redis: 可能用于缓存或状态管理。