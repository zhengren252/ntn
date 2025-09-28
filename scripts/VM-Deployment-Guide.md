# NeuroTrade Nexus (NTN) 虚拟机部署指南

## 概述

本指南提供了在Ubuntu虚拟机环境中部署NeuroTrade Nexus (NTN) AI驱动交易系统的完整流程。

## 环境信息

### 虚拟机配置
- **操作系统**: Ubuntu 20.04/22.04 LTS
- **用户名**: tjsga
- **密码**: 791106
- **IP地址**: 
  - 主虚拟机: 192.168.1.19
  - 备用虚拟机: 192.168.1.20
- **SSH端口**: 22

### 系统要求
- **内存**: 最少8GB，推荐16GB
- **磁盘空间**: 最少50GB可用空间
- **网络**: 稳定的网络连接
- **Docker**: 20.10+
- **Docker Compose**: 2.0+

## 部署脚本说明

### 1. SSH连接脚本 (ssh-vm-connect.ps1)

**功能**: 提供与Ubuntu虚拟机的SSH连接管理

**使用方法**:
```powershell
# 连接到主虚拟机
.\ssh-vm-connect.ps1

# 连接到备用虚拟机
.\ssh-vm-connect.ps1 -UseVM2

# 执行远程命令
.\ssh-vm-connect.ps1 -Command "docker --version"

# 传输文件
.\ssh-vm-connect.ps1 -TransferFile "C:\local\file.txt" "/remote/path/"
```

### 2. Docker部署脚本 (ubuntu-docker-deploy.sh)

**功能**: 在Ubuntu虚拟机中自动部署NTN系统

**使用方法**:
```bash
# 在虚拟机中执行
chmod +x ubuntu-docker-deploy.sh
./ubuntu-docker-deploy.sh
```

**部署流程**:
1. 系统环境检查
2. Docker环境验证
3. 端口冲突检查
4. 备份现有部署
5. 停止现有容器
6. 构建和启动新容器
7. 健康状态验证
8. 生成部署报告

### 3. 健康检查脚本 (ubuntu-vm-health-check.ps1)

**功能**: 从Windows主机远程检查Ubuntu虚拟机中的容器状态

**使用方法**:
```powershell
# 完整健康检查
.\ubuntu-vm-health-check.ps1

# 使用备用虚拟机
.\ubuntu-vm-health-check.ps1 -UseVM2

# 仅检查容器状态
.\ubuntu-vm-health-check.ps1 -SkipSystemCheck
```

## 容器架构

### 核心服务容器 (15个)

| 容器名称 | 端口 | 功能描述 |
|---------|------|----------|
| ntn-redis-prod | 6379 | Redis缓存服务 |
| 01APIForge | 8000 | API管理工厂 |
| 02DataSpider | 8001 | 信息爬虫服务 |
| 03ScanPulse | 8002 | 扫描脉冲服务 |
| 04OptiCore | 8003 | 策略优化核心 |
| 05-07TradeGuard | 8004 | 交易守护服务 |
| 08NeuroHub | 8005 | 神经网络中枢 |
| 09MMS | 8006 | 市场制造商服务 |
| 10ReviewGuard-backend | 8007 | 审查守护后端 |
| 11ASTSConsole | 8008 | ASTS控制台后端 |
| 12TACoreService | 8009 | TA核心服务 |
| 13AI-Strategy-Assistant | 8010 | AI策略助手 |
| 14Observability-Center | 8011 | 可观测性中心 |
| 10ReviewGuard-frontend | 3000 | 审查守护前端 |
| 11ASTSConsole-frontend | 3001 | ASTS控制台前端 |
| nginx | 80/443 | Nginx网关 |

## 部署流程

### 第一步: 环境准备

1. **验证网络连接**:
```powershell
.\ssh-vm-connect.ps1 -TestConnection
```

2. **检查虚拟机状态**:
```powershell
.\ssh-vm-connect.ps1 -Command "uname -a && docker --version"
```

### 第二步: 传输配置文件

1. **传输Docker Compose配置**:
```powershell
.\ssh-vm-connect.ps1 -TransferFile "docker-compose.prod.yml" "/home/tjsga/ntn/"
```

