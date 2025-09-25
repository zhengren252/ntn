# TACoreService - 交易代理核心服务

## 项目概述

TACoreService是一个高性能的交易代理核心服务，基于ZeroMQ消息队列和微服务架构设计。该服务提供了完整的交易功能，包括市场扫描、订单执行、风险评估等核心功能，并集成了TradingAgents-CN智能交易代理。

## 核心特性

- **高性能消息队列**: 基于ZeroMQ ROUTER/DEALER模式的负载均衡代理
- **工作进程集群**: 支持多进程并行处理，提高系统吞吐量
- **智能交易集成**: 集成TradingAgents-CN提供AI驱动的交易决策
- **实时监控**: FastAPI驱动的监控API和Web界面
- **数据持久化**: SQLite数据库存储请求日志和系统指标
- **缓存优化**: Redis缓存提高数据访问性能
- **可靠性保证**: Lazy Pirate Pattern确保客户端连接可靠性
- **健康检查**: 完整的服务健康监控机制

## 系统架构

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   客户端应用     │    │   负载均衡代理   │    │   工作进程集群   │
│                │────│   (ZeroMQ)     │────│                │
│  Lazy Pirate   │    │   ROUTER/DEALER │    │ TradingAgents  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                │
                       ┌─────────────────┐
                       │   监控API服务   │
                       │   (FastAPI)    │
                       └─────────────────┘
                                │
                    ┌─────────────┴─────────────┐
                    │                           │
            ┌─────────────────┐        ┌─────────────────┐
            │   SQLite数据库   │        │   Redis缓存     │
            │   (日志/指标)    │        │   (市场数据)    │
            └─────────────────┘        └─────────────────┘
```

## 快速开始

### 环境要求

- Python 3.11+
- Redis 6.0+
- Docker & Docker Compose (可选)

### 本地开发安装

1. **克隆项目**
```bash
git clone <repository-url>
cd 12TACoreService
```

2. **创建虚拟环境**
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate     # Windows
```

3. **安装依赖**
```bash
pip install -r requirements.txt
```

4. **启动Redis服务**
```bash
# 使用Docker
docker run -d -p 6379:6379 redis:7-alpine

# 或本地安装的Redis
redis-server
```

5. **运行服务**
```bash
python -m tacoreservice.main
```

### Docker部署

#### 快速部署

**Linux/Mac:**
```bash
chmod +x deploy.sh
./deploy.sh
```

**Windows:**
```cmd
deploy.bat
```

#### 手动部署

```bash
# 构建并启动服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f tacoreservice
```

## API接口

### ZeroMQ接口 (端口: 5555)

#### 请求格式
```json
{
    "request_id": "unique_request_id",
    "method": "method_name",
    "params": {
        "param1": "value1",
        "param2": "value2"
    }
}
```

#### 响应格式
```json
{
    "status": "success|error",
    "request_id": "unique_request_id",
    "data": {},
    "error": null,
    "processing_time_ms": 150,
    "timestamp": 1640995200
}
```

### 支持的方法

#### 1. 健康检查
```json
{
    "method": "health.check",
    "params": {
        "detailed": false
    }
}
```

#### 2. 市场扫描
```json
{
    "method": "scan.market",
    "params": {
        "market": "US",
        "criteria": {
            "min_volume": 1000000,
            "price_range": [10, 500]
        }
    }
}
```

#### 3. 订单执行
```json
{
    "method": "execute.order",
    "params": {
        "symbol": "AAPL",
        "action": "buy",
        "quantity": 100,
        "order_type": "market"
    }
}
```

#### 4. 风险评估
```json
{
    "method": "evaluate.risk",
    "params": {
        "portfolio": {
            "AAPL": 100,
            "GOOGL": 50
        }
    }
}
```

#### 5. 股票分析
```json
{
    "method": "analyze.stock",
    "params": {
        "symbol": "AAPL",
        "analysis_type": "technical"
    }
}
```

#### 6. 市场数据获取
```json
{
    "method": "get.market_data",
    "params": {
        "symbols": ["AAPL", "GOOGL", "MSFT"]
    }
}
```

### 监控API (端口: 8000)

- **健康检查**: `GET /health`
- **服务指标**: `GET /metrics`
- **请求日志**: `GET /logs`
- **工作进程状态**: `GET /workers`
- **方法统计**: `GET /methods`

## 客户端示例

### Python客户端

