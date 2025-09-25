# AI智能体驱动交易系统V1.2 - 端口映射配置文档

## 概述
本文档记录了生产环境中所有14个模组及基础服务的端口映射配置，确保端口无冲突且服务间通信正常。

## 端口分配策略
- **基础服务**: 6000-6999
- **API服务**: 5000-5999 
- **前端服务**: 3000-3999
- **ZMQ通信**: 5555-5599
- **监控服务**: 8000-8999, 9000-9999
- **Web服务**: 80, 443

## 详细端口映射表

### 基础服务层
| 服务名称 | 容器名称 | 内部端口 | 外部端口 | 协议 | 用途 |
|---------|----------|----------|----------|------|------|
| Redis | ntn-redis-prod | 6379 | 6379 | TCP | 缓存服务 |
| Nginx | ntn-nginx-prod | 80 | 80 | HTTP | 反向代理 |
| Nginx | ntn-nginx-prod | 443 | 443 | HTTPS | 安全代理 |

### 核心业务模组层

#### 模组一：API统一管理工厂
| 服务名称 | 容器名称 | 内部端口 | 外部端口 | 协议 | 用途 |
|---------|----------|----------|----------|------|------|
| API Factory | ntn-api-factory-prod | 8000 | 8000 | HTTP | API服务 |
| API Factory | ntn-api-factory-prod | 5555 | 5555 | ZMQ | ZMQ Publisher |
| API Factory | ntn-api-factory-prod | 5556 | 5556 | ZMQ | ZMQ Subscriber |

#### 模组二：信息源爬虫
| 服务名称 | 容器名称 | 内部端口 | 外部端口 | 协议 | 用途 |
|---------|----------|----------|----------|------|------|
| Info Crawler | ntn-info-crawler-prod | 5000 | 5001 | HTTP | Flask API |
| Info Crawler | ntn-info-crawler-prod | 5555 | 5557 | ZMQ | ZMQ Publisher |

#### 模组三：扫描器
| 服务名称 | 容器名称 | 内部端口 | 外部端口 | 协议 | 用途 |
|---------|----------|----------|----------|------|------|
| Scanner | ntn-scanner-prod | 5000 | 5002 | HTTP | Scanner API |
| Scanner | ntn-scanner-prod | 5555 | 5558 | ZMQ | ZMQ Publisher |

#### 模组四：策略优化
| 服务名称 | 容器名称 | 内部端口 | 外部端口 | 协议 | 用途 |
|---------|----------|----------|----------|------|------|
| Strategy Optimizer | ntn-strategy-optimizer-prod | 5000 | 5003 | HTTP | Optimizer API |
| Strategy Optimizer | ntn-strategy-optimizer-prod | 3000 | 3001 | HTTP | Frontend |

#### 模组五、六、七：交易执行铁三角
| 服务名称 | 容器名称 | 内部端口 | 外部端口 | 协议 | 用途 |
|---------|----------|----------|----------|------|------|
| Trade Guard | ntn-trade-guard-prod | 5000 | 5004 | HTTP | TradeGuard API |
| Trade Guard | ntn-trade-guard-prod | 3000 | 3002 | HTTP | Frontend |

#### 模组八：总控模块
| 服务名称 | 容器名称 | 内部端口 | 外部端口 | 协议 | 用途 |
|---------|----------|----------|----------|------|------|
| Neuro Hub | ntn-neuro-hub-prod | 5000 | 5005 | HTTP | NeuroHub API |
| Neuro Hub | ntn-neuro-hub-prod | 3000 | 3003 | HTTP | Frontend |

#### 模组九：MMS (Market Making System)
| 服务名称 | 容器名称 | 内部端口 | 外部端口 | 协议 | 用途 |
|---------|----------|----------|----------|------|------|
| MMS | ntn-mms-prod | 5000 | 5006 | HTTP | MMS API |

#### 模组十：人工审核模块
| 服务名称 | 容器名称 | 内部端口 | 外部端口 | 协议 | 用途 |
|---------|----------|----------|----------|------|------|
| Review Guard | ntn-review-guard-prod | 5000 | 5007 | HTTP | ReviewGuard API |
| Review Guard | ntn-review-guard-prod | 3000 | 3004 | HTTP | Frontend |

#### 模组十一：ASTS Console (前端管理界面)
| 服务名称 | 容器名称 | 内部端口 | 外部端口 | 协议 | 用途 |
|---------|----------|----------|----------|------|------|
| ASTS Console | ntn-asts-console-prod | 3000 | 3000 | HTTP | 主前端界面 |

