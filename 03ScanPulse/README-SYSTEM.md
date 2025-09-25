# AI智能体驱动交易系统 V3.5 - 系统集成部署指南

## 概述

本文档介绍如何使用 `docker-compose.system.yml` 部署完整的AI智能体驱动交易系统V3.5，包含全部12个模组的统一编排。

## 系统架构

### 核心服务层 (2个)
- **TACoreService**: TradingAgents-CN核心服务，提供统一的交易智能体接口
- **Redis**: 缓存服务，提供高性能数据存储和消息队列

### 业务模组层 (11个)
1. **API Factory** (端口: 8001) - API工厂模组
2. **Crawler** (端口: 8002) - 爬虫模组
3. **Scanner** (端口: 8003) - 扫描器模组
4. **Trader** (端口: 8004) - 交易员模组
5. **Risk Manager** (端口: 8005) - 风控模组
6. **Portfolio** (端口: 8006) - 投资组合模组
7. **Notifier** (端口: 8007) - 通知模组
8. **Analytics** (端口: 8008) - 数据分析模组
9. **Backtester** (端口: 8009) - 回测模组
10. **Web UI** (端口: 3000) - 用户界面模组
11. **Monitor** (端口: 8011, 9090) - 监控模组

## 快速启动

### 方法一：使用启动脚本 (推荐)

**Windows:**
```bash
.\start-system.bat
```

**Linux/macOS:**
```bash
chmod +x start-system.sh
./start-system.sh
```

### 方法二：手动启动

```bash
# 停止现有服务
docker-compose -f docker-compose.system.yml down

# 启动完整系统
docker-compose -f docker-compose.system.yml up --build
```

### 方法三：后台运行

```bash
# 后台启动所有服务
docker-compose -f docker-compose.system.yml up -d --build

# 查看服务状态
docker-compose -f docker-compose.system.yml ps

# 查看日志
docker-compose -f docker-compose.system.yml logs -f
```

## 系统状态检查

### 使用状态检查脚本

```bash
python check-system-status.py
```

该脚本会检查所有12个模组的健康状态，并生成详细的状态报告。

### 手动检查关键服务

```bash
# 检查TACoreService
curl -X POST http://localhost:5555 -d '{"method":"health.check"}'

# 检查Redis
redis-cli ping

# 检查Web UI
curl http://localhost:3000

# 检查API Factory
curl http://localhost:8001/health
```

## 访问地址

| 服务 | 地址 | 说明 |
|------|------|------|
| Web UI | http://localhost:3000 | 主要用户界面 |
| API Factory | http://localhost:8001 | API网关 |
| Scanner | http://localhost:8003 | 扫描器服务 |
| Monitor | http://localhost:9090 | Prometheus监控 |
| TACoreService | tcp://localhost:5555 | ZMQ核心服务 |
| Redis | localhost:6379 | 缓存服务 |

## 服务依赖关系

```
TACoreService (核心)
├── Redis (缓存)
└── 业务模组
    ├── API Factory → Web UI
    ├── Scanner → Trader
    ├── Trader → Risk Manager
    ├── Risk Manager → Portfolio
    └── All → Monitor
```

## 环境变量配置

### 核心服务
- `SERVICE_ENV`: 服务环境 (production/staging/development)
- `BIND_ADDRESS`: TACoreService绑定地址
- `WORKER_COUNT`: 工作进程数量

### 业务模组
- `MODULE_ENV`: 模组环境
- `TACORE_SERVICE_URL`: TACoreService连接地址
- `REDIS_URL`: Redis连接地址

## 日志管理

所有服务的日志都存储在 `./logs/` 目录下：

```
logs/
├── tacore/          # TACoreService日志
├── api_factory/     # API Factory日志
├── crawler/         # 爬虫日志
├── scanner/         # 扫描器日志
├── trader/          # 交易员日志
├── risk_manager/    # 风控日志
├── portfolio/       # 投资组合日志
├── notifier/        # 通知日志
├── analytics/       # 数据分析日志
├── backtester/      # 回测日志
├── web_ui/          # Web UI日志
└── monitor/         # 监控日志
```

## 故障排除

### 常见问题

1. **端口冲突**
   ```bash
   # 检查端口占用
   netstat -tulpn | grep :5555
   
   # 停止冲突服务
   docker-compose -f docker-compose.system.yml down
   ```

2. **服务启动失败**
   ```bash
   # 查看特定服务日志
   docker-compose -f docker-compose.system.yml logs tacore_service
   
   # 重启特定服务
   docker-compose -f docker-compose.system.yml restart tacore_service
   ```

3. **健康检查失败**
   ```bash
   # 检查服务状态
   docker-compose -f docker-compose.system.yml ps
   
   # 查看健康检查日志
   docker inspect <container_name> | grep Health
   ```

### 性能优化

1. **调整工作进程数量**
   ```yaml
   environment:
     - WORKER_COUNT=8  # 根据CPU核心数调整
   ```

2. **内存限制**
   ```yaml
   deploy:
     resources:
       limits:
         memory: 1G
       reservations:
         memory: 512M
   ```

## 升级和维护

### 滚动更新

```bash
# 更新单个服务
docker-compose -f docker-compose.system.yml up -d --no-deps --build tacore_service

# 更新所有服务
docker-compose -f docker-compose.system.yml up -d --build
```

### 数据备份

```bash
# 备份Redis数据
docker exec trading_redis redis-cli BGSAVE

# 备份日志
tar -czf logs_backup_$(date +%Y%m%d).tar.gz logs/
```

### 清理资源

```bash
# 停止并删除所有容器
docker-compose -f docker-compose.system.yml down

# 清理未使用的镜像
docker image prune -f

# 清理未使用的卷
docker volume prune -f
```

## 监控和告警

### Prometheus指标

访问 http://localhost:9090 查看系统指标：

- 服务健康状态
- 请求响应时间
- 错误率统计
- 资源使用情况

### 自定义告警

在 `docker/prometheus.yml` 中配置告警规则：

```yaml
rule_files:
  - "alert_rules.yml"

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093
```

## 安全注意事项

1. **网络隔离**: 所有服务运行在独立的Docker网络中
2. **端口暴露**: 仅暴露必要的服务端口
3. **环境变量**: 敏感信息使用环境变量管理
4. **访问控制**: 生产环境建议配置防火墙规则

## 技术支持

如遇到问题，请：

1. 运行 `python check-system-status.py` 检查系统状态
2. 查看相关服务日志
3. 检查网络连接和端口占用
4. 参考故障排除章节

---

**版本**: V3.5  
**更新时间**: 2025-01-06  
**维护团队**: AI智能体驱动交易系统开发团队