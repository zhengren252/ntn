# NeuroTrade Nexus (NTN) - 信息源爬虫模组

## 模组二：Info Crawler Module

### 项目概述

信息源爬虫模组是NeuroTrade Nexus系统的核心组件，负责从无API的信息源（网页、Telegram频道等）抓取金融数据，并通过ZeroMQ消息总线分发给其他模组。

### 核心设计理念

- **微服务架构**：独立部署，松耦合设计
- **ZeroMQ消息总线**：高性能异步通信
- **三环境隔离**：development/staging/production严格分离
- **Docker容器化**：标准化部署和运维
- **数据质量保证**：多层验证和清洗机制

### 技术栈

- **Python 3.11+**：主要开发语言
- **Scrapy**：网页爬虫框架
- **Telethon**：Telegram API客户端
- **ZeroMQ**：消息队列通信
- **Redis**：缓存和会话存储
- **SQLite**：本地数据存储
- **Flask**：API服务框架
- **Docker**：容器化部署

### 项目结构

```
02DataSpider/
├── app/                    # 应用核心代码
│   ├── config/            # 配置管理
│   ├── crawlers/          # 爬虫模块
│   ├── processors/        # 数据处理
│   ├── api/              # Flask API
│   ├── utils/            # 工具函数
│   └── zmq_client/       # ZeroMQ客户端
├── config/               # 配置文件
├── logs/                 # 日志文件
├── data/                 # 数据存储
├── tests/                # 测试代码
├── scripts/              # 脚本工具
├── docker/               # Docker配置
├── main.py              # 主入口文件
├── requirements.txt     # Python依赖
└── README.md           # 项目说明
```

### 依赖管理

所有依赖库安装在 `D:\yilai\core_lib` 目录，确保环境隔离：

```bash
# 安装依赖
pip install --target "D:\yilai\core_lib" -r requirements.txt
```

### 快速开始

#### 1. 环境准备

```bash
# 克隆项目
cd "E:\NeuroTrade Nexus (NTN)\02DataSpider"

# 安装依赖
pip install --target "D:\yilai\core_lib" -r requirements.txt
```

#### 2. 配置设置

```bash
# 复制配置模板
cp config/development.yml.template config/development.yml

# 编辑配置文件
# 设置ZeroMQ地址、Redis连接、Telegram API等
```

#### 3. 启动服务

```bash
# 开发环境 - 启动所有服务
python main.py --env development --mode all

# 仅启动爬虫服务
python main.py --env development --mode crawler

# 仅启动API服务
python main.py --env development --mode api

# 生产环境
python main.py --env production --mode all
```

### 核心功能

#### 1. 网页爬虫 (Scrapy)
- 支持JavaScript渲染
- 反爬虫策略
- 分布式爬取
- 数据去重

#### 2. Telegram监听 (Telethon)
- 实时消息监听
- 关键词过滤
- 多频道支持
- 消息去重

#### 3. 数据处理
- 数据清洗和验证
- 格式标准化
- 质量评分
- 异常检测

#### 4. ZeroMQ通信
- 发布crawler.news主题
- 高性能异步通信
- 消息持久化
- 负载均衡

#### 5. API接口
- 监控面板
- 配置管理
- 健康检查
- 性能指标

### 环境配置

#### Development (开发环境)
- 调试模式开启
- 详细日志输出
- 本地数据存储
- 快速重启

#### Staging (测试环境)
- 生产级配置
- 性能监控
- 数据备份
- 集成测试

#### Production (生产环境)
- 高可用部署
- 监控告警
- 数据持久化
- 安全加固

### Docker部署

```bash
# 构建镜像
docker build -t ntn-crawler .

# 运行容器
docker-compose up -d

# 查看日志
docker-compose logs -f
```

### 监控和运维

- **健康检查**：HTTP端点监控服务状态
- **性能指标**：Prometheus metrics导出
- **日志聚合**：结构化日志输出
- **告警通知**：异常情况自动通知

### 开发规范

1. **代码风格**：遵循PEP 8规范
2. **测试覆盖**：单元测试覆盖率 > 80%
3. **文档更新**：代码变更同步更新文档
4. **版本管理**：语义化版本控制
5. **安全审计**：定期安全扫描

### 故障排查

#### 常见问题

1. **ZeroMQ连接失败**
   - 检查网络连接
   - 验证端口配置
   - 查看防火墙设置

2. **爬虫被封禁**
   - 调整请求频率
   - 更换User-Agent
   - 使用代理池

3. **Telegram API限制**
   - 检查API配额
   - 调整请求间隔
   - 验证账号状态

#### 日志查看

```bash
# 查看实时日志
tail -f logs/crawler.log

# 查看错误日志
grep ERROR logs/crawler.log

# 查看性能日志
grep PERFORMANCE logs/crawler.log
```

### 贡献指南

1. Fork项目仓库
2. 创建功能分支
3. 提交代码变更
4. 编写测试用例
5. 提交Pull Request

### 许可证

Copyright © 2025 NeuroTrade Nexus Team. All rights reserved.

---

**注意**：本项目严格遵循NeuroTrade Nexus系统全局规范，任何修改都必须符合核心设计理念和技术标准。