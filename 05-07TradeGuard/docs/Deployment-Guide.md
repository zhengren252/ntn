# 交易执行铁三角部署指南

## 概述

本文档详细说明了交易执行铁三角系统的部署流程、环境配置、监控设置和运维管理。系统采用微服务架构，支持开发、预发布和生产三套环境。

## 系统架构

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   交易员模组     │    │    风控模组     │    │   财务模组      │
│   (Trader)      │    │    (Risk)       │    │   (Finance)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │   ZeroMQ 代理   │
                    │   (Message)     │
                    └─────────────────┘
                                 │
         ┌───────────────────────┼───────────────────────┐
         │                       │                       │
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   数据库层      │    │    缓存层       │    │   监控层        │
│   (Database)    │    │    (Redis)      │    │   (Monitoring)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 环境要求

### 硬件要求

#### 开发环境
- CPU: 4核心以上
- 内存: 8GB以上
- 存储: 100GB以上
- 网络: 100Mbps以上

#### 生产环境
- CPU: 16核心以上
- 内存: 32GB以上
- 存储: 500GB以上 (SSD推荐)
- 网络: 1Gbps以上
- 备份存储: 1TB以上

### 软件要求

#### 基础环境
- 操作系统: Ubuntu 20.04+ / CentOS 8+ / Windows Server 2019+
- Node.js: 18.0+
- npm/pnpm: 最新版本
- Git: 2.30+

#### 数据库
- SQLite: 3.35+ (开发环境)
- PostgreSQL: 13+ (生产环境推荐)
- MySQL: 8.0+ (可选)

#### 缓存和消息队列
- Redis: 6.0+
- ZeroMQ: 4.3+

#### 容器化 (可选)
- Docker: 20.10+
- Docker Compose: 2.0+
- Kubernetes: 1.20+ (大规模部署)

## 快速部署

### 1. 环境初始化

```bash
# 克隆项目
git clone <repository-url>
cd TradeGuard

# 运行环境初始化脚本
./scripts/init-env.sh development

# 或者使用npm
npm run init:dev
```

### 2. 配置文件设置

```bash
# 复制配置模板
cp config/config.example.json config/config.development.json

# 编辑配置文件
vim config/config.development.json
```

### 3. 数据库初始化

```bash
# 运行数据库迁移
./scripts/migrate.sh run development

# 或者使用npm
npm run db:migrate
```

### 4. 启动服务

```bash
# 启动所有服务
./scripts/start-services.sh development

# 或者分别启动
npm run dev:trader    # 交易员模组
npm run dev:risk      # 风控模组
npm run dev:finance   # 财务模组
npm run dev:frontend  # 前端界面
```

## 详细部署流程

### 开发环境部署

#### 1. 环境准备

```bash
# 安装Node.js (使用nvm)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
nvm install 18
nvm use 18

# 安装pnpm
npm install -g pnpm

# 安装Redis
sudo apt update
sudo apt install redis-server
sudo systemctl start redis-server
sudo systemctl enable redis-server

# 验证Redis
redis-cli ping
```

#### 2. 项目配置

```bash
# 安装依赖
pnpm install

# 创建配置文件
cp config/config.example.json config/config.development.json

# 编辑配置
{
  "environment": "development",
  "server": {
    "port": 3000,
    "host": "localhost"
  },
  "database": {
    "type": "sqlite",
    "path": "./data/development.db"
  },
  "redis": {
    "host": "localhost",
    "port": 6379,
    "db": 0
  },
  "zeromq": {
    "broker_port": 5555,
    "pub_port": 5556,
    "sub_port": 5557
  }
}
```

#### 3. 数据库初始化

```bash
# 创建数据库目录
mkdir -p data

# 运行迁移
node scripts/db-version.js init development
node scripts/db-version.js migrate development

# 插入初始数据
node scripts/db-version.js seed development
```

#### 4. 启动开发服务

```bash
# 启动ZeroMQ代理
node scripts/zmq-broker.js &

# 启动后端服务
npm run dev &

# 启动前端开发服务器
npm run dev:frontend &

# 启动监控服务
node scripts/metrics-collector.js &
node scripts/alert-manager.js &
```