```python
import zmq
import json
import uuid

class TACoreServiceClient:
    def __init__(self, server_endpoint="tcp://localhost:5555"):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REQ)
        self.socket.connect(server_endpoint)
        
        # Lazy Pirate Pattern配置
        self.socket.setsockopt(zmq.LINGER, 0)
        self.poll = zmq.Poller()
        self.poll.register(self.socket, zmq.POLLIN)
    
    def send_request(self, method, params=None, timeout=5000):
        request = {
            "request_id": str(uuid.uuid4()),
            "method": method,
            "params": params or {}
        }
        
        # 发送请求
        self.socket.send_string(json.dumps(request))
        
        # 等待响应
        socks = dict(self.poll.poll(timeout))
        if socks.get(self.socket) == zmq.POLLIN:
            response = self.socket.recv_string()
            return json.loads(response)
        else:
            # 超时处理
            self.socket.close()
            self.socket = self.context.socket(zmq.REQ)
            self.socket.connect("tcp://localhost:5555")
            self.poll.register(self.socket, zmq.POLLIN)
            raise TimeoutError("Request timeout")
    
    def health_check(self):
        return self.send_request("health.check")
    
    def scan_market(self, market="US", criteria=None):
        params = {"market": market}
        if criteria:
            params["criteria"] = criteria
        return self.send_request("scan.market", params)
    
    def close(self):
        self.socket.close()
        self.context.term()

# 使用示例
client = TACoreServiceClient()
try:
    # 健康检查
    health = client.health_check()
    print(f"Health: {health}")
    
    # 市场扫描
    scan_result = client.scan_market(
        market="US",
        criteria={"min_volume": 1000000}
    )
    print(f"Scan result: {scan_result}")
finally:
    client.close()
```

## 配置说明

### 环境变量

- `TACORESERVICE_ENV`: 运行环境 (development/production)
- `TACORESERVICE_LOG_LEVEL`: 日志级别 (DEBUG/INFO/WARNING/ERROR)
- `REDIS_URL`: Redis连接URL
- `DATABASE_PATH`: SQLite数据库文件路径
- `WORKER_COUNT`: 工作进程数量
- `ZMQ_FRONTEND_PORT`: ZeroMQ前端端口
- `ZMQ_BACKEND_PORT`: ZeroMQ后端端口
- `API_PORT`: 监控API端口

### 配置文件

配置文件位于 `config/` 目录下：

- `config.yaml`: 主配置文件
- `logging.yaml`: 日志配置
- `trading_config.yaml`: 交易相关配置

## 监控和日志

### 日志文件

- `logs/tacoreservice.log`: 主服务日志
- `logs/worker.log`: 工作进程日志
- `logs/performance.log`: 性能日志

### 监控指标

- 请求总数和成功率
- 平均响应时间
- 工作进程状态
- 系统资源使用情况
- 缓存命中率

## 测试

```bash
# 运行所有测试
pytest tests/ -v

# 运行特定测试
pytest tests/test_message_handler.py -v

# 生成覆盖率报告
pytest tests/ --cov=tacoreservice --cov-report=html
```

## 性能优化

### 建议配置

- **工作进程数**: CPU核心数 × 2
- **Redis内存**: 根据缓存数据量调整
- **数据库连接池**: 10-20个连接
- **ZeroMQ高水位标记**: 1000

### 监控关键指标

- 响应时间 < 100ms (P95)
- CPU使用率 < 80%
- 内存使用率 < 85%
- 缓存命中率 > 90%

## 故障排除

### 常见问题

1. **服务无法启动**
   - 检查端口是否被占用
   - 确认Redis服务是否运行
   - 查看日志文件获取详细错误信息

2. **连接超时**
   - 检查防火墙设置
   - 确认ZeroMQ端口配置
   - 增加客户端超时时间

3. **性能问题**
   - 增加工作进程数量
   - 优化Redis缓存策略
   - 检查数据库查询性能

### 日志分析

```bash
# 查看错误日志
grep "ERROR" logs/tacoreservice.log

# 监控实时日志
tail -f logs/tacoreservice.log

# 分析性能日志
grep "processing_time" logs/performance.log | awk '{print $NF}' | sort -n
```

## 贡献指南

1. Fork项目
2. 创建功能分支
3. 提交更改
4. 推送到分支
5. 创建Pull Request

## 许可证

本项目采用MIT许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 联系方式

- 项目维护者: TACoreService Team
- 邮箱: support@tacoreservice.com
- 文档: https://docs.tacoreservice.com