# NeuroTrade Nexus (NTN) - 扫描器模组 (ScanPulse)

## 项目概述

ScanPulse是NeuroTrade Nexus系统的核心扫描器模组，专注于加密货币市场的实时监控和智能分析。基于微服务架构设计，提供高性能、高可用性的市场扫描服务。

## 核心功能

### 🎯 三高规则引擎
- **高波动性检测**: 识别价格波动剧烈的交易对
- **高流动性筛选**: 筛选交易活跃的优质标的
- **高相关性分析**: 发现市场联动性强的交易机会

### 🐎 黑马监测器
- **新闻事件触发**: 基于新闻热点发现潜在黑马
- **技术指标分析**: 多维度技术分析识别突破信号
- **智能评分系统**: 综合评估黑马潜力

### 💎 潜力挖掘器
- **低市值筛选**: 发现被低估的小市值币种
- **价格洼地识别**: 寻找价格相对较低的投资机会
- **成长性分析**: 评估项目发展潜力

### 🔗 系统集成
- **TradingAgents-CN适配**: 复用现有扫描引擎
- **ZeroMQ通信**: 高性能消息传递
- **Redis缓存**: 高速数据存储和检索
- **多环境支持**: 开发/预发布/生产环境隔离

## 技术架构

### 核心技术栈
- **Python 3.11+**: 主要开发语言
- **ZeroMQ**: 高性能消息队列
- **Redis**: 内存数据库和缓存
- **asyncio**: 异步编程框架
- **structlog**: 结构化日志记录
- **pydantic**: 数据验证和序列化
- **Docker**: 容器化部署

### 架构设计
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   三高规则引擎   │    │   黑马监测器     │    │   潜力挖掘器     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │   扫描器核心     │
                    └─────────────────┘
                                 │
         ┌───────────────────────┼───────────────────────┐
         │                       │                       │
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  ZeroMQ通信     │    │  Redis缓存      │    │ TradingAgents   │
│     模块        │    │     模块        │    │   CN适配器      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 快速开始

### 环境要求
- Python 3.11+
- Redis 6.0+
- ZeroMQ 4.3+
- Docker (可选)

### 安装步骤

1. **克隆项目**
```bash
git clone <repository-url>
cd "03ScanPulse"
```

2. **安装依赖**
```bash
pip install -r requirements.txt
```

3. **配置环境**
```bash
# 复制环境变量模板
cp .env.example .env

# 编辑环境变量
vim .env
```

4. **启动Redis服务**
```bash
# 使用Docker启动Redis
docker run -d --name redis -p 6379:6379 redis:7-alpine

# 或使用本地Redis服务
redis-server
```

5. **运行扫描器**
```bash
# 开发环境
python start.py --env development

# 生产环境
python start.py --env production
```

### Docker部署

1. **构建镜像**
```bash
docker build -t scanpulse:latest .
```

2. **使用Docker Compose**
```bash
# 生产环境
docker-compose up -d

# 开发环境
docker-compose -f docker-compose.dev.yml up -d
```

## 配置说明

### 环境配置

项目支持三种环境配置：
- `development`: 开发环境
- `staging`: 预发布环境
- `production`: 生产环境

### 配置文件

- `config.yaml`: 默认配置
- `config.development.yaml`: 开发环境配置
- `config.production.yaml`: 生产环境配置
- `.env`: 环境变量配置

### 关键配置项

```yaml
# Redis配置
redis:
  host: localhost
  port: 6379
  db: 0
  password: null

# ZeroMQ配置
zmq:
  pub_port: 5555
  rep_port: 5556
  
# 扫描器配置
scanner:
  scan_interval: 60
  batch_size: 100
  max_workers: 4
```

## 使用指南

### 启动参数

```bash
# 基本启动
python start.py

# 指定环境
python start.py --env production

# 自定义配置
python start.py --config-file custom_config.yaml

# 设置日志级别
python start.py --log-level DEBUG

# 检查依赖
python start.py --check-deps
```

### API接口

扫描器通过ZeroMQ提供以下接口：

1. **扫描请求** (REQ/REP模式)
```python
# 请求格式
{
    "action": "scan",
    "symbols": ["BTCUSDT", "ETHUSDT"],
    "rules": ["three_high", "black_horse"]
}

# 响应格式
{
    "status": "success",
    "results": [...],
    "timestamp": "2024-01-01T00:00:00Z"
}
```

2. **结果订阅** (PUB/SUB模式)
```python
# 订阅主题
"scan_results"     # 扫描结果
"three_high"       # 三高信号
"black_horse"      # 黑马信号
"potential"        # 潜力信号
"status"           # 状态更新
```

### 监控和日志

1. **健康检查**
```bash
curl http://localhost:8080/health
```

2. **日志查看**
```bash
# 查看实时日志
tail -f logs/scanner.log

# 查看错误日志
tail -f logs/error.log
```

