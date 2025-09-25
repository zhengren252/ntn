# 交易执行铁三角 API 文档

## 概述

交易执行铁三角系统提供RESTful API接口，支持交易员、风控和财务三大模组的核心功能。本文档详细描述了所有API端点的使用方法、参数说明和响应格式。

## 基础信息

- **基础URL**: `http://localhost:3000/api`
- **API版本**: v1.0
- **数据格式**: JSON
- **字符编码**: UTF-8
- **认证方式**: Bearer Token (可选)

## 通用响应格式

### 成功响应
```json
{
  "success": true,
  "data": {},
  "message": "操作成功",
  "timestamp": "2024-12-25T12:00:00.000Z"
}
```

### 错误响应
```json
{
  "success": false,
  "error": "错误描述",
  "code": "ERROR_CODE",
  "timestamp": "2024-12-25T12:00:00.000Z"
}
```

### 分页响应
```json
{
  "success": true,
  "data": [],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 100,
    "pages": 5
  }
}
```

## 交易员模组 API

### 策略包管理

#### 创建策略包
```http
POST /api/trader/strategies
```

**请求参数**:
```json
{
  "name": "策略名称",
  "description": "策略描述",
  "version": "1.0.0",
  "parameters": {
    "symbol": "BTCUSDT",
    "timeframe": "1h",
    "stop_loss": 0.02,
    "take_profit": 0.05
  },
  "status": "active"
}
```

**响应示例**:
```json
{
  "success": true,
  "data": {
    "id": 1,
    "name": "策略名称",
    "description": "策略描述",
    "version": "1.0.0",
    "parameters": "{\"symbol\":\"BTCUSDT\",\"timeframe\":\"1h\"}",
    "status": "active",
    "created_at": "2024-12-25T12:00:00.000Z"
  }
}
```

#### 获取策略包列表
```http
GET /api/trader/strategies
```

**查询参数**:
- `page` (可选): 页码，默认1
- `limit` (可选): 每页数量，默认20
- `status` (可选): 策略状态 (active, inactive, testing)
- `search` (可选): 搜索关键词

