# 模组13: AIStrategyAssistant

AI策略研究助手 - 提供智能策略分析、回测和优化建议

## 功能特性

- RESTful API服务
- ZeroMQ异步消息通信
- Docker容器化部署
- 健康检查和监控
- 配置管理
- 日志记录

## 快速开始

### 环境要求

- Python 3.9+
- Docker (可选)
- Redis
- PostgreSQL (可选)

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置环境

1. 复制环境变量模板:
```bash
cp config/.env.example .env
```

2. 编辑`.env`文件，填入实际配置值

### 运行应用

#### 直接运行
```bash
python main.py
```

#### Docker运行
```bash
# 构建镜像
docker build -t 模组13:-aistrategyassistant .

# 运行容器
docker run -p 8000:8000 -p 5555:5555 模组13:-aistrategyassistant
```

## API文档

启动应用后，访问以下地址查看API文档:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 主要接口

### 健康检查
```
GET /health
```

### 消息处理
```
POST /api/message
```

## ZeroMQ通信

模组通过ZeroMQ进行异步消息通信，默认端口5555。

## 目录结构

```
模组13: AIStrategyAssistant/
├── main.py              # 主程序入口
├── requirements.txt     # Python依赖
├── Dockerfile          # Docker构建文件
├── README.md           # 说明文档
├── config/             # 配置目录
│   ├── config.py       # 配置管理
│   └── .env.example    # 环境变量模板
├── src/                # 源代码目录
├── tests/              # 测试目录
├── logs/               # 日志目录
└── data/               # 数据目录
```

## 开发指南

### 代码规范

- 遵循PEP 8代码风格
- 使用类型注解
- 编写单元测试
- 添加适当的文档字符串

### 测试

```bash
# 运行测试
pytest tests/

# 生成覆盖率报告
pytest --cov=src tests/
```

## 部署

### Docker Compose

参考项目根目录的`docker-compose.yml`文件进行整体部署。

### 监控

- 健康检查: `/health`
- 指标收集: Prometheus兼容
- 日志聚合: 结构化日志输出

## 故障排除

### 常见问题

1. **端口冲突**: 检查8000和5555端口是否被占用
2. **依赖安装失败**: 确保Python版本正确，使用虚拟环境
3. **配置错误**: 检查`.env`文件配置是否正确

### 日志查看

```bash
# 查看应用日志
tail -f logs/app.log

# Docker容器日志
docker logs <container_id>
```

## 支持

如有问题，请联系开发团队或查看项目文档。