### 生产环境部署

#### 1. 服务器准备

```bash
# 创建应用用户
sudo useradd -m -s /bin/bash tradeguard
sudo usermod -aG sudo tradeguard

# 切换到应用用户
su - tradeguard

# 创建应用目录
mkdir -p /opt/tradeguard
cd /opt/tradeguard
```

#### 2. 数据库设置 (PostgreSQL)

```bash
# 安装PostgreSQL
sudo apt install postgresql postgresql-contrib

# 创建数据库和用户
sudo -u postgres psql
CREATE DATABASE tradeguard_prod;
CREATE USER tradeguard WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE tradeguard_prod TO tradeguard;
\q
```

#### 3. 生产配置

```json
{
  "environment": "production",
  "server": {
    "port": 3000,
    "host": "0.0.0.0"
  },
  "database": {
    "type": "postgresql",
    "host": "localhost",
    "port": 5432,
    "database": "tradeguard_prod",
    "username": "tradeguard",
    "password": "secure_password"
  },
  "redis": {
    "host": "localhost",
    "port": 6379,
    "db": 1,
    "password": "redis_password"
  },
  "security": {
    "jwt_secret": "your-jwt-secret",
    "encryption_key": "your-encryption-key"
  },
  "logging": {
    "level": "info",
    "file": "/var/log/tradeguard/app.log"
  }
}
```

#### 4. 使用PM2部署

```bash
# 安装PM2
npm install -g pm2

# 创建PM2配置文件
cat > ecosystem.config.js << EOF
module.exports = {
  apps: [
    {
      name: 'tradeguard-api',
      script: 'api/server.js',
      instances: 'max',
      exec_mode: 'cluster',
      env: {
        NODE_ENV: 'production',
        PORT: 3000
      }
    },
    {
      name: 'zmq-broker',
      script: 'scripts/zmq-broker.js',
      instances: 1,
      env: {
        NODE_ENV: 'production'
      }
    },
    {
      name: 'metrics-collector',
      script: 'scripts/metrics-collector.js',
      instances: 1,
      env: {
        NODE_ENV: 'production'
      }
    },
    {
      name: 'alert-manager',
      script: 'scripts/alert-manager.js',
      instances: 1,
      env: {
        NODE_ENV: 'production'
      }
    }
  ]
};
EOF

# 启动应用
pm2 start ecosystem.config.js

# 保存PM2配置
pm2 save
pm2 startup
```

## Docker部署

### 1. Dockerfile

```dockerfile
# 多阶段构建
FROM node:18-alpine AS builder

WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production

FROM node:18-alpine AS runtime

RUN addgroup -g 1001 -S nodejs
RUN adduser -S tradeguard -u 1001

WORKDIR /app

COPY --from=builder /app/node_modules ./node_modules
COPY --chown=tradeguard:nodejs . .

USER tradeguard

EXPOSE 3000

CMD ["node", "api/server.js"]
```

### 2. Docker Compose

```yaml
version: '3.8'

services:
  tradeguard-api:
    build: .
    ports:
      - "3000:3000"
    environment:
      - NODE_ENV=production
      - DATABASE_URL=postgresql://tradeguard:password@postgres:5432/tradeguard
      - REDIS_URL=redis://redis:6379
    depends_on:
      - postgres
      - redis
    volumes:
      - ./config:/app/config
      - ./logs:/app/logs
    restart: unless-stopped

  postgres:
    image: postgres:13
    environment:
      - POSTGRES_DB=tradeguard
      - POSTGRES_USER=tradeguard
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./migrations:/docker-entrypoint-initdb.d
    restart: unless-stopped

  redis:
    image: redis:6-alpine
    command: redis-server --requirepass redis_password
    volumes:
      - redis_data:/data
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - tradeguard-api
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
```

### 3. 部署命令

```bash
# 构建和启动
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down

# 更新服务
docker-compose pull
docker-compose up -d
```

## Kubernetes部署

