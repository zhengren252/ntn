# ReviewGuard后端服务 Dockerfile
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 创建非root用户
RUN groupadd --gid 1001 appgroup && \
    useradd --uid 1001 --gid appgroup --shell /bin/bash --create-home appuser

# 安装系统依赖 (添加重试机制和镜像源优化)
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list && apt-get update --fix-missing && \
    apt-get install -y --no-install-recommends \
    build-essential \
    libzmq3-dev \
    pkg-config \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# 复制依赖文件并安装Python依赖
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 复制源代�?
COPY . .

# 创建必要目录并设置权�?
RUN mkdir -p /app/data /app/logs && \
    chown -R appuser:appgroup /app

# 切换到非root用户
USER appuser

# 暴露端口
EXPOSE 8000 5555 5556

# 设置环境变量
ENV PYTHONPATH=/app/src
ENV APP_ENV=production
ENV PYTHONUNBUFFERED=1

# 健康检�?
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 启动命令
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
