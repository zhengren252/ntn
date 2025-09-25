# TACoreService - AI智能体驱动交易系统V3.5核心服务

## 概述

TACoreService是AI智能体驱动交易系统V3.5的核心服务，负责统一管理和提供TradingAgents-CN功能。该服务采用ZeroMQ通信协议，为所有模组提供标准化的AI交易代理服务。

## 功能特性

- **统一服务接口**: 通过ZeroMQ REP套接字提供标准化API
- **多进程架构**: 支持多工作进程并行处理请求
- **负载均衡**: 自动分配任务到可用的工作进程
- **健康监控**: 内置健康检查和性能监控
- **容器化部署**: 完整的Docker容器化支持
- **配置管理**: 灵活的环境配置管理
- **日志记录**: 结构化日志记录和监控

## 架构设计

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Scanner       │    │   Strategy      │    │   Portfolio     │
│   Module        │    │   Module        │    │   Module        │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          │              ZeroMQ REQ/REP                  │
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 │
                    ┌─────────────────┐
                    │  TACoreService  │
                    │   (Main Loop)   │
                    └─────────┬───────┘
                              │
                    ┌─────────┴───────┐
                    │ Worker Process  │
                    │      Pool       │
                    └─────────────────┘
```

## 快速开始

### 环境要求

- Python 3.11+
- Docker & Docker Compose
- ZeroMQ库

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置环境

1. 复制环境配置文件：
```bash
cp .env.example .env
```

2. 编辑配置文件：
```bash
vim .env
```

### 运行服务

#### 直接运行

```bash
python main.py
```

#### Docker运行

```bash
# 构建镜像
docker build -t tacore-service .

# 运行容器
docker run -p 5555:5555 tacore-service
```

#### Docker Compose运行

```bash
# 启动所有服务
docker-compose up -d

# 启动包含监控的服务
docker-compose --profile monitoring up -d

# 查看日志
docker-compose logs -f tacore-service

# 停止服务
docker-compose down
```

## API接口

### 请求格式

```json
{
  "method": "scan.market",
  "params": {
    "symbols": ["BTCUSDT", "ETHUSDT"],
    "scan_type": "comprehensive"
  },
  "request_id": "req_123456"
}
```

### 响应格式

```json
{
  "status": "success",
  "result": {
    "scan_results": [...],
    "total_scanned": 2
  },
  "request_id": "req_123456",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

### 支持的方法

- `scan.market`: 市场扫描
- `analyze.symbol`: 单个交易对分析
- `get.market_data`: 获取市场数据
- `health.check`: 健康检查

## 配置说明

### 环境变量

| 变量名 | 描述 | 默认值 |
|--------|------|--------|
| `ENVIRONMENT` | 运行环境 | `development` |
| `SERVICE_PORT` | 服务端口 | `5555` |
| `WORKER_COUNT` | 工作进程数 | `4` |
| `LOG_LEVEL` | 日志级别 | `INFO` |

### 配置文件

- `config/config.yaml`: 主配置文件
- `config/redis.conf`: Redis配置
- `config/prometheus.yml`: Prometheus监控配置

## 监控和日志

### 健康检查

```bash
# 检查服务状态
curl http://localhost:8080/health

# 或使用ZeroMQ
python -c "import zmq; ctx = zmq.Context(); sock = ctx.socket(zmq.REQ); sock.connect('tcp://localhost:5555'); sock.send_json({'method': 'health.check'}); print(sock.recv_json())"
```

### 监控指标

- 请求总数
- 成功/失败率
- 响应时间
- 工作进程状态
- 系统资源使用

### 日志查看

```bash
# 查看服务日志
tail -f logs/tacore.log

# Docker日志
docker-compose logs -f tacore-service
```

## 开发指南

### 项目结构

```
12TACoreService/
├── main.py              # 主服务文件
├── worker.py            # 工作进程
├── Dockerfile           # Docker配置
├── docker-compose.yml   # 容器编排
├── requirements.txt     # Python依赖
├── .env                 # 环境变量
├── config/              # 配置文件目录
│   ├── config.yaml      # 主配置
│   ├── redis.conf       # Redis配置
│   └── prometheus.yml   # 监控配置
└── README.md           # 文档
```

### 添加新方法

1. 在`main.py`的`_process_request`方法中添加路由
2. 实现对应的处理方法
3. 在`worker.py`中添加具体的业务逻辑
4. 更新API文档

### 测试

```bash
# 运行单元测试
pytest tests/

# 运行集成测试
pytest tests/integration/

# 性能测试
pytest tests/performance/
```

## 部署指南

### 生产环境部署

1. 设置环境变量：
```bash
export ENVIRONMENT=production
export WORKER_COUNT=8
export LOG_LEVEL=WARNING
```

2. 启动服务：
```bash
docker-compose -f docker-compose.yml --profile monitoring up -d
```

3. 配置负载均衡器（如Nginx）

4. 设置监控告警

### 扩容指南

- 水平扩容：增加服务实例
- 垂直扩容：增加工作进程数
- 负载均衡：使用ZeroMQ DEALER/ROUTER模式

## 故障排除

### 常见问题

1. **服务无法启动**
   - 检查端口是否被占用
   - 验证配置文件格式
   - 查看日志文件

2. **请求超时**
   - 检查网络连接
   - 增加超时时间
   - 检查工作进程状态

3. **内存使用过高**
   - 调整工作进程数
   - 检查内存泄漏
   - 优化数据处理逻辑

### 日志分析

```bash
# 查看错误日志
grep "ERROR" logs/tacore.log

# 分析请求统计
grep "requests_total" logs/tacore.log | tail -10
```

## 版本历史

- **v3.5.0**: 初始版本，统一TradingAgents-CN服务
- 支持ZeroMQ通信协议
- 多进程架构
- 容器化部署

## 许可证

本项目采用MIT许可证。详见LICENSE文件。

## 联系方式

如有问题或建议，请联系开发团队。