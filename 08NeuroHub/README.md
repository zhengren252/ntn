# 模组八：总控模块 (Master Control Module)

## 项目概述

模组八总控模块是NeuroTrade Nexus交易系统的决策大脑和指挥中心。作为系统的"总司令"，它负责全局监控、模式切换和风险熔断，确保整个交易系统的安全稳定运行。

### 核心特性

- 🎯 **战场仪表盘**: 实时监控牛熊指数、板块轮动、市场杠杆率
- 💰 **资金模式切换**: 根据总资金量自动切换微/低/标准资金模式
- 🚨 **熔断协议**: 极端风险事件下的一键清仓和资产转移
- 🧠 **记忆网络**: 存储历史重大事件处置方案，用于决策参考
- 🔄 **微服务架构**: 基于ZeroMQ的高性能异步通信
- 📊 **实时监控**: Redis状态管理和SQLite持久化存储

## 技术架构

### 前端技术栈
- React 18 + TypeScript
- Ant Design + ECharts
- Tailwind CSS
- Zustand状态管理
- WebSocket实时通信

### 后端技术栈
- Node.js + Express
- Python + FastAPI (计划)
- ZeroMQ消息总线
- Redis缓存
- SQLite数据库

### 部署技术
- Docker + Docker Compose
- 三环境隔离 (development/staging/production)
- Prometheus + Grafana监控

## 快速开始

### 环境要求

- Node.js >= 18.0.0
- npm >= 8.0.0
- Docker >= 20.0.0 (可选)
- Python >= 3.9 (后端开发)

### 安装依赖

```bash
# 安装Node.js依赖
npm install

# 安装Python依赖 (如果需要)
pip install -r requirements.txt
```

### 环境配置

1. 复制环境变量模板:
```bash
cp .env.template .env.development
```

2. 编辑 `.env.development` 文件，填入必要的配置信息

### 开发模式

```bash
# 启动前端和后端开发服务器
npm run dev

# 仅启动前端
npm run client:dev

# 仅启动后端
npm run server:dev
```

### Docker部署

```bash
# 启动所有服务
docker-compose up -d

# 启动包含监控的完整服务
docker-compose --profile monitoring up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f master_control
```

## 项目结构

```
08NeuroHub/
├── src/                    # 前端源码
│   ├── components/         # React组件
│   ├── pages/             # 页面组件
│   ├── hooks/             # 自定义Hooks
│   └── lib/               # 工具库
├── api/                   # 后端API
│   ├── routes/            # 路由定义
│   └── server.ts          # 服务器入口
├── config/                # 配置文件
│   ├── base.yaml          # 基础配置
│   ├── development.yaml   # 开发环境配置
│   ├── staging.yaml       # 测试环境配置
│   └── production.yaml    # 生产环境配置
├── database/              # 数据库相关
│   └── init.sql           # 数据库初始化脚本
├── logs/                  # 日志文件
├── data/                  # 数据存储
├── .trae/documents/       # 项目文档
├── docker-compose.yml     # Docker编排配置
├── Dockerfile            # Docker镜像配置
└── requirements.txt      # Python依赖
```

## 核心功能模块

### 1. 战场仪表盘
- 实时系统状态监控
- 市场指标展示
- 模组健康度检查
- 告警通知管理

### 2. 资金管理
- 资金模式自动切换
- 风险敞口监控
- 预算分配管理
- 资金流向分析

### 3. 熔断控制
- 紧急熔断触发
- 风险事件处理
- 应急预案执行
- 操作日志记录

### 4. 记忆网络
- 历史事件存储
- 相似事件匹配
- 决策模式学习
- 策略优化建议

## API文档

### 核心接口

- `GET /api/status/overview` - 获取系统状态概览
- `POST /api/commands/execute` - 执行控制指令
- `GET /api/memory/events` - 查询历史事件
- `WebSocket /ws/realtime` - 实时数据推送

详细API文档请参考 [技术架构文档](.trae/documents/模组八_总控模块_技术架构文档.md)

## 数据隔离规范

项目严格遵循数据隔离与环境管理规范V1.0：

1. **环境隔离**: development/staging/production三套独立环境
2. **配置管理**: 敏感信息通过环境变量注入，严禁硬编码
3. **数据隔离**: 各环境使用独立的数据库和Redis实例
4. **日志规范**: 分环境的日志级别和输出配置

## 监控和告警

### Prometheus指标
- 系统健康度
- 模组状态
- 风险评分
- 性能指标

### Grafana仪表盘
- 实时监控面板
- 历史趋势分析
- 告警规则配置
- 性能分析图表

## 开发指南

### 代码规范
- TypeScript严格模式
- ESLint代码检查
- Prettier代码格式化
- 组件化开发

### 提交规范
```bash
# 功能开发
git commit -m "feat: 添加战场仪表盘实时监控功能"

# 问题修复
git commit -m "fix: 修复Redis连接超时问题"

# 文档更新
git commit -m "docs: 更新API文档"
```

## 部署指南

### 开发环境
```bash
npm run dev
```

### 测试环境
```bash
APP_ENV=staging docker-compose up -d
```

### 生产环境
```bash
APP_ENV=production docker-compose up -d
```

## 故障排除

### 常见问题

1. **ZeroMQ连接失败**
   - 检查端口是否被占用
   - 确认防火墙设置
   - 验证网络连通性

2. **Redis连接超时**
   - 检查Redis服务状态
   - 验证连接配置
   - 查看网络延迟

3. **数据库锁定**
   - 检查SQLite文件权限
   - 确认WAL模式启用
   - 重启应用服务

## 贡献指南

1. Fork项目
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add some amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建Pull Request

## 许可证

本项目采用MIT许可证 - 详见 [LICENSE](LICENSE) 文件

## 联系方式

- 项目文档: [.trae/documents/](.trae/documents/)
- 技术支持: 请创建Issue
- 邮箱: support@neurotrade.com

---

**注意**: 本项目严格遵循数据隔离与环境管理规范，请确保在正确的环境中进行开发和部署。
