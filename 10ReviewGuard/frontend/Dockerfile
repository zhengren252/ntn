# ReviewGuard前端服务 Dockerfile
# 构建阶段
FROM node:18 AS builder

WORKDIR /app

# 复制依赖文件
COPY package*.json ./

# 安装依赖
RUN npm install

# 复制源代码
COPY . .

# 设置构建时公开API变量（用于 Next.js 构建期读取）
ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}

# 构建应用
RUN npm run build

# 生产阶段
FROM node:18 AS runner

WORKDIR /app

# 创建非root用户
RUN groupadd --gid 1001 nodejs
RUN useradd --uid 1001 --gid nodejs --shell /bin/bash --create-home nextjs

# 复制构建结果
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

# 切换到非root用户
USER nextjs

# 暴露端口
EXPOSE 3000

# 设置环境变量
ENV PORT=3000
ENV NODE_ENV=production

# 启动命令
CMD ["node", "server.js"]