### 1. 命名空间

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: tradeguard
```

### 2. ConfigMap

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: tradeguard-config
  namespace: tradeguard
data:
  config.json: |
    {
      "environment": "production",
      "server": {
        "port": 3000,
        "host": "0.0.0.0"
      },
      "database": {
        "type": "postgresql",
        "host": "postgres-service",
        "port": 5432,
        "database": "tradeguard"
      }
    }
```

### 3. Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: tradeguard-api
  namespace: tradeguard
spec:
  replicas: 3
  selector:
    matchLabels:
      app: tradeguard-api
  template:
    metadata:
      labels:
        app: tradeguard-api
    spec:
      containers:
      - name: api
        image: tradeguard:latest
        ports:
        - containerPort: 3000
        env:
        - name: NODE_ENV
          value: "production"
        volumeMounts:
        - name: config
          mountPath: /app/config
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
      volumes:
      - name: config
        configMap:
          name: tradeguard-config
```

### 4. Service

```yaml
apiVersion: v1
kind: Service
metadata:
  name: tradeguard-service
  namespace: tradeguard
spec:
  selector:
    app: tradeguard-api
  ports:
  - port: 80
    targetPort: 3000
  type: LoadBalancer
```

## 监控和日志

### 1. 日志配置

```javascript
// config/logging.js
const winston = require('winston');

const logger = winston.createLogger({
  level: process.env.LOG_LEVEL || 'info',
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.errors({ stack: true }),
    winston.format.json()
  ),
  transports: [
    new winston.transports.File({ 
      filename: 'logs/error.log', 
      level: 'error' 
    }),
    new winston.transports.File({ 
      filename: 'logs/combined.log' 
    })
  ]
});

if (process.env.NODE_ENV !== 'production') {
  logger.add(new winston.transports.Console({
    format: winston.format.simple()
  }));
}

module.exports = logger;
```

### 2. 健康检查

```javascript
// api/routes/health.js
const express = require('express');
const router = express.Router();

router.get('/health', async (req, res) => {
  try {
    // 检查数据库连接
    await db.raw('SELECT 1');
    
    // 检查Redis连接
    await redis.ping();
    
    // 检查ZeroMQ连接
    const zmqStatus = await checkZmqStatus();
    
    res.json({
      status: 'healthy',
      timestamp: new Date().toISOString(),
      services: {
        database: 'up',
        redis: 'up',
        zeromq: zmqStatus ? 'up' : 'down'
      }
    });
  } catch (error) {
    res.status(503).json({
      status: 'unhealthy',
      error: error.message
    });
  }
});

module.exports = router;
```

### 3. Prometheus指标

```javascript
// api/middleware/metrics.js
const prometheus = require('prom-client');

// 创建指标
const httpRequestDuration = new prometheus.Histogram({
  name: 'http_request_duration_seconds',
  help: 'HTTP request duration in seconds',
  labelNames: ['method', 'route', 'status']
});

const httpRequestTotal = new prometheus.Counter({
  name: 'http_requests_total',
  help: 'Total number of HTTP requests',
  labelNames: ['method', 'route', 'status']
});

// 中间件
function metricsMiddleware(req, res, next) {
  const start = Date.now();
  
  res.on('finish', () => {
    const duration = (Date.now() - start) / 1000;
    const route = req.route ? req.route.path : req.path;
    
    httpRequestDuration
      .labels(req.method, route, res.statusCode)
      .observe(duration);
    
    httpRequestTotal
      .labels(req.method, route, res.statusCode)
      .inc();
  });
  
  next();
}

module.exports = { metricsMiddleware };
```

## 备份和恢复

### 1. 数据库备份

```bash
#!/bin/bash
# scripts/backup-db.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/opt/tradeguard/backups"
DB_NAME="tradeguard_prod"

# 创建备份目录
mkdir -p $BACKUP_DIR

# PostgreSQL备份
pg_dump -h localhost -U tradeguard $DB_NAME | gzip > $BACKUP_DIR/db_backup_$DATE.sql.gz

# 保留最近30天的备份
find $BACKUP_DIR -name "db_backup_*.sql.gz" -mtime +30 -delete