**响应示例**:
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "name": "策略A",
      "description": "描述",
      "status": "active",
      "created_at": "2024-12-25T12:00:00.000Z"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 1,
    "pages": 1
  }
}
```

#### 获取策略包详情
```http
GET /api/trader/strategies/{id}
```

**路径参数**:
- `id`: 策略包ID

**响应示例**:
```json
{
  "success": true,
  "data": {
    "id": 1,
    "name": "策略A",
    "description": "详细描述",
    "version": "1.0.0",
    "parameters": "{\"symbol\":\"BTCUSDT\"}",
    "status": "active",
    "created_at": "2024-12-25T12:00:00.000Z",
    "updated_at": "2024-12-25T12:00:00.000Z"
  }
}
```

#### 更新策略包
```http
PUT /api/trader/strategies/{id}
```

**请求参数**:
```json
{
  "name": "更新后的策略名称",
  "description": "更新后的描述",
  "parameters": {
    "symbol": "ETHUSDT",
    "timeframe": "4h"
  },
  "status": "inactive"
}
```

#### 删除策略包
```http
DELETE /api/trader/strategies/{id}
```

### 订单管理

#### 创建订单
```http
POST /api/trader/orders
```

**请求参数**:
```json
{
  "strategy_id": 1,
  "symbol": "BTCUSDT",
  "side": "buy",
  "type": "limit",
  "quantity": 1.5,
  "price": 30000,
  "stop_loss": 29000,
  "take_profit": 32000
}
```

**字段说明**:
- `strategy_id`: 关联的策略包ID
- `symbol`: 交易对
- `side`: 买卖方向 (buy, sell)
- `type`: 订单类型 (market, limit, stop)
- `quantity`: 数量
- `price`: 价格 (市价单可为空)
- `stop_loss`: 止损价格 (可选)
- `take_profit`: 止盈价格 (可选)

**响应示例**:
```json
{
  "success": true,
  "data": {
    "id": 1,
    "strategy_id": 1,
    "symbol": "BTCUSDT",
    "side": "buy",
    "type": "limit",
    "quantity": 1.5,
    "price": 30000,
    "status": "pending",
    "created_at": "2024-12-25T12:00:00.000Z"
  }
}
```

#### 获取订单列表
```http
GET /api/trader/orders
```

**查询参数**:
- `strategy_id` (可选): 策略包ID
- `symbol` (可选): 交易对
- `side` (可选): 买卖方向
- `status` (可选): 订单状态
- `page` (可选): 页码
- `limit` (可选): 每页数量

#### 获取订单详情
```http
GET /api/trader/orders/{id}
```

#### 取消订单
```http
DELETE /api/trader/orders/{id}
```

## 风控模组 API

### 风险评估

#### 创建风险评估
```http
POST /api/risk/assessments
```

**请求参数**:
```json
{
  "strategy_id": 1,
  "risk_score": 65,
  "risk_level": "medium",
  "assessment_data": {
    "volatility": 0.25,
    "max_drawdown": 0.08,
    "var_95": 0.12,
    "correlation_btc": 0.85
  },
  "recommendations": [
    "建议设置止损位",
    "监控市场波动",
    "定期调整仓位"
  ]
}
```

**字段说明**:
- `strategy_id`: 关联的策略包ID
- `risk_score`: 风险评分 (0-100)
- `risk_level`: 风险等级 (low, medium, high)
- `assessment_data`: 评估数据对象
- `recommendations`: 建议列表

**响应示例**:
```json
{
  "success": true,
  "data": {
    "id": 1,
    "strategy_id": 1,
    "risk_score": 65,
    "risk_level": "medium",
    "assessment_data": "{\"volatility\":0.25}",
    "recommendations": "[\"建议设置止损位\"]",
    "created_at": "2024-12-25T12:00:00.000Z"
  }
}
```

#### 获取风险评估列表
```http
GET /api/risk/assessments
```

**查询参数**:
- `strategy_id` (可选): 策略包ID
- `risk_level` (可选): 风险等级
- `min_score` (可选): 最小风险评分
- `max_score` (可选): 最大风险评分
- `page` (可选): 页码
- `limit` (可选): 每页数量

#### 获取风险评估详情
```http
GET /api/risk/assessments/{id}
```

### 风险告警

#### 创建风险告警
```http
POST /api/risk/alerts
```

**请求参数**:
```json
{
  "strategy_id": 1,
  "alert_type": "position_limit",
  "severity": "high",
  "message": "持仓超过限制",
  "threshold_value": 100000,
  "current_value": 120000
}
```

**字段说明**:
- `strategy_id`: 关联的策略包ID
- `alert_type`: 告警类型 (position_limit, drawdown, volatility, correlation)
- `severity`: 严重程度 (low, medium, high, critical)
- `message`: 告警消息
- `threshold_value`: 阈值
- `current_value`: 当前值

#### 获取风险告警列表
```http
GET /api/risk/alerts
```

**查询参数**:
- `strategy_id` (可选): 策略包ID
- `alert_type` (可选): 告警类型
- `severity` (可选): 严重程度
- `status` (可选): 状态 (active, resolved)
- `page` (可选): 页码
- `limit` (可选): 每页数量

#### 解决风险告警
```http
PUT /api/risk/alerts/{id}/resolve
```

**请求参数**:
```json
{
  "resolution_notes": "已调整仓位，风险已控制"
}
```

## 财务模组 API

### 预算申请

#### 创建预算申请
```http
POST /api/finance/budget-requests
```

**请求参数**:
```json
{
  "strategy_id": 1,
  "requested_amount": 100000,
  "purpose": "量化交易策略执行",
  "justification": "基于历史回测数据，预期年化收益率15%",
  "duration_months": 12,
  "risk_level": "medium"
}
```

**字段说明**:
- `strategy_id`: 关联的策略包ID
- `requested_amount`: 申请金额
- `purpose`: 用途说明
- `justification`: 申请理由
- `duration_months`: 使用期限（月）
- `risk_level`: 风险等级

**响应示例**:
```json
{
  "success": true,
  "data": {
    "id": 1,
    "strategy_id": 1,
    "requested_amount": 100000,
    "purpose": "量化交易策略执行",
    "status": "pending",
    "created_at": "2024-12-25T12:00:00.000Z"
  }
}
```

#### 获取预算申请列表
```http
GET /api/finance/budget-requests
```

**查询参数**:
- `strategy_id` (可选): 策略包ID
- `status` (可选): 状态 (pending, approved, rejected)
- `min_amount` (可选): 最小金额
- `max_amount` (可选): 最大金额
- `page` (可选): 页码
- `limit` (可选): 每页数量

#### 批准预算申请
```http
PUT /api/finance/budget-requests/{id}/approve
```

**请求参数**:
```json
{
  "approved_amount": 80000,
  "approval_notes": "部分批准，降低风险"
}
```

#### 拒绝预算申请
```http
PUT /api/finance/budget-requests/{id}/reject
```

**请求参数**:
```json
{
  "rejection_reason": "风险评估不通过"
}
```

### 资金分配

#### 创建资金分配
```http
POST /api/finance/fund-allocations
```

**请求参数**:
```json
{
  "budget_request_id": 1,
  "allocated_amount": 60000,
  "allocation_type": "initial",
  "allocation_date": "2024-12-25",
  "notes": "初始资金分配"
}
```

**字段说明**:
- `budget_request_id`: 关联的预算申请ID
- `allocated_amount`: 分配金额
- `allocation_type`: 分配类型 (initial, additional, adjustment)
- `allocation_date`: 分配日期
- `notes`: 备注

#### 获取资金分配列表
```http
GET /api/finance/fund-allocations
```

**查询参数**:
- `budget_request_id` (可选): 预算申请ID
- `allocation_type` (可选): 分配类型
- `status` (可选): 状态
- `page` (可选): 页码
- `limit` (可选): 每页数量

### 账户管理

#### 创建交易账户
```http
POST /api/finance/accounts
```

**请求参数**:
```json
{
  "account_name": "主交易账户",
  "account_type": "trading",
  "initial_balance": 1000000,
  "currency": "USDT",
  "exchange": "binance",
  "status": "active"
}
```

**字段说明**:
- `account_name`: 账户名称
- `account_type`: 账户类型 (trading, reserve, settlement)
- `initial_balance`: 初始余额
- `currency`: 币种
- `exchange`: 交易所
- `status`: 状态

#### 获取账户列表
```http
GET /api/finance/accounts
```

**查询参数**:
- `account_type` (可选): 账户类型
- `currency` (可选): 币种
- `exchange` (可选): 交易所
- `status` (可选): 状态

#### 更新账户余额
```http
PUT /api/finance/accounts/{id}/balance
```

**请求参数**:
```json
{
  "balance_change": -5000,
  "transaction_type": "trade",
  "description": "交易支出"
}
```

## 错误代码说明

| 错误代码 | HTTP状态码 | 描述 |
|---------|-----------|------|
| VALIDATION_ERROR | 400 | 请求参数验证失败 |
| UNAUTHORIZED | 401 | 未授权访问 |
| FORBIDDEN | 403 | 权限不足 |
| NOT_FOUND | 404 | 资源不存在 |
| CONFLICT | 409 | 资源冲突 |
| INTERNAL_ERROR | 500 | 服务器内部错误 |
| DATABASE_ERROR | 500 | 数据库错误 |
| EXTERNAL_API_ERROR | 502 | 外部API调用失败 |

## 限流说明

为保证系统稳定性，API实施以下限流策略：

- **普通接口**: 每分钟最多100次请求
- **查询接口**: 每分钟最多200次请求
- **创建/更新接口**: 每分钟最多50次请求

超出限制时返回HTTP 429状态码。

## 认证说明

系统支持Bearer Token认证（可选）：

```http
Authorization: Bearer <your-token>
```

## 示例代码

### JavaScript (Node.js)

```javascript
const axios = require('axios');

