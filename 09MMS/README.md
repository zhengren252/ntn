# 市场微结构仿真引擎 (MMS)

## 项目概述

市场微结构仿真引擎 (Market Microstructure Simulation Engine, MMS) 是 NeuroTrade Nexus (NTN) 系统的第九个模组，专门用于模拟和分析金融市场的微观结构行为。该引擎提供高性能的市场仿真能力，支持做市商策略、套利策略的建模和回测。

### 核心功能

- **高性能仿真引擎**: 基于事件驱动的市场仿真框架
- **策略建模**: 支持做市商和套利策略的实现和测试
- **参数校准**: 自动化的市场参数校准和优化
- **分布式计算**: 基于ZeroMQ的负载均衡和任务分发
- **缓存优化**: Redis缓存提升数据访问性能
- **RESTful API**: 完整的Web API接口
- **实时监控**: 全面的指标收集和健康检查

### 技术架构

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   FastAPI       │    │  ZeroMQ Load    │    │  Simulation     │
│   Web Server    │◄──►│  Balancer       │◄──►│  Workers        │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Redis Cache   │    │  SQLite DB      │    │  Metrics        │
│   Layer         │    │  Storage        │    │  Collector      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 快速开始

### 环境要求

- Python 3.9+
- Redis Server 6.0+
- SQLite 3.35+
- ZeroMQ 4.3+

### 安装依赖

```bash
# 克隆项目
git clone <repository-url>
cd 09MMS

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

### 配置环境

1. 复制配置模板：
```bash
cp config/config.example.yaml config/config.yaml
```

2. 编辑配置文件 `config/config.yaml`：
```yaml
database:
  db_path: "data/mms.db"
  pool_size: 10

redis:
  host: "localhost"
  port: 6379
  db: 0

zmq:
  frontend_port: 5555
  backend_port: 5556
  worker_count: 4
```

### 启动服务

1. 启动Redis服务器：
```bash
redis-server
```

2. 启动仿真引擎：
```bash
python -m src.api.main
```

3. 启动工作进程：
```bash
python -m src.core.worker
```

### API使用示例

#### 提交仿真任务

```bash
curl -X POST "http://localhost:8000/api/v1/simulate" \
     -H "Content-Type: application/json" \
     -d '{
       "ticker": "AAPL",
       "date": "2024-01-15",
       "time_window": ["09:30:00", "16:00:00"],
       "market_depth": 10,
       "mm_strategy": "adaptive",
       "mm_params": {
         "spread": 0.05,
         "inventory_limit": 1000,
         "risk_aversion": 0.1
       },
       "arb_strategy": "statistical",
       "arb_params": {
         "threshold": 0.02,
         "holding_period": 5,
         "max_positions": 10
       }
     }'
```

#### 查询任务状态

```bash
curl "http://localhost:8000/api/v1/status/{task_id}"
```

#### 获取仿真报告

```bash
curl "http://localhost:8000/api/v1/report/{task_id}"
```

## 项目结构

```
09MMS/
├── src/                    # 源代码目录
│   ├── api/               # FastAPI Web接口
│   │   ├── main.py        # 主应用入口
│   │   └── routes/        # API路由定义
│   ├── core/              # 核心业务逻辑
│   │   ├── config.py      # 配置管理
│   │   ├── database.py    # 数据库操作
│   │   ├── simulation.py  # 仿真引擎
│   │   ├── cache.py       # 缓存管理
│   │   ├── load_balancer.py # 负载均衡器
│   │   └── worker.py      # 工作进程
│   └── utils/             # 工具模块
│       ├── logger.py      # 日志管理
│       ├── exceptions.py  # 异常处理
│       └── metrics.py     # 指标收集
├── tests/                 # 测试代码
│   ├── test_core.py       # 核心模块测试
│   ├── test_api.py        # API测试
│   ├── test_utils.py      # 工具模块测试
│   ├── test_database.py   # 数据库测试
│   └── test_integration.py # 集成测试
├── config/                # 配置文件
├── data/                  # 数据存储目录
├── logs/                  # 日志文件目录
├── docs/                  # 项目文档
├── requirements.txt       # Python依赖
├── pytest.ini           # 测试配置
└── README.md             # 项目说明
```

## 开发指南

### 运行测试

```bash
# 运行所有测试
pytest

# 运行特定测试类型
pytest -m unit          # 单元测试
pytest -m integration   # 集成测试
pytest -m slow          # 慢速测试

# 生成覆盖率报告
pytest --cov=src --cov-report=html
```

### 代码质量检查

```bash
# 代码格式化
black src/ tests/

# 代码风格检查
flake8 src/ tests/

# 类型检查
mypy src/
```

### 性能监控

访问 `http://localhost:8000/metrics` 查看系统指标。

### 健康检查

访问 `http://localhost:8000/health` 查看服务健康状态。

## API文档

启动服务后，访问以下地址查看API文档：

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

## 核心概念

### 仿真任务

仿真任务是系统的基本执行单元，包含以下要素：

- **标的资产**: 要仿真的股票或其他金融工具
- **时间窗口**: 仿真的时间范围
- **市场深度**: 订单簿的深度层级
- **策略参数**: 做市商和套利策略的配置

### 策略类型

#### 做市商策略

- **Adaptive**: 自适应做市策略
- **Fixed**: 固定价差做市策略
- **Inventory**: 基于库存的做市策略

#### 套利策略

- **Statistical**: 统计套利策略
- **Pairs**: 配对交易策略
- **Momentum**: 动量套利策略

### 参数校准

系统支持自动校准以下市场参数：

- 价格冲击系数
- 订单到达率
- 取消率
- 波动率
- 买卖价差

## 性能优化

### 缓存策略

- **仿真结果缓存**: 避免重复计算相同参数的仿真
- **市场数据缓存**: 减少外部数据源访问
- **校准参数缓存**: 复用历史校准结果

### 分布式计算

- **负载均衡**: ZeroMQ实现的任务分发
- **工作进程池**: 多进程并行执行仿真任务
- **故障恢复**: 自动检测和重启失败的工作进程

## 监控和运维

### 日志管理

日志文件位于 `logs/` 目录：

- `app.log`: 应用主日志
- `debug.log`: 调试信息
- `error.log`: 错误日志
- `performance.log`: 性能指标

### 指标监控

系统收集以下关键指标：

- 仿真任务执行时间
- 系统资源使用率
- API请求响应时间
- 缓存命中率
- 数据库查询性能

### 故障排除

常见问题及解决方案：

1. **Redis连接失败**
   - 检查Redis服务是否启动
   - 验证连接配置

2. **ZeroMQ通信异常**
   - 检查端口是否被占用
   - 验证防火墙设置

3. **数据库锁定**
   - 检查并发访问
   - 优化事务处理

## 贡献指南

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 联系方式

- 项目维护者: NeuroTrade Nexus 开发团队
- 邮箱: dev@neurotrade-nexus.com
- 项目主页: https://github.com/neurotrade-nexus/09MMS

## 更新日志

### v1.0.0 (2024-12-01)

- 初始版本发布
- 实现核心仿真引擎
- 添加FastAPI Web接口
- 集成ZeroMQ负载均衡
- 支持Redis缓存
- 完整的测试覆盖

---

**注意**: 本项目仅用于研究和教育目的，不构成投资建议。使用本软件进行实际交易的风险由用户自行承担。