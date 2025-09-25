# ReviewGuard 人工审核模组

ReviewGuard是NeuroTrade Nexus交易系统的智能安全阀，负责对交易策略进行人工审核和风险控制。

## 项目架构

本项目采用微服务架构，前后端完全分离：

```
ReviewGuard/
├── frontend/          # Next.js前端应用
│   ├── src/          # 前端源代码
│   ├── package.json  # 前端依赖
│   └── Dockerfile    # 前端Docker配置
├── backend/          # Python FastAPI后端
│   ├── src/          # 后端源代码
│   ├── requirements.txt # 后端依赖
│   └── Dockerfile    # 后端Docker配置
├── docker-compose.yml # 容器编排配置
└── package.json      # 根目录配置（仅用于脚本管理）
```

## 技术栈

### 前端
- **框架**: Next.js 15.4.5
- **UI库**: Radix UI + Tailwind CSS
- **状态管理**: Zustand
- **数据获取**: TanStack Query
- **HTTP客户端**: Axios

### 后端
- **框架**: FastAPI
- **数据库**: SQLite
- **消息队列**: ZeroMQ (PyZMQ)
- **缓存**: Redis
- **认证**: JWT

## 开发环境启动

### 前端开发
```bash
# 进入前端目录
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

### 后端开发
```bash
# 进入后端目录
cd backend

# 安装Python依赖
pip install -r requirements.txt

# 启动后端服务
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

### 使用根目录脚本
```bash
# 启动前端开发服务器
npm run frontend:dev

# 启动后端开发服务器
npm run backend:dev

# 构建前端
npm run frontend:build
```

## Docker部署

### 构建和启动所有服务
```bash
# 构建Docker镜像
docker-compose build

# 启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 停止所有服务
docker-compose down
```

### 服务端口
- **前端**: http://localhost:3000
- **后端API**: http://localhost:8000
- **Redis**: localhost:6379
- **ZeroMQ订阅**: localhost:5555
- **ZeroMQ发布**: localhost:5556

## API接口

### 主要端点
- `GET /api/reviews/pending` - 获取待审核策略列表
- `GET /api/strategies/{strategy_id}/detail` - 获取策略详情
- `POST /api/reviews/{review_id}/decision` - 提交审核决策
- `GET /api/reviews/history` - 获取审核历史
- `GET /api/config/rules` - 获取审核规则配置
- `GET /api/monitor/status` - 系统监控状态

## 环境变量

### 后端环境变量
```bash
APP_ENV=development
REDIS_URL=redis://localhost:6379
DATABASE_PATH=./data/reviewguard.db
ZEROMQ_SUB_PORT=5555
ZEROMQ_PUB_PORT=5556
```

### 前端环境变量
```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## 数据库

项目使用SQLite数据库，主要表结构：
- `strategy_reviews` - 策略审核记录
- `review_decisions` - 审核决策
- `users` - 用户信息
- `risk_assessments` - 风险评估
- `audit_rules` - 审核规则

## ZeroMQ消息

### 订阅频道
- `optimizer.pool.trading` - 接收优化器的交易策略

### 发布频道
- `review.pool.approved` - 发布审核通过的策略

## 开发指南

1. **代码规范**: 遵循ESLint和Prettier配置
2. **提交规范**: 使用Conventional Commits格式
3. **测试**: 前后端都需要编写单元测试
4. **文档**: 重要功能需要添加注释和文档

## 故障排除

### 常见问题
1. **端口冲突**: 确保8000、3000、6379、5555、5556端口未被占用
2. **依赖问题**: 删除node_modules和重新安装
3. **Docker问题**: 检查Docker服务是否正常运行

### 日志查看
```bash
# 查看所有服务日志
docker-compose logs

# 查看特定服务日志
docker-compose logs reviewguard-backend
docker-compose logs reviewguard-frontend
```

## 许可证

本项目为NeuroTrade Nexus系统的一部分，遵循相应的许可证协议。