# 模组14: ObservabilityCenter Dockerfile
# 基于Python 3.9 slim镜像
FROM python:3.9-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 创建非root用户
RUN groupadd -r appuser && useradd -r -g appuser appuser

# 复制requirements文件
COPY 14ObservabilityCenter/requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 复制健康检查脚本
COPY 14ObservabilityCenter/health_check.py /app/health_check.py

# 复制应用代码
COPY 14ObservabilityCenter/. .

# 创建必要的目录
RUN mkdir -p logs data && \
    chown -R appuser:appuser /app

# 切换到非root用户
USER appuser

# 暴露端口
EXPOSE 8000 5555

# 健康检查 - 使用Python urllib替代curl
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python /app/health_check.py http://localhost:8000/health 10 3 1.0 || exit 1

# 启动命令
CMD ["python", "main.py"]
