# ReviewGuard模块主Dockerfile
# 人工审核模块 - 基于Python 3.11-slim，支持FastAPI + ZeroMQ + Redis
# 遵循AI智能体驱动交易系统架构规范

FROM python:3.11-slim as base

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app:/app/backend/src \
    APP_ENV=production

# 设置工作目录
WORKDIR /app

# 创建与宿主机匹配的用户 (UID 1000)
RUN groupadd -g 1000 vscode && useradd -u 1000 -g 1000 vscode

# 安装系统依赖
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list && apt-get update && apt-get install -y \
    build-essential \
    libzmq3-dev \
    pkg-config \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# 复制后端依赖文件
COPY 10ReviewGuard/backend/requirements.txt ./backend/

# 【重建虚拟环境】创建Python虚拟环境
RUN python -m venv /opt/venv

# 【设置PATH环境变量】将虚拟环境的bin目录加入系统PATH
ENV PATH="/opt/venv/bin:$PATH"

# 【在虚拟环境中安装依赖】使用虚拟环境中的pip安装所有依赖
RUN /opt/venv/bin/pip install --no-cache-dir --upgrade pip && \
    /opt/venv/bin/pip install --no-cache-dir -r backend/requirements.txt

# 复制后端源代码
COPY 10ReviewGuard/backend/ ./backend/

# 复制models目录
COPY 10ReviewGuard/models/ ./models/

# 复制配置文件
COPY 10ReviewGuard/.env.production 10ReviewGuard/.env.staging 10ReviewGuard/.env.example ./

# 创建数据目录并设置正确权限
RUN mkdir -p /app/data /app/logs /app/config && \
    chown -R vscode:vscode /app && \
    chmod -R 755 /app/data /app/logs /app/config

# 切换到非root用户
USER vscode

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 暴露端口
# 8000: FastAPI HTTP API
# 5555: ZeroMQ发布端口
# 5556: ZeroMQ订阅端口
EXPOSE 8000 5555 5556

# 【修正启动命令】使用虚拟环境中的uvicorn启动应用
CMD ["/opt/venv/bin/uvicorn", "backend.src.main:app", "--host", "0.0.0.0", "--port", "8000"]