2. **传输部署脚本**:
```powershell
.\ssh-vm-connect.ps1 -TransferFile "ubuntu-docker-deploy.sh" "/home/tjsga/ntn/"
```

### 第三步: 执行部署

1. **运行部署脚本**:
```powershell
.\ssh-vm-connect.ps1 -Command "cd /home/tjsga/ntn && chmod +x ubuntu-docker-deploy.sh && ./ubuntu-docker-deploy.sh"
```

2. **监控部署进度**:
```powershell
.\ssh-vm-connect.ps1 -Command "cd /home/tjsga/ntn && docker-compose -f docker-compose.prod.yml ps"
```

### 第四步: 健康检查

1. **执行完整健康检查**:
```powershell
.\ubuntu-vm-health-check.ps1
```

2. **验证服务端点**:
```powershell
.\ubuntu-vm-health-check.ps1 -CheckEndpoints
```

## 故障排除

### 常见问题

#### 1. SSH连接失败
**症状**: 无法连接到虚拟机
**解决方案**:
- 检查网络连接
- 验证IP地址和端口
- 确认SSH服务运行状态
- 检查防火墙设置

#### 2. 容器启动失败
**症状**: 容器无法正常启动
**解决方案**:
```bash
# 查看容器日志
docker-compose -f docker-compose.prod.yml logs [container_name]

# 检查资源使用
docker system df
free -h

# 清理未使用资源
docker system prune -f
```

#### 3. 端口冲突
**症状**: 端口已被占用
**解决方案**:
```bash
# 查看端口使用情况
netstat -tulpn | grep :8000

# 停止冲突进程
sudo kill -9 [PID]
```

#### 4. 内存不足
**症状**: 系统响应缓慢或容器被杀死
**解决方案**:
```bash
# 检查内存使用
free -h
docker stats

# 调整容器资源限制
# 编辑docker-compose.prod.yml中的resources配置
```

### 日志收集

#### 系统日志
```bash
# 查看系统日志
sudo journalctl -u docker.service
sudo dmesg | tail -50
```

#### 容器日志
```bash
# 查看所有容器日志
docker-compose -f docker-compose.prod.yml logs

# 查看特定容器日志
docker-compose -f docker-compose.prod.yml logs 01APIForge

# 实时跟踪日志
docker-compose -f docker-compose.prod.yml logs -f
```

## 监控和维护

### 定期检查

1. **每日健康检查**:
```powershell
# 设置定时任务执行
.\ubuntu-vm-health-check.ps1 > "health-check-$(Get-Date -Format 'yyyyMMdd').log"
```

2. **资源监控**:
```bash
# 在虚拟机中设置监控脚本
watch -n 30 'docker stats --no-stream && echo "=== Memory ===" && free -h && echo "=== Disk ===" && df -h'
```

### 备份策略

1. **配置文件备份**:
```bash
# 备份Docker Compose配置
cp docker-compose.prod.yml docker-compose.prod.yml.backup.$(date +%Y%m%d)
```

2. **数据卷备份**:
```bash
# 备份Redis数据
docker exec ntn-redis-prod redis-cli BGSAVE
```

### 更新流程

1. **停止服务**:
```bash
docker-compose -f docker-compose.prod.yml down
```

2. **更新镜像**:
```bash
docker-compose -f docker-compose.prod.yml pull
```

3. **重新部署**:
```bash
./ubuntu-docker-deploy.sh
```

## 安全注意事项

1. **网络安全**:
   - 使用防火墙限制访问
   - 定期更新SSH密钥
   - 监控异常登录

2. **容器安全**:
   - 定期更新基础镜像
   - 扫描安全漏洞
   - 限制容器权限

3. **数据安全**:
   - 加密敏感数据
   - 定期备份
   - 访问控制

## 联系支持

如遇到技术问题，请提供以下信息：
- 错误日志
- 系统配置
- 复现步骤
- 环境信息

---

**文档版本**: 1.0  
**最后更新**: 2024年1月  
**维护者**: NTN开发团队