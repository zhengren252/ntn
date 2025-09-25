# TACoreService 验收测试套件

## 概述

本测试套件是为 TACoreService（AI核心引擎）设计的全面验收测试方案，基于《TACoreService 最终技术规格与实施指南 (V1.0 优化整合版)》文档开发。

测试计划ID: `ACCEPTANCE-TEST-PLAN-M12-TACORESVC-V1.0`

## 测试范围

### 核心测试套件

1. **ZeroMQ业务API测试** (`ZMQ_BUSINESS_API`)
   - 市场扫描接口 (`scan.market`)
   - 订单执行接口 (`execute.order`)
   - 风险评估接口 (`evaluate.risk`)
   - 无效方法处理测试
   - Lazy Pirate Pattern 可靠性测试

2. **HTTP监控API测试** (`HTTP_MONITORING_API`)
   - 服务状态接口 (`GET /status`)
   - 工作进程列表 (`GET /workers`)
   - 日志获取接口 (`GET /logs`)

3. **负载均衡与可扩展性测试** (`LOAD_BALANCING`)
   - 请求分发验证
   - 水平扩展能力测试
   - 性能压力测试

4. **高可用性与故障转移测试** (`HIGH_AVAILABILITY`)
   - 工作进程故障转移
   - 客户端自动重试 (Lazy Pirate)
   - 服务恢复能力测试

5. **数据持久化验证测试** (`DATA_PERSISTENCE`)
   - SQLite 请求日志持久化
   - Redis 缓存机制验证
   - 数据库连接性测试

## 环境要求

### 系统要求
- Python 3.8+
- Docker & Docker Compose
- 至少 4GB 可用内存
- 网络端口 5555 (ZMQ) 和 8080 (HTTP) 可用

### 依赖服务
- TACoreService (主服务)
- Redis (缓存)
- SQLite (日志存储)
- Worker 进程 (业务处理)

## 快速开始

### 1. 环境设置

```bash
# 进入测试目录
cd acceptance_tests

# 运行环境设置脚本
python setup.py
```

### 2. 启动服务

```bash
# 返回项目根目录
cd ..

# 启动所有服务
docker-compose up -d

# 检查服务状态
docker-compose ps
```

### 3. 运行测试

#### 快速测试（基本功能验证）
```bash
cd acceptance_tests
python quick_test.py
```

#### 完整验收测试
```bash
# 运行所有测试套件
python run_tests.py

# 运行特定测试套件
python run_tests.py --suites ZMQ_BUSINESS_API HTTP_MONITORING_API

# 详细输出模式
python run_tests.py --verbose

# 不生成报告
python run_tests.py --no-reports
```

## 测试配置

### 配置文件
- `config.py` - 主要测试配置
- `test_config.py` - 环境特定配置（由setup.py生成）

### 关键配置项
```python
# 服务端点
ZMQ_ENDPOINT = "tcp://localhost:5555"
HTTP_ENDPOINT = "http://localhost:8080"

# 超时设置
TEST_TIMEOUT = 30
REQUEST_TIMEOUT = 10
RETRY_ATTEMPTS = 3

# 负载测试
CONCURRENT_REQUESTS = 10
LOAD_TEST_DURATION = 30
```

## 测试报告

测试完成后，会在 `reports/` 目录生成以下报告：

- `test_report.html` - HTML格式详细报告
- `test_report.json` - JSON格式结构化数据
- `test_report.txt` - 纯文本摘要报告

### 报告内容
- 测试执行摘要
- 每个测试用例的详细结果
- 性能指标和统计数据
- 失败测试的错误信息
- 验证点检查结果

## 目录结构

```
acceptance_tests/
├── README.md                 # 本文档
├── setup.py                  # 环境设置脚本
├── requirements.txt          # Python依赖
├── config.py                 # 测试配置
├── run_tests.py             # 主测试运行器
├── quick_test.py            # 快速测试脚本
├── utils/                   # 测试工具
│   ├── __init__.py
│   ├── test_logger.py       # 测试日志
│   ├── test_helpers.py      # 测试辅助函数
│   └── report_generator.py  # 报告生成器
├── tests/                   # 测试套件
│   ├── __init__.py
│   ├── test_zmq_business_api.py      # ZMQ业务API测试
│   ├── test_http_monitoring_api.py   # HTTP监控API测试
│   ├── test_load_balancing.py        # 负载均衡测试
│   ├── test_high_availability.py     # 高可用性测试
│   └── test_data_persistence.py      # 数据持久化测试
├── reports/                 # 测试报告输出
├── logs/                    # 测试日志
└── data/                    # 测试数据
```

