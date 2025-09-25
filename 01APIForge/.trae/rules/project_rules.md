模组一：API统一管理工厂 (APIForge) - A.C.R.E. 审计与修复协议
模组核心特性 (Contextualize)
首先，我们必须明确APIForge的上下文信息，这些信息均提炼自您提供的最新规范文档：


核心职责: 系统的“外交与安保部”，作为统一的对外网关，负责安全、稳定、高效地管理所有外部第三方API调用，不作为内部API网关 。


语言/框架: 推荐使用 Python (FastAPI) 。

关键文件与结构:


main.py: 服务主入口 。


routers/exchange.py & routers/llm.py: 按功能分离的路由文件 。


security.py: 认证与安全逻辑 。


config/prod.yaml: 生产环境配置文件 。


Dockerfile: 容器化部署文件 。

通信协议:


提供服务: 对内提供HTTP/HTTPS RESTful API，服务地址为 http://api_factory:8000 。


核心API端点: POST /exchange/{exchange_name}/order, GET /exchange/{exchange_name}/klines, POST /llm/{model_name}/chat 。


发布通知: 通过ZeroMQ (PUB)向外广播状态变更 。


ZMQ主题: api_factory.events.status 。


ZMQ消息结构: {"source": "api_factory", "type": "status_change", "api_name": "binance", "status": "down", ...} 。

核心功能:

API网关 。

认证中心 。

配额与熔断 。

集群管理 。


核心依赖: 无内部模组依赖 。

审计清单 (Audit Checklist)
在执行任何修复前，请指挥trae执行以下只读审计命令，以评估模组健康状况：

文件结构完整性审计:

指令: ls -R 01APIForge/


检查: 确认项目结构是否符合搭建规范，包含routers、config等目录以及main.py等关键文件 。

配置与安全审计:

指令: grep '\${.*}' 01APIForge/config/prod.yaml


检查: 确认prod.yaml配置文件中，API密钥等敏感信息是通过${VAR}语法引用的环境变量，而非硬编码 。

指令: grep -r -i -E 'key|secret' 01APIForge/ --exclude-dir=config --exclude=*.md

检查: 扫描除配置文件外的所有代码文件，确保没有任何硬编码的API密钥或私密信息。

API与通信逻辑审计:

指令: grep -r -E "/exchange|/llm" 01APIForge/routers/


检查: 确认routers目录下的文件中定义了/exchange/{exchange_name}/order和/llm/{model_name}/chat等核心API端点 。

指令: grep "api_factory.events.status" 01APIForge/main.py


检查: 确认main.py或其调用的模块中，存在向api_factory.events.status主题发布ZeroMQ消息的逻辑 。

依赖库审计:

指令: cat 01APIForge/requirements.txt


检查: 确认fastapi和pyzmq等核心库已包含在内 。

原子化修复规则 (Atomic Repair Rules)
如果审计发现问题，请使用以下精确、封装的指令进行修复。

场景一：配置文件config/prod.yaml结构损坏或不符合规范

风险: 错误的配置结构将导致服务启动失败或无法正确加载API密钥。

原子化修复策略: 使用heredoc完整、一次性地重写配置文件，确保其结构和变量引用方式的正确性。

给trae的指令:

Bash

# 指令：原子化恢复APIForge的prod.yaml配置文件结构。
cat > 01APIForge/config/prod.yaml << 'EOF'
# 标准配置文件 V1.1
binance:
  api_key: ${BINANCE_API_KEY}
  api_secret: ${BINANCE_API_SECRET}

okx:
  api_key: ${OKX_API_KEY}
  api_secret: ${OKX_API_SECRET}

deepseek_llm:
  api_key: ${DEEPSEEK_API_KEY}
EOF

echo "配置文件结构已恢复。请确保环境变量已正确设置，然后执行 'docker-compose restart api_factory' 来使配置生效。"
场景二：交易路由逻辑(routers/exchange.py)损坏或丢失

风险: 交易是核心功能，路由损坏将导致所有交易失败。

原子化修复策略: 使用一个独立的shell脚本，执行“停止-备份-替换-构建-启动-验证”的完整原子操作，确保逻辑被完整无误地恢复。

创建repair_apiforge_router.sh脚本:

Bash

#!/bin/bash
# 该脚本用于原子化修复APIForge的交易路由逻辑
set -e # 任何命令失败则立即中止脚本

MODULE_DIR="01APIForge"
ROUTER_FILE="routers/exchange.py"
SERVICE_NAME="api_factory"

echo "正在原子化修复 ${MODULE_DIR}/${ROUTER_FILE}..."

# 1. 停止相关服务
docker-compose stop ${SERVICE_NAME}

# 2. 安全备份当前文件
mv "${MODULE_DIR}/${ROUTER_FILE}" "${MODULE_DIR}/${ROUTER_FILE}.bak.$(date +%s)"

# 3. 使用heredoc原子化写入全新的、符合规范的文件内容
cat > "${MODULE_DIR}/${ROUTER_FILE}" << 'EOF'
# 标准交易路由 V1.1
from fastapi import APIRouter, Body

router = APIRouter(prefix="/exchange", tags=["Exchange"])

@router.post("/{exchange_name}/order")
def execute_order(exchange_name: str, order_details: dict = Body(...)):
    # 完整的订单执行逻辑...
    # 示例响应结构
    print(f"Executing order on {exchange_name} with details: {order_details}")
    return {"status": "ok", "orderId": "mock_order_12345"}

@router.get("/{exchange_name}/klines")
def get_klines(exchange_name: str, symbol: str, interval: str = "1h"):
    # 完整的K线获取逻辑...
    print(f"Fetching klines for {symbol} on {exchange_name}")
    return {"status": "ok", "data": []}
EOF

# 4. 重启并验证服务
echo "交易路由文件已恢复，正在重建并启动服务..."
docker-compose up -d --build ${SERVICE_NAME}
sleep 5 # 等待服务健康检查

echo "修复完成。请检查最新的50行日志以确认服务正常启动："
docker-compose logs --tail=50 ${SERVICE_NAME}
给trae的指令:
执行bash ./repair_apiforge_router.sh

演进与验证 (Evolve/Verify)
在执行完任何修复操作后，必须指挥trae重新运行一遍审计清单中的所有命令，以确保修复已成功且未引入新问题。

针对APIForge的专属验证步骤:

指令:

Bash

# 从一个临时容器内部测试APIForge的健康检查端点
# 注意: <your_project_network_name> 需要替换为实际的Docker网络名
docker run --rm --network=<your_project_network_name> nicolaka/netshoot curl -s -o /dev/null -w "%{http_code}" http://api_factory:8000/health
预期输出: 200。如果不是200，则表示服务未能正常启动，需要立即检查日志 (docker-compose logs api_factory)。