# 交易执行铁三角 (TradeGuard)

一个基于微服务架构的分布式量化交易执行系统，由交易员(Trader)、风控(Risk Control)、财务(Finance)三个核心模组构成。

## 🏗️ 系统架构

### 核心设计理念
- **化整为零，分而治之**: 将复杂交易系统拆分为8个独立模组
- **高内聚，低耦合**: 通过ZeroMQ消息总线实现模组间通信
- **三环境隔离**: 支持development/staging/production环境严格隔离
- **零配置部署**: 基于Docker的一键部署方案

### 技术栈
- **前端**: React 18 + TypeScript + Tailwind CSS + Vite
- **后端**: Node.js + Express + TypeScript
- **消息队列**: ZeroMQ (PUB/SUB, REQ/REP模式)
- **缓存**: Redis 7.0
- **数据库**: SQLite (轻量级、零配置)
- **容器化**: Docker + Docker Compose
- **图表**: Recharts
- **AI集成**: TradingAgents-CN v3.0

## 📁 项目结构

```
├── src/                          # 前端源码
│   ├── modules/                  # 业务模组
│   │   ├── trader/              # 交易员模组
│   │   ├── risk/                # 风控模组
│   │   ├── finance/             # 财务模组
│   │   └── master-control/      # 总控模组
│   ├── shared/                  # 共享代码
│   │   ├── types/               # 类型定义
│   │   ├── utils/               # 工具函数
│   │   └── services/            # 服务层
│   └── components/              # 通用组件
├── api/                         # 后端API
│   ├── modules/                 # 业务模组API
│   │   ├── trader/              # 交易员API
│   │   ├── risk/                # 风控API
│   │   ├── finance/             # 财务API
│   │   └── master-control/      # 总控API
│   └── shared/                  # 共享后端代码
│       ├── database/            # 数据库配置
│       ├── messaging/           # ZeroMQ消息处理
│       └── middleware/          # 中间件
├── config/                      # 配置文件
│   ├── base.yaml               # 基础配置
│   ├── development.yaml        # 开发环境配置
│   ├── staging.yaml            # 测试环境配置
│   └── production.yaml         # 生产环境配置
├── scripts/                     # 脚本文件
├── .trae/documents/            # 项目文档
└── docker-compose.yml          # Docker编排配置
```

## 🚀 快速开始

### 环境要求
- Node.js 18+
- Redis 7.0+
- Docker & Docker Compose (可选)

### 本地开发

1. **克隆项目并安装依赖**
```bash
git clone <repository-url>
cd 05-07TradeGuard
npm install
```

2. **配置环境变量**
```bash
cp .env.example .env
# 编辑 .env 文件，配置必要的环境变量
```

3. **启动Redis服务**
```bash
# 使用Docker启动Redis
docker run -d --name redis -p 6379:6379 redis:7-alpine

# 或使用本地Redis服务
redis-server
```

4. **启动开发服务器**
```bash
# 同时启动前端和后端开发服务器
npm run dev

# 或分别启动
npm run client:dev  # 前端开发服务器 (http://localhost:5173)
npm run server:dev  # 后端API服务器 (http://localhost:3000)
```

### Docker部署

1. **开发环境**
```bash
# 启动开发环境
docker-compose up -d

# 查看日志
docker-compose logs -f tradeguard-app
```

2. **生产环境**
```bash
# 创建生产环境配置
cp .env.example .env.prod
# 编辑 .env.prod 文件

# 启动生产环境
docker-compose --profile production up -d
```

3. **包含监控的完整部署**
```bash
# 启动包含Prometheus和Grafana的完整监控栈
docker-compose --profile monitoring --profile production up -d
```

## 🔧 开发指南

### 环境管理

系统支持三个环境的严格隔离：

- **development**: 开发环境，支持热重载、详细日志、模拟数据
- **staging**: 准生产环境，用于集成测试和性能测试
- **production**: 生产环境，优化性能、安全加固、监控告警

通过 `APP_ENV` 环境变量切换：
```bash
export APP_ENV=development  # 或 staging, production
```

### 模组开发

每个模组都遵循相同的开发模式：

1. **前端模组** (`src/modules/{module}/`)
   - `components/`: React组件
   - `pages/`: 页面组件
   - `hooks/`: 自定义Hook
   - `services/`: API服务
   - `types/`: 模组特定类型

2. **后端模组** (`api/modules/{module}/`)
   - `routes/`: API路由
   - `controllers/`: 控制器
   - `services/`: 业务逻辑
   - `models/`: 数据模型

### ZeroMQ通信

模组间通信使用ZeroMQ的两种模式：

1. **发布/订阅 (PUB/SUB)**: 一对多广播
```typescript
// 发布消息
publisher.send(['topic.name', JSON.stringify(message)]);

// 订阅消息
subscriber.subscribe('topic.name');
subscriber.on('message', (topic, message) => {
  // 处理消息
});
```

2. **请求/响应 (REQ/REP)**: 一对一服务调用
```typescript
// 发送请求
const response = await requester.send(JSON.stringify(request));

// 处理请求
responder.on('message', async (request) => {
  const response = await processRequest(request);
  responder.send(JSON.stringify(response));
});
```

## 📊 核心功能

### 交易员模组 (Trader)
- 策略包接收和管理
- 风险评估申请
- 资金申请和审批
- TWAP/VWAP智能订单执行
- 实时持仓监控

### 风控模组 (Risk Control)
- 交易前风险评估 (1-10分评分)
- 实时市场监控
- 风险警报发布
- 熔断机制触发

### 财务模组 (Finance)
- 动态资金分配算法
- 预算审批流程
- 账户健康检查
- 盈亏统计分析

### 总控模组 (Master Control)
- 全局状态监控
- 系统模式切换 (牛市/熊市/防御)
- 紧急熔断控制
- 系统健康检查

## 🔒 安全规范

### 数据隔离
- 严禁硬编码敏感信息
- 通过环境变量注入API密钥
- 不同环境使用独立数据库
- 占位数据仅限开发环境

### 访问控制
- 基于角色的权限管理
- JWT令牌认证
- API限流保护
- 请求日志记录

## 📈 监控和日志

### 日志级别
- **development**: DEBUG级别，控制台输出
- **staging**: DEBUG级别，文件输出
- **production**: INFO级别，文件+错误日志分离

### 监控指标
- 系统健康状态
- 交易执行性能
- 风险指标监控
- 资金使用情况
- ZeroMQ消息延迟

### Grafana仪表板
访问 http://localhost:3001 查看监控仪表板
- 默认用户名: admin
- 默认密码: admin123

## 🧪 测试

```bash
# 运行所有测试
npm test

# 运行特定模组测试
npm test -- --grep "trader"

# 生成测试覆盖率报告
npm run test:coverage
```

## 📝 API文档

启动服务后访问 http://localhost:3000/api/docs 查看完整API文档。

## 🤝 贡献指南

1. Fork项目
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add some amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 📞 支持

如有问题或建议，请创建 [Issue](../../issues) 或联系开发团队。