## 测试用例详情

### ZMQ业务API测试

| 测试用例ID | 测试内容 | 验证点 |
|-----------|----------|--------|
| ZMQ-API-01 | scan.market 成功路径 | 响应状态、request_id匹配、opportunities数组 |
| ZMQ-API-02 | execute.order 成功路径 | 响应状态、order_id非空 |
| ZMQ-API-03 | evaluate.risk 成功路径 | risk_score数字、risk_level枚举值 |
| ZMQ-API-04 | 无效方法测试 | 错误状态、UNKNOWN_ACTION错误码 |

### HTTP监控API测试

| 测试用例ID | 测试内容 | 验证点 |
|-----------|----------|--------|
| HTTP-API-01 | GET /status | HTTP 200、JSON结构、关键字段 |
| HTTP-API-02 | GET /workers | HTTP 200、数组结构、worker信息 |
| HTTP-API-03 | GET /logs | HTTP 200、条数限制、级别过滤 |

### 负载均衡测试

| 测试用例ID | 测试内容 | 验证点 |
|-----------|----------|--------|
| LB-01 | 请求分发验证 | 请求均匀分发到各worker |
| SCALE-01 | 水平扩展能力 | 增加worker后性能提升 |

### 高可用性测试

| 测试用例ID | 测试内容 | 验证点 |
|-----------|----------|--------|
| HA-01 | 工作进程故障转移 | 服务不中断、状态正确反映 |
| HA-02 | 客户端自动重试 | 超时检测、重连重试、最终成功 |

### 数据持久化测试

| 测试用例ID | 测试内容 | 验证点 |
|-----------|----------|--------|
| DATA-01 | SQLite日志持久化 | 记录存在、ID匹配、状态正确 |
| DATA-02 | Redis缓存机制 | 缓存命中、响应时间改善 |

## 故障排除

### 常见问题

1. **连接超时**
   - 检查服务是否启动：`docker-compose ps`
   - 检查端口占用：`netstat -an | findstr :5555`
   - 增加超时时间：修改 `config.py` 中的 `REQUEST_TIMEOUT`

2. **Docker服务异常**
   - 重启服务：`docker-compose restart`
   - 查看日志：`docker-compose logs tacore_service`
   - 清理重建：`docker-compose down && docker-compose up -d`

3. **依赖安装失败**
   - 升级pip：`python -m pip install --upgrade pip`
   - 使用国内源：`pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/`

4. **测试失败**
   - 查看详细日志：`logs/test_*.log`
   - 运行单个测试：修改 `run_tests.py` 中的测试选择
   - 检查服务健康状态：`python quick_test.py`

### 调试模式

```python
# 在测试文件中启用调试
import logging
logging.basicConfig(level=logging.DEBUG)

# 增加详细输出
test_logger.set_level("DEBUG")
```

## 性能基准

### 预期性能指标

- **ZMQ请求响应时间**: < 100ms (95th percentile)
- **HTTP API响应时间**: < 50ms (95th percentile)
- **并发处理能力**: 100+ requests/second
- **故障恢复时间**: < 5 seconds
- **内存使用**: < 512MB per worker

### 负载测试参数

- **并发请求数**: 10-50
- **测试持续时间**: 30-300 seconds
- **Worker扩展**: 2-8 processes

## 扩展测试

### 添加新测试用例

1. 在相应的测试文件中添加新方法
2. 遵循命名约定：`test_<功能>_<场景>()`
3. 使用统一的返回格式
4. 添加适当的验证点

### 自定义测试套件

```python
# 创建新的测试套件类
class CustomTestSuite:
    def __init__(self):
        self.logger = TestLogger()
        self.helpers = TestHelpers()
    
    def run_all_tests(self):
        # 实现测试逻辑
        pass
```

## 联系信息

如有问题或建议，请联系开发团队或查看项目文档。

---

**版本**: 1.0  
**更新日期**: 2024年  
**兼容性**: TACoreService V1.0+