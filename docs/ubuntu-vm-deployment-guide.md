# Ubuntu虚拟机Docker部署指南

## 环境信息
- **虚拟机系统**: Ubuntu 22.04.5 LTS
- **Docker版本**: 最新稳定版
- **部署模式**: 生产环境集成测试

## 部署前检查清单

### 1. 系统要求验证
```bash
# 检查Ubuntu版本
lsb_release -a

# 检查Docker版本
docker --version
docker-compose --version

# 检查系统资源
free -h
df -h
```

### 2. 网络配置检查
```bash
# 检查端口占用情况
sudo netstat -tulpn | grep -E ':(80|443|3000|5000|6379|8000)'

# 检查防火墙状态
sudo ufw status
```

### 3. 权限配置
```bash
# 确保当前用户在docker组中
sudo usermod -aG docker $USER
newgrp docker

# 验证Docker权限
docker run hello-world
```

## 部署步骤

### 阶段一：环境准备
```bash
# 1. 进入项目目录
cd "/path/to/NeuroTrade Nexus (NTN)"

# 2. 检查配置文件
ls -la docker-compose.prod.yml
ls -la config/

# 3. 创建必要的目录
mkdir -p logs data temp
```

### 阶段二：系统启动
```bash
# 1. 清理旧容器（如果存在）
docker-compose -f docker-compose.prod.yml down
docker system prune -f

# 2. 构建并启动所有服务
docker-compose -f docker-compose.prod.yml up --build -d

# 3. 检查容器状态
docker-compose -f docker-compose.prod.yml ps
```

### 阶段三：健康检查
```bash
# 1. 检查所有容器运行状态
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# 2. 检查容器健康状态
docker ps --filter "health=healthy" --format "table {{.Names}}\t{{.Status}}"
docker ps --filter "health=unhealthy" --format "table {{.Names}}\t{{.Status}}"

# 3. 查看容器日志（如有问题）
docker-compose -f docker-compose.prod.yml logs [service-name]
```

## 服务端点验证

### 核心服务健康检查
```bash
# Redis
docker exec ntn-redis-prod redis-cli ping

# API Factory
curl -f http://localhost:8000/health

# Info Crawler
curl -f http://localhost:5001/health

# Scanner
curl -f http://localhost:5002/health

# Strategy Optimizer
curl -f http://localhost:5003/health

# Trade Guard
curl -f http://localhost:5004/health

# Neuro Hub
curl -f http://localhost:5005/health

# MMS
curl -f http://localhost:5006/health

# Review Guard Backend
curl -f http://localhost:5007/health

# TACoreService
curl -f http://localhost:5008/health

# AI Strategy Assistant
curl -f http://localhost:5009/health

# Observability Center
curl -f http://localhost:5010/health
```

### 前端界面访问
```bash
# ASTS Console (主界面)
curl -f http://localhost:3000

# Strategy Optimizer Frontend
curl -f http://localhost:3001

# Trade Guard Frontend
curl -f http://localhost:3002

# Neuro Hub Frontend
curl -f http://localhost:3003

# Review Guard Frontend
curl -f http://localhost:3004

# Observability Dashboard
curl -f http://localhost:3005

# Grafana
curl -f http://localhost:3006
```

## 故障排除

### 常见问题
1. **容器启动失败**
   ```bash
   # 查看详细日志
   docker-compose -f docker-compose.prod.yml logs [service-name]
   
   # 检查资源使用
   docker stats
   ```

2. **端口冲突**
   ```bash
   # 查找占用端口的进程
   sudo lsof -i :[port-number]
   
   # 停止冲突服务
   sudo systemctl stop [service-name]
   ```

3. **权限问题**
   ```bash
   # 修复目录权限
   sudo chown -R $USER:$USER ./logs ./data ./temp
   chmod -R 755 ./logs ./data ./temp
   ```

4. **内存不足**
   ```bash
   # 检查内存使用
   free -h
   docker stats --no-stream
   
   # 清理Docker缓存
   docker system prune -a
   ```

## 性能优化建议

### Ubuntu虚拟机优化
1. **分配足够资源**
   - 内存: 至少16GB
   - CPU: 至少4核心
   - 磁盘: 至少100GB可用空间

2. **系统优化**
   ```bash
   # 优化虚拟内存
   echo 'vm.swappiness=10' | sudo tee -a /etc/sysctl.conf
   
   # 优化文件描述符限制
   echo '* soft nofile 65536' | sudo tee -a /etc/security/limits.conf
   echo '* hard nofile 65536' | sudo tee -a /etc/security/limits.conf
   ```

3. **Docker优化**
   ```bash
   # 配置Docker日志轮转
   sudo tee /etc/docker/daemon.json > /dev/null <<EOF
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "100m",
    "max-file": "3"
  }
}
EOF
   
   sudo systemctl restart docker
   ```

## 监控和维护

### 定期检查脚本
```bash
#!/bin/bash
# health-check.sh

echo "=== NTN系统健康检查 ==="
echo "时间: $(date)"
echo

echo "容器状态:"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo

echo "健康检查:"
docker ps --filter "health=healthy" --format "table {{.Names}}\t{{.Status}}"
echo

echo "异常容器:"
docker ps --filter "health=unhealthy" --format "table {{.Names}}\t{{.Status}}"
echo

echo "资源使用:"
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}"
```

### 备份脚本
```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="/backup/ntn-$(date +%Y%m%d-%H%M%S)"
mkdir -p $BACKUP_DIR

# 备份数据卷
docker run --rm -v ntn_redis_data:/data -v $BACKUP_DIR:/backup alpine tar czf /backup/redis_data.tar.gz -C /data .
docker run --rm -v ntn_prometheus_data:/data -v $BACKUP_DIR:/backup alpine tar czf /backup/prometheus_data.tar.gz -C /data .
docker run --rm -v ntn_grafana_data:/data -v $BACKUP_DIR:/backup alpine tar czf /backup/grafana_data.tar.gz -C /data .

# 备份配置文件
cp -r ./config $BACKUP_DIR/
cp docker-compose.prod.yml $BACKUP_DIR/

echo "备份完成: $BACKUP_DIR"
```

## 部署验证清单

- [ ] Ubuntu 22.04.5虚拟机环境就绪
- [ ] Docker和Docker Compose安装完成
- [ ] 用户权限配置正确
- [ ] 所有15个容器成功启动
- [ ] 所有容器健康检查通过
- [ ] 核心服务API端点响应正常
- [ ] 前端界面可正常访问
- [ ] 网络连接和端口映射正确
- [ ] 日志记录功能正常
- [ ] 监控和告警系统运行
- [ ] 备份和恢复流程测试通过

---

**注意**: 此部署指南专为Ubuntu 22.04.5虚拟机环境设计，替代了原有的Docker Desktop方案，提供更稳定的容器化部署体验。