3. **Redis监控**
```bash
# 连接Redis CLI
redis-cli

# 查看扫描结果
KEYS scanner:scan_results:*
```

## 开发指南

### 项目结构

```
03ScanPulse/
├── scanner/                    # 主要代码目录
│   ├── engines/               # 扫描引擎
│   │   ├── three_high_engine.py
│   │   └── base_engine.py
│   ├── detectors/             # 检测器
│   │   └── black_horse_detector.py
│   ├── miners/                # 挖掘器
│   │   └── potential_finder.py
│   ├── communication/         # 通信模块
│   │   ├── zmq_client.py
│   │   └── redis_client.py
│   ├── adapters/              # 适配器
│   │   └── trading_agents_cn_adapter.py
│   ├── config/                # 配置管理
│   │   ├── env_manager.py
│   │   ├── config.yaml
│   │   ├── config.development.yaml
│   │   └── config.production.yaml
│   ├── utils/                 # 工具模块
│   │   ├── logger.py
│   │   └── health_check.py
│   └── main.py                # 主程序入口
├── tests/                     # 测试代码
├── logs/                      # 日志目录
├── requirements.txt           # 依赖列表
├── Dockerfile                 # Docker配置
├── docker-compose.yml         # Docker Compose配置
├── start.py                   # 启动脚本
└── README.md                  # 项目文档
```

### 添加新的扫描规则

1. **创建规则引擎**
```python
# scanner/engines/my_rule_engine.py
from .base_engine import BaseEngine

class MyRuleEngine(BaseEngine):
    async def analyze(self, symbol: str, data: dict) -> dict:
        # 实现分析逻辑
        pass
```

2. **注册规则引擎**
```python
# scanner/main.py
from scanner.engines.my_rule_engine import MyRuleEngine

# 在ScannerApplication.initialize_components()中添加
if scanner_config["rules"]["my_rule"]["enabled"]:
    self.my_rule_engine = MyRuleEngine(
        scanner_config["rules"]["my_rule"],
        self.redis_client
    )
```

3. **更新配置文件**
```yaml
# config.yaml
scanner:
  rules:
    my_rule:
      enabled: true
      threshold: 0.8
```

### 测试

```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/test_engines.py

# 运行测试并生成覆盖率报告
pytest --cov=scanner
```

### 代码规范

```bash
# 代码格式化
black scanner/

# 代码检查
flake8 scanner/

# 类型检查
mypy scanner/
```

## 部署指南

### 生产环境部署

1. **环境准备**
```bash
# 创建生产环境配置
cp config.production.yaml config.yaml

# 设置环境变量
export SCANNER_ENV=production
export REDIS_HOST=redis.example.com
export REDIS_PASSWORD=your_password
```

2. **Docker部署**
```bash
# 构建生产镜像
docker build -t scanpulse:v1.0.0 .

# 启动服务
docker-compose up -d
```

3. **监控配置**
```bash
# 启动Prometheus监控
docker-compose -f docker-compose.monitoring.yml up -d
```

### 性能优化

1. **Redis优化**
- 启用持久化
- 配置内存限制
- 设置合适的过期策略

2. **ZeroMQ优化**
- 调整高水位标记
- 配置适当的套接字选项
- 使用连接池

3. **扫描器优化**
- 调整批处理大小
- 优化扫描间隔
- 使用多线程处理

## 故障排除

### 常见问题

1. **Redis连接失败**
```bash
# 检查Redis服务状态
redis-cli ping

# 检查网络连接
telnet redis_host 6379
```

2. **ZeroMQ端口冲突**
```bash
# 检查端口占用
netstat -tulpn | grep 5555

# 修改配置文件中的端口
```

3. **内存不足**
```bash
# 检查内存使用
free -h

# 调整批处理大小
# 在config.yaml中减少batch_size
```

### 日志分析

```bash
# 查看错误日志
grep "ERROR" logs/scanner.log

# 查看性能日志
grep "PERFORMANCE" logs/scanner.log

# 查看特定组件日志
grep "three_high_engine" logs/scanner.log
```

## 贡献指南

1. Fork项目
2. 创建功能分支
3. 提交更改
4. 推送到分支
5. 创建Pull Request

### 提交规范

```
feat: 添加新功能
fix: 修复bug
docs: 更新文档
style: 代码格式调整
refactor: 代码重构
test: 添加测试
chore: 构建过程或辅助工具的变动
```

## 许可证

本项目采用MIT许可证 - 查看[LICENSE](LICENSE)文件了解详情。

## 联系方式

- 项目维护者: NeuroTrade Nexus Team
- 邮箱: support@neurotrade-nexus.com
- 文档: https://docs.neurotrade-nexus.com

## 更新日志

### v1.0.0 (2024-01-01)
- 初始版本发布
- 实现三高规则引擎
- 实现黑马监测器
- 实现潜力挖掘器
- 集成TradingAgents-CN适配器
- 支持Docker容器化部署
- 完善监控和日志系统