echo "数据库备份完成: $BACKUP_DIR/db_backup_$DATE.sql.gz"
```

### 2. 配置文件备份

```bash
#!/bin/bash
# scripts/backup-config.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/opt/tradeguard/backups"
CONFIG_DIR="/opt/tradeguard/config"

# 备份配置文件
tar -czf $BACKUP_DIR/config_backup_$DATE.tar.gz -C $CONFIG_DIR .

echo "配置备份完成: $BACKUP_DIR/config_backup_$DATE.tar.gz"
```

### 3. 自动备份计划

```bash
# 添加到crontab
crontab -e

# 每天凌晨2点备份数据库
0 2 * * * /opt/tradeguard/scripts/backup-db.sh

# 每周日凌晨3点备份配置
0 3 * * 0 /opt/tradeguard/scripts/backup-config.sh
```

## 安全配置

### 1. 防火墙设置

```bash
# UFW配置
sudo ufw enable
sudo ufw default deny incoming
sudo ufw default allow outgoing

# 允许SSH
sudo ufw allow ssh

# 允许HTTP/HTTPS
sudo ufw allow 80
sudo ufw allow 443

# 允许应用端口（仅内网）
sudo ufw allow from 10.0.0.0/8 to any port 3000
sudo ufw allow from 10.0.0.0/8 to any port 5555
```

### 2. SSL证书配置

```bash
# 使用Let's Encrypt
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com

# 自动续期
sudo crontab -e
0 12 * * * /usr/bin/certbot renew --quiet
```

### 3. Nginx配置

```nginx
server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com;
    
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    
    # 安全头
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains";
    
    # API代理
    location /api/ {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # 静态文件
    location / {
        root /opt/tradeguard/dist;
        try_files $uri $uri/ /index.html;
    }
}
```

## 故障排除

### 常见问题

#### 1. 数据库连接失败
```bash
# 检查数据库状态
sudo systemctl status postgresql

# 检查连接
psql -h localhost -U tradeguard -d tradeguard_prod

# 查看日志
sudo tail -f /var/log/postgresql/postgresql-13-main.log
```

#### 2. Redis连接问题
```bash
# 检查Redis状态
sudo systemctl status redis-server

# 测试连接
redis-cli ping

# 查看配置
sudo cat /etc/redis/redis.conf | grep -v "^#" | grep -v "^$"
```

#### 3. ZeroMQ通信问题
```bash
# 检查端口占用
netstat -tlnp | grep 555

# 测试ZeroMQ连接
node -e "const zmq = require('zeromq'); console.log('ZeroMQ version:', zmq.version);"
```

#### 4. 性能问题
```bash
# 查看系统资源
top
htop
iotop

# 查看应用日志
pm2 logs
tail -f logs/combined.log

# 数据库性能
psql -c "SELECT * FROM pg_stat_activity;"
```

### 日志分析

```bash
# 查看错误日志
grep -i error logs/combined.log | tail -20

# 分析API响应时间
grep "response_time" logs/combined.log | awk '{print $NF}' | sort -n | tail -10

# 统计请求量
grep "$(date +%Y-%m-%d)" logs/combined.log | wc -l
```

## 维护计划

### 日常维护
- 检查系统资源使用情况
- 查看应用日志和错误
- 验证备份完整性
- 监控API响应时间

### 周期维护
- **每周**: 更新系统补丁
- **每月**: 清理旧日志文件
- **每季度**: 性能优化和容量规划
- **每年**: 安全审计和依赖更新

### 更新流程

```bash
# 1. 备份当前版本
./scripts/backup-db.sh
./scripts/backup-config.sh

# 2. 拉取新代码
git pull origin main

# 3. 安装依赖
npm ci

# 4. 运行迁移
./scripts/migrate.sh run production

# 5. 重启服务
pm2 restart all

# 6. 验证部署
curl -f http://localhost:3000/api/health
```

## 联系方式

如需技术支持，请联系：
- 运维团队: ops@tradeguard.com
- 紧急联系: +86-xxx-xxxx-xxxx
- 文档更新: 请提交PR到项目仓库