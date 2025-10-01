# 模组13: AIStrategyAssistant Dockerfile
# 基于Python 3.9 slim镜像，优化构建速度
FROM python:3.9-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

# 使用阿里云镜像源加速
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || \
    sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list

# 安装系统依赖（最小化安装）
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# 创建非root用户
RUN groupadd -r appuser && useradd -r -g appuser appuser

# 复制requirements文件
COPY 13AIStrategyAssistant/requirements.txt .

# 升级pip并使用阿里云镜像安装依赖
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# 复制健康检查脚本
COPY 13AIStrategyAssistant/health_check.py /app/health_check.py

# 复制应用代码
COPY 13AIStrategyAssistant/. .

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
