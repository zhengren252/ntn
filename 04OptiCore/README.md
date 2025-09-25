# NeuroTrade Nexus (NTN) - 策略优化模组 (OptiCore)

[![Python Version](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://docker.com)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-passing-brightgreen.svg)](tests/)
[![Coverage](https://img.shields.io/badge/coverage-95%25-brightgreen.svg)](htmlcov/)

## 📋 项目概述

策略优化模组 (OptiCore) 是 NeuroTrade Nexus 量化交易系统的核心组件，负责策略参数优化、回测验证和决策生成。该模组采用微服务架构，集成了遗传算法优化器、VectorBT回测引擎和智能决策引擎。

### 🎯 核心功能

- **🧬 遗传算法优化**: 使用DEAP库实现多目标参数优化
- **📊 高性能回测**: 基于VectorBT的向量化回测引擎
- **🤖 智能决策**: 自动化策略评估和参数包生成
- **📡 消息通信**: ZeroMQ消息总线实现模组间通信
- **🛡️ 风险管理**: 实时风险监控和控制机制
- **🔄 三环境隔离**: 开发、预发布、生产环境完全隔离
- **🐳 容器化部署**: Docker和Docker Compose支持
- **📈 性能监控**: Prometheus + Grafana监控体系

### 🏗️ 技术架构

```
┌─────────────────────────────────────────────────────────────┐
│                    策略优化模组 (OptiCore)                      │
├─────────────────────────────────────────────────────────────┤
│  API层          │  FastAPI + Uvicorn                        │
├─────────────────────────────────────────────────────────────┤
│  业务逻辑层      │  遗传优化器 │ 回测引擎 │ 决策引擎 │ 风险管理  │
├─────────────────────────────────────────────────────────────┤
│  通信层          │  ZeroMQ消息总线 (订阅/发布模式)              │
├─────────────────────────────────────────────────────────────┤
│  数据层          │  SQLite/PostgreSQL │ Redis缓存           │
├─────────────────────────────────────────────────────────────┤
│  基础设施层      │  Docker容器 │ 监控告警 │ 日志聚合           │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 快速开始

### 环境要求

- Python 3.11+
- Docker & Docker Compose
- Redis (可选，用于缓存)
- PostgreSQL (可选，生产环境推荐)

### 安装步骤

#### 1. 克隆项目

```bash
git clone <repository-url>
cd 04OptiCore
```

#### 2. 环境配置

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑环境变量
vim .env
```

#### 3. 使用Docker部署（推荐）

```bash
# 开发环境
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# 生产环境
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

#### 4. 本地开发部署

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 启动服务
uvicorn api.app:app --reload --host 0.0.0.0 --port 8000
```

### 验证安装

```bash
# 健康检查
curl http://localhost:8000/health

# API文档
open http://localhost:8000/docs
```

## 📖 使用指南

### API接口

#### 健康检查
```http
GET /health
```

#### 启动回测任务
```http
POST /api/backtest/start
Content-Type: application/json

{
  "strategy_id": 1,
  "symbol": "BTCUSDT",
  "start_date": "2023-01-01",
  "end_date": "2023-12-31",
  "initial_capital": 10000,
  "parameters": {
    "fast_period": 10,
    "slow_period": 20
  }
}
```

#### 启动参数优化
```http
POST /api/optimization/start
Content-Type: application/json

{
  "strategy_id": 1,
  "symbol": "BTCUSDT",
  "start_date": "2023-01-01",
  "end_date": "2023-12-31",
  "parameter_ranges": {
    "fast_period": [5, 15],
    "slow_period": [20, 50]
  },
  "optimization_target": "sharpe_ratio",
  "population_size": 50,
  "generations": 100
}
```

#### 生成策略决策
```http
POST /api/decision/make
Content-Type: application/json

{
  "symbol": "BTCUSDT",
  "market_data": {
    "price": 45000,
    "volume": 1500000,
    "timestamp": "2024-01-01T12:00:00Z"
  },
  "strategy_filters": {
    "min_confidence": 0.7,
    "max_risk_score": 0.3
  }
}
```

### 配置说明

#### 环境变量

```bash
# 核心环境
NTN_ENVIRONMENT=development  # development/staging/production
DEBUG=true
LOG_LEVEL=DEBUG

# 数据库配置
DATABASE_PATH=./data/opticore.db
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# ZeroMQ配置
ZMQ_SUBSCRIBER_PORT=5555
ZMQ_PUBLISHER_PORT=5556
ZMQ_SUBSCRIBER_TOPIC=scanner.pool.preliminary
ZMQ_PUBLISHER_TOPIC=optimizer.pool.trading

# 回测配置
BACKTEST_MAX_CONCURRENT=4
BACKTEST_TIMEOUT=300
BACKTEST_CACHE_SIZE=1000

# 优化配置
OPTIMIZATION_POPULATION_SIZE=50
OPTIMIZATION_GENERATIONS=100
OPTIMIZATION_MUTATION_RATE=0.1
OPTIMIZATION_CROSSOVER_RATE=0.8

# 风险控制
RISK_MAX_POSITION_SIZE=0.1
RISK_MAX_DAILY_LOSS=0.02
RISK_MAX_DRAWDOWN=0.15
RISK_MIN_CONFIDENCE=0.6
```

#### 策略参数示例

```json
{
  "ma_cross": {
    "fast_period": 10,
    "slow_period": 20,
    "signal_threshold": 0.01
  },
  "rsi_mean_reversion": {
    "rsi_period": 14,
    "oversold": 30,
    "overbought": 70,
    "exit_threshold": 50
  },
  "bollinger_bands": {
    "period": 20,
    "std_dev": 2,
    "entry_threshold": 0.02
  }
}
```

## 🧪 测试

### 运行测试

```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/test_backtest_engine.py

# 运行覆盖率测试
pytest --cov=optimizer --cov-report=html

# 运行性能测试
pytest -m performance

# 运行集成测试
pytest -m integration
```

### 测试分类

- **单元测试**: 测试单个组件功能
- **集成测试**: 测试组件间交互
- **性能测试**: 测试系统性能指标
- **端到端测试**: 测试完整业务流程

### 测试覆盖率

当前测试覆盖率: **95%**

查看详细覆盖率报告:
```bash
open htmlcov/index.html
```

## 📊 监控和运维

### 监控指标

- **系统指标**: CPU、内存、磁盘、网络使用率
- **业务指标**: 回测任务数、优化任务数、决策生成数
- **性能指标**: 响应时间、吞吐量、错误率
- **资源指标**: 数据库连接数、缓存命中率、队列长度

### 日志管理

```bash
# 查看实时日志
docker-compose logs -f opticore

# 查看错误日志
docker-compose logs opticore | grep ERROR

# 日志文件位置
./logs/opticore.log
./logs/error.log
./logs/access.log
```

### 性能调优

#### 数据库优化
```sql
-- 创建索引
CREATE INDEX idx_backtest_reports_strategy_symbol ON backtest_reports(strategy_id, symbol);
CREATE INDEX idx_optimization_tasks_status ON optimization_tasks(status);
```

#### Redis缓存配置
```bash
# 设置内存策略
redis-cli CONFIG SET maxmemory-policy allkeys-lru

# 设置过期时间
redis-cli CONFIG SET timeout 300
```

## 🔧 开发指南

### 项目结构

```
04OptiCore/
├── api/                    # FastAPI接口层
│   ├── app.py             # 主应用入口
│   └── routes/            # 路由定义
├── optimizer/             # 核心业务逻辑
│   ├── backtest/          # 回测引擎
│   ├── optimization/      # 遗传算法优化器
│   ├── decision/          # 决策引擎
│   ├── communication/     # ZeroMQ通信
│   ├── risk/              # 风险管理
│   └── utils/             # 工具函数
├── config/                # 配置文件
│   ├── config.py          # 系统配置
│   └── settings.py        # 环境设置
├── tests/                 # 测试文件
│   ├── conftest.py        # 测试配置
│   ├── test_utils.py      # 测试工具
│   └── test_*.py          # 具体测试
├── data/                  # 数据文件
├── logs/                  # 日志文件
├── docs/                  # 文档
├── scripts/               # 脚本文件
├── .env.example           # 环境变量模板
├── requirements.txt       # Python依赖
├── Dockerfile            # Docker配置
├── docker-compose.yml    # Docker Compose配置
├── pytest.ini           # 测试配置
└── README.md             # 项目说明
```

### 代码规范

#### Python代码风格
```bash
# 代码格式化
black .

# 导入排序
isort .

# 代码检查
flake8 .
mypy .
pylint optimizer/
```

#### 提交规范
```bash
# 提交格式
git commit -m "feat: 添加新功能"
git commit -m "fix: 修复bug"
git commit -m "docs: 更新文档"
git commit -m "test: 添加测试"
git commit -m "refactor: 重构代码"
```

### 添加新功能

1. **创建功能分支**
   ```bash
   git checkout -b feature/new-feature
   ```

2. **编写代码和测试**
   ```bash
   # 实现功能
   vim optimizer/new_module.py
   
   # 编写测试
   vim tests/test_new_module.py
   ```

3. **运行测试**
   ```bash
   pytest tests/test_new_module.py
   ```

4. **提交代码**
   ```bash
   git add .
   git commit -m "feat: 添加新功能模块"
   git push origin feature/new-feature
   ```

## 🚨 故障排除

### 常见问题

#### 1. 服务启动失败
```bash
# 检查端口占用
netstat -tulpn | grep :8000

# 检查Docker状态
docker-compose ps

# 查看详细错误
docker-compose logs opticore
```

#### 2. 数据库连接失败
```bash
# 检查数据库文件权限
ls -la data/opticore.db

# 检查Redis连接
redis-cli ping

# 重置数据库
rm data/opticore.db
python scripts/init_database.py
```

#### 3. ZeroMQ通信问题
```bash
# 检查端口绑定
netstat -tulpn | grep :555

# 测试ZeroMQ连接
python scripts/test_zmq.py
```

#### 4. 内存不足
```bash
# 检查内存使用
free -h
docker stats

# 清理缓存
redis-cli FLUSHALL
docker system prune
```

### 性能问题诊断

```bash
# 查看系统资源
top
htop
iostat

# 查看应用性能
python -m cProfile -o profile.stats api/app.py
python -c "import pstats; pstats.Stats('profile.stats').sort_stats('cumulative').print_stats(10)"

# 查看数据库性能
sqlite3 data/opticore.db ".timer on" ".explain query plan SELECT * FROM strategies;"
```

## 📚 相关文档

- [API文档](http://localhost:8000/docs) - FastAPI自动生成的API文档
- [技术架构文档](.trae/documents/策略优化模组技术架构文档.md) - 详细技术设计
- [部署指南](docs/deployment.md) - 生产环境部署说明
- [开发指南](docs/development.md) - 开发环境搭建
- [故障排除](docs/troubleshooting.md) - 常见问题解决方案

## 🤝 贡献指南

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 👥 团队

- **项目负责人**: NeuroTrade Nexus Team
- **技术架构**: AI Assistant
- **开发团队**: 量化交易开发组

## 📞 联系我们

- **项目主页**: [NeuroTrade Nexus](https://github.com/neurotrade-nexus)
- **问题反馈**: [Issues](https://github.com/neurotrade-nexus/04OptiCore/issues)
- **技术讨论**: [Discussions](https://github.com/neurotrade-nexus/04OptiCore/discussions)

---

**NeuroTrade Nexus (NTN)** - 让量化交易更智能 🚀