#### 模组十二：TACoreService
| 服务名称 | 容器名称 | 内部端口 | 外部端口 | 协议 | 用途 |
|---------|----------|----------|----------|------|------|
| TACore Service | ntn-tacore-service-prod | 5000 | 5008 | HTTP | TACoreService API |

#### 模组十三：AI策略研究助理
| 服务名称 | 容器名称 | 内部端口 | 外部端口 | 协议 | 用途 |
|---------|----------|----------|----------|------|------|
| AI Strategy Assistant | ntn-ai-strategy-assistant-prod | 5000 | 5009 | HTTP | AI Assistant API |

#### 模组十四：系统可观测性中心
| 服务名称 | 容器名称 | 内部端口 | 外部端口 | 协议 | 用途 |
|---------|----------|----------|----------|------|------|
| Observability Center | ntn-observability-center-prod | 5000 | 5010 | HTTP | Observability API |
| Observability Center | ntn-observability-center-prod | 3000 | 3005 | HTTP | Monitoring Dashboard |
| Observability Center | ntn-observability-center-prod | 9090 | 9090 | HTTP | Prometheus |
| Observability Center | ntn-observability-center-prod | 3001 | 3006 | HTTP | Grafana |

## 端口范围总结

### 已使用端口
- **80**: Nginx HTTP
- **443**: Nginx HTTPS
- **3000**: ASTS Console 主前端
- **3001**: Strategy Optimizer Frontend
- **3002**: Trade Guard Frontend
- **3003**: Neuro Hub Frontend
- **3004**: Review Guard Frontend
- **3005**: Observability Center Dashboard
- **3006**: Grafana
- **5001**: Info Crawler API
- **5002**: Scanner API
- **5003**: Strategy Optimizer API
- **5004**: Trade Guard API
- **5005**: Neuro Hub API
- **5006**: MMS API
- **5007**: Review Guard API
- **5008**: TACore Service API
- **5009**: AI Strategy Assistant API
- **5010**: Observability Center API
- **5555**: API Factory ZMQ Publisher
- **5556**: API Factory ZMQ Subscriber
- **5557**: Info Crawler ZMQ Publisher
- **5558**: Scanner ZMQ Publisher
- **6379**: Redis
- **8000**: API Factory HTTP
- **9090**: Prometheus

### 预留端口
- **5011-5020**: 未来API服务扩展
- **3007-3010**: 未来前端服务扩展
- **5559-5570**: 未来ZMQ通信扩展

## 服务间通信配置

### 内部网络通信
所有服务都连接到 `ntn_network` 桥接网络，子网为 `192.168.100.0/24`。

### ZMQ消息队列通信
- **API Factory**: 作为主要的ZMQ Hub，端口5555(Publisher)和5556(Subscriber)
- **Info Crawler**: ZMQ Publisher端口5557
- **Scanner**: ZMQ Publisher端口5558

### Redis数据库分配
- **Redis DB 0**: 默认/共享缓存
- **Redis DB 1**: Info Crawler
- **Redis DB 2**: Scanner
- **Redis DB 3**: Strategy Optimizer
- **Redis DB 4**: Trade Guard
- **Redis DB 5**: Neuro Hub
- **Redis DB 6**: MMS
- **Redis DB 7**: Review Guard
- **Redis DB 8**: TACore Service
- **Redis DB 9**: AI Strategy Assistant
- **Redis DB 10**: Observability Center

## 健康检查端点
所有API服务都提供 `/health` 端点用于健康检查：
- 检查间隔：30秒
- 超时时间：10-15秒
- 重试次数：3-5次
- 启动等待：60-120秒

## 防火墙和安全配置

### 对外开放端口
- **80**: HTTP访问
- **443**: HTTPS访问
- **3000**: 主前端界面
- **8000**: API工厂主入口

### 内部端口
所有5001-5010端口仅用于内部服务通信和调试，生产环境建议通过Nginx代理访问。

## 故障排查指南

### 端口冲突检查
```bash
# 检查端口占用
netstat -tulpn | grep :端口号

# 检查Docker容器端口映射
docker port 容器名称
```

### 服务连通性测试
```bash
# 测试HTTP服务
curl -f http://localhost:端口号/health

# 测试ZMQ连接
telnet localhost ZMQ端口号
```

### 常见问题
1. **端口已被占用**: 检查系统中是否有其他服务占用相同端口
2. **容器无法启动**: 检查端口映射配置和防火墙设置
3. **服务间通信失败**: 验证网络配置和服务发现设置

---

**文档版本**: V1.2  
**最后更新**: 2024年集成测试阶段  
**维护者**: AI智能体驱动交易系统开发团队