const api = axios.create({
  baseURL: 'http://localhost:3000/api',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer your-token' // 可选
  }
});

// 创建策略
async function createStrategy() {
  try {
    const response = await api.post('/trader/strategies', {
      name: '测试策略',
      description: '这是一个测试策略',
      parameters: {
        symbol: 'BTCUSDT',
        timeframe: '1h'
      }
    });
    
    console.log('策略创建成功:', response.data);
  } catch (error) {
    console.error('创建失败:', error.response.data);
  }
}

// 获取策略列表
async function getStrategies() {
  try {
    const response = await api.get('/trader/strategies', {
      params: {
        page: 1,
        limit: 10,
        status: 'active'
      }
    });
    
    console.log('策略列表:', response.data);
  } catch (error) {
    console.error('获取失败:', error.response.data);
  }
}
```

### Python

```python
import requests
import json

class TradeGuardAPI:
    def __init__(self, base_url='http://localhost:3000/api', token=None):
        self.base_url = base_url
        self.headers = {
            'Content-Type': 'application/json'
        }
        if token:
            self.headers['Authorization'] = f'Bearer {token}'
    
    def create_strategy(self, strategy_data):
        url = f'{self.base_url}/trader/strategies'
        response = requests.post(url, json=strategy_data, headers=self.headers)
        return response.json()
    
    def get_strategies(self, params=None):
        url = f'{self.base_url}/trader/strategies'
        response = requests.get(url, params=params, headers=self.headers)
        return response.json()
    
    def create_order(self, order_data):
        url = f'{self.base_url}/trader/orders'
        response = requests.post(url, json=order_data, headers=self.headers)
        return response.json()

# 使用示例
api = TradeGuardAPI()

# 创建策略
strategy = {
    'name': 'Python测试策略',
    'description': '使用Python创建的测试策略',
    'parameters': {
        'symbol': 'ETHUSDT',
        'timeframe': '4h'
    }
}

result = api.create_strategy(strategy)
print('策略创建结果:', result)
```

## 更新日志

### v1.0.0 (2024-12-25)
- 初始版本发布
- 支持交易员、风控、财务三大模组API
- 实现策略包、订单、风险评估、预算申请等核心功能
- 提供完整的错误处理和响应格式

## 联系方式

如有问题或建议，请联系开发团队：
- 邮箱: dev@tradeguard.com
- 文档更新: 请查看项目仓库
- 技术支持: 工作日 9:00-18:00