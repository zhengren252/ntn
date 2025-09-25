# NeuroTrade Nexus (NTN) - AI智能体驱动交易系统

[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://python.org)
[![TypeScript](https://img.shields.io/badge/TypeScript-4.0%2B-blue.svg)](https://typescriptlang.org)
[![Docker](https://img.shields.io/badge/Docker-20.10%2B-blue.svg)](https://docker.com)

## 项目概述

NeuroTrade Nexus (NTN) 是一个基于微服务架构的AI智能体驱动交易系统，采用14个专业化模组构建，实现了人机协作的智能化交易决策与执行平台。

## 核心特性

- 🤖 **AI智能体驱动**: 基于先进的人工智能算法进行交易决策
- 🏗️ **微服务架构**: 14个独立模组，单一职责，高度解耦
- 🔒 **多层风控体系**: 资金安全保障，异常人工介入机制
- 📊 **实时数据处理**: 高频数据采集与分析
- 🚀 **高性能执行**: 低延迟交易执行引擎
- 🔍 **全链路监控**: 完整的可观测性解决方案

## 系统架构

### 14模组详细功能清单

| 模组ID | 模组名称 | 核心职责 | 技术栈 |
|--------|----------|----------|--------|
| 01 | APIForge | API统一管理工厂 | FastAPI, Python |
| 02 | DataSpider | 信息源爬虫 | Scrapy, Python |
| 03 | ScanPulse | 扫描器 | Python, Redis |
| 04 | OptiCore | 策略优化 | Python, NumPy |
| 05-07 | TradeGuard | 交易执行铁三角 | Python, ZeroMQ |
| 08 | NeuroHub | 总控中心 | React, TypeScript |
| 09 | MMS | 市场微结构仿真引擎 | Python, SQLite |
| 10 | ReviewGuard | 人工审核模块 | React, TypeScript |
| 11 | ASTSConsole | 智能化指挥中心 | React, TypeScript |
| 12 | TACoreService | 交易代理核心服务 | Python, Cython |
| 13 | AIStrategyAssistant | AI策略研究助手 | Python, TensorFlow |
| 14 | ObservabilityCenter | 可观测性中心 | Prometheus, Grafana |

## 快速开始

### 环境要求

- **操作系统**: Ubuntu Server 24.04 LTS 64bit (推荐)
- **Docker**: 20.10+
- **Docker Compose**: 3.8+
- **Python**: 3.8+
- **Node.js**: 16+
- **内存**: 8GB+ (推荐16GB)
- **存储**: 50GB+ SSD

### 安装部署

1. **克隆仓库**
```bash
git clone https://github.com/wufayuzhi/NeuroTrade-Nexus-NTN.git
cd NeuroTrade-Nexus-NTN
```

2. **环境配置**
```bash
# 复制环境变量模板
cp .env.example .env

# 编辑配置文件
vim .env
```

3. **Docker部署**
```bash
# 构建所有服务
docker-compose build

# 启动服务
docker-compose up -d

# 查看服务状态
docker-compose ps
```

4. **验证部署**
```bash
# 运行健康检查
python run_ntn_tests.py

# 查看服务日志
docker-compose logs -f
```

## 开发指南

### 代码规范

- **Python**: 遵循 PEP 8 规范
- **TypeScript**: 启用严格模式，使用 ESLint + Prettier
- **测试覆盖率**: 最低80%
- **提交规范**: 使用 Conventional Commits

### 测试策略

```bash
# 单元测试
pytest tests/unit/

# 集成测试
pytest tests/integration/

# 端到端测试
python 05-07TradeGuard/docker_deployment_test.py
```

### 模组开发

每个模组都包含以下标准结构：

```
XX-ModuleName/
├── src/                 # 源代码
├── tests/              # 测试文件
├── config/             # 配置文件
├── docs/               # 文档
├── Dockerfile          # Docker构建文件
├── requirements.txt    # Python依赖
├── package.json        # Node.js依赖 (如适用)
└── README.md          # 模组说明
```

## 通信协议

### 消息格式规范

所有模组间通信必须遵循统一的JSON格式：

```json
{
  "timestamp": "2025-01-01T00:00:00Z",
  "request_id": "uuid-string",
  "success": true,
  "data": {},
  "error": null
}
```

### 通信方式

- **ZeroMQ**: 模组间低延迟异步消息传递
- **HTTP REST API**: 同步服务调用接口
- **WebSocket**: 实时数据推送

## 监控与运维

### 健康检查

```bash
# 系统整体健康检查
curl http://localhost:8080/health

# 单个模组健康检查
curl http://localhost:8001/api/v1/health  # APIForge
curl http://localhost:8002/api/v1/health  # DataSpider
# ... 其他模组
```

### 日志管理

- **日志级别**: DEBUG, INFO, WARNING, ERROR, CRITICAL
- **日志格式**: 结构化JSON格式
- **日志聚合**: 使用ELK Stack或类似方案

### 性能监控

- **指标收集**: Prometheus
- **可视化**: Grafana
- **告警**: AlertManager

## 安全考虑

- 🔐 **API认证**: JWT Token + API Key
- 🛡️ **数据加密**: TLS 1.3 传输加密
- 🔒 **访问控制**: RBAC权限模型
- 📝 **审计日志**: 完整的操作审计链
- 🚨 **异常检测**: 实时风险监控

## 贡献指南

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

### 提交规范

```
type(scope): description

[optional body]

[optional footer]
```

类型包括：
- `feat`: 新功能
- `fix`: 修复bug
- `docs`: 文档更新
- `style`: 代码格式调整
- `refactor`: 代码重构
- `test`: 测试相关
- `chore`: 构建过程或辅助工具的变动

## 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 联系方式

- **项目维护者**: wufayuzhi
- **邮箱**: [your-email@example.com]
- **问题反馈**: [GitHub Issues](https://github.com/wufayuzhi/NeuroTrade-Nexus-NTN/issues)

## 更新日志

查看 [CHANGELOG.md](CHANGELOG.md) 了解版本更新历史。

---

**注意**: 本系统仅供学习和研究使用，实际交易请谨慎评估风险。