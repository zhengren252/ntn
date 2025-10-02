# TACoreService Docker配置
FROM python:3.9-slim

# 设置工作目录
WORKDIR /app

# 配置国内镜像源并安装系统依赖
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources && \
    apt-get update && apt-get install -y \
    gcc \
    g++ \
    libzmq3-dev \
    pkg-config \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制requirements文件
COPY 12TACoreService/requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY 12TACoreService/. .

# 创建必要的目录
RUN mkdir -p /app/data /app/logs /app/config

# 设置环境变量
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH=/app \
    TACORESERVICE_ENV=production \
    TACORESERVICE_LOG_LEVEL=INFO

# 暴露端口
EXPOSE 5555 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 启动命令
CMD ["python", "main.py"]