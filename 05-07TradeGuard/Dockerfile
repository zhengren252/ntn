# 交易执行铁三角系统 Dockerfile
FROM node:20-alpine AS base

# 安装必要的系统依赖
RUN apk update && apk add --no-cache \
    python3 \
    py3-pip \
    python3-dev \
    py3-setuptools \
    build-base \
    sqlite \
    redis

# 设置工作目录
WORKDIR /app

# 复制package文件
COPY package*.json ./

# 安装依赖
RUN npm ci --only=production

# 开发阶段
FROM base AS development

# 安装开发依赖
RUN npm ci

# 复制源代码
COPY . .

# 暴露端口
EXPOSE 3000 5173

# 开发命令
CMD ["npm", "run", "dev"]

# 构建阶段
FROM base AS build

# 安装所有依赖（包括开发依赖）
RUN npm ci

# 复制源代码
COPY . .

# 构建应用
RUN npm run build

# 生产阶段
FROM node:20-alpine AS production

# 安装生产环境必要的系统依赖
RUN apk update && apk add --no-cache \
    dumb-init

# 创建非root用户
RUN addgroup -g 1001 -S nodejs
RUN adduser -S tradeguard -u 1001

# 设置工作目录
WORKDIR /app

# 复制package文件
COPY package*.json ./

# 安装生产依赖和tsx
RUN npm config set registry https://registry.npmmirror.com && \
    npm ci --only=production --ignore-scripts && npm install tsx --ignore-scripts && npm cache clean --force

# 从构建阶段复制构建产物
COPY --from=build --chown=tradeguard:nodejs /app/dist ./dist
COPY --from=build --chown=tradeguard:nodejs /app/api ./api
COPY --from=build --chown=tradeguard:nodejs /app/config ./config

# 创建必要的目录
RUN mkdir -p logs backups data && \
    chown -R tradeguard:nodejs logs backups data

# 切换到非root用户
USER tradeguard

# 暴露端口
EXPOSE 3001

# 健康检查
HEALTHCHECK --interval=10s --timeout=5s --start-period=30s --retries=3 \
    CMD node -e "const http = require('http'); const req = http.get('http://localhost:3001/api/health', (res) => { process.exit(res.statusCode === 200 ? 0 : 1); }); req.on('error', () => process.exit(1)); req.setTimeout(3000, () => { req.destroy(); process.exit(1); });"

# 使用dumb-init作为PID 1
ENTRYPOINT ["dumb-init", "--"]

# 启动命令
CMD ["npx", "tsx", "api/server.ts"]