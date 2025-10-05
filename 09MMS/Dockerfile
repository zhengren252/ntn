# 市场微结构仿真引擎(MMS) Docker配置文件
# 多阶段构建，优化镜像大小和安全性

# 构建阶段
FROM python:3.11-slim as builder

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list && apt-get update && apt-get install -y --fix-missing -o Acquire::Retries=3 -o Acquire::http::Timeout=30 \
    gcc \
    g++ \
    make \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY 09MMS/requirements.txt .

# 创建虚拟环境并安装Python依赖
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir --upgrade pip setuptools wheel
RUN pip install --no-cache-dir --default-timeout=100 --retries 3 --index-url https://pypi.org/simple -r requirements.txt

# 运行阶段
FROM python:3.11-slim as runtime

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    APP_ENV=production

# 创建与宿主机匹配的用户 (UID 1000)
RUN groupadd -g 1000 vscode && useradd -u 1000 -g 1000 vscode

# 安装运行时依赖
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list && apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制虚拟环境
COPY --from=builder /opt/venv /opt/venv

# 设置工作目录
WORKDIR /app

# 复制应用代码并设置标准权限
COPY --chown=vscode:vscode 09MMS/src/ ./src/
COPY --chown=vscode:vscode 09MMS/scripts/ ./scripts/
COPY --chown=vscode:vscode 09MMS/config/ ./config/
COPY --chown=vscode:vscode 09MMS/*.py ./
COPY --chown=vscode:vscode 09MMS/*.md ./
COPY --chown=vscode:vscode 09MMS/*.txt ./

# 创建必要目录并设置标准权限
RUN mkdir -p /app/data /app/logs && chown -R vscode:vscode /app

# 切换到非root用户
USER vscode

# 暴露端口
EXPOSE 8000 5555 5556 5557

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 启动命令
CMD ["python", "-m", "uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]

# 元数据标签
LABEL maintainer="NeuroTrade Nexus Team" \
      version="1.0.0" \
      description="Market Microstructure Simulation Engine" \
      org.opencontainers.image.title="MMS" \
      org.opencontainers.image.description="Market Microstructure Simulation Engine" \
      org.opencontainers.image.version="1.0.0" \
      org.opencontainers.image.vendor="NeuroTrade Nexus" \
      org.opencontainers.image.licenses="MIT"