# 信息源爬虫模块 - Docker镜像
# 支持三环境隔离：development/staging/production

FROM python:3.11-slim as base

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 安装系统依赖
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list && apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    wget \
    git \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# 创建应用用户
RUN groupadd -r appuser && useradd -r -g appuser appuser

# 设置工作目录
WORKDIR /app

# 复制依赖文件
COPY 02DataSpider/requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 开发环境阶段
FROM base as development

# 安装开发依赖
RUN pip install --no-cache-dir \
    pytest \
    pytest-cov \
    black \
    pylint \
    mypy \
    ipython

# 复制应用代码
COPY 02DataSpider/. .

# 创建数据目录
RUN mkdir -p data logs temp \
    && chown -R appuser:appuser /app

# 设置环境变量
ENV PATH="/opt/venv/bin:$PATH" \
    APP_ENV=development \
    NTN_ENV=development \
    PYTHONPATH=/app \
    LOG_LEVEL=DEBUG

# 切换到应用用户
USER appuser

# 暴露端口
EXPOSE 5000 5555 5556

# 启动命令
CMD ["python", "main.py", "--env", "development", "--mode", "all"]

# 测试环境阶段
FROM base as staging

# 复制应用代码
COPY 02DataSpider/. .

# 创建数据目录
RUN mkdir -p data logs temp \
    && chown -R appuser:appuser /app

# 设置环境变量
ENV PATH="/opt/venv/bin:$PATH" \
    APP_ENV=staging \
    NTN_ENV=staging \
    PYTHONPATH=/app \
    LOG_LEVEL=INFO

# 切换到应用用户
USER appuser

# 暴露端口
EXPOSE 5000 5555 5556

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=90s --retries=5 \
    CMD python -c "import sys,urllib.request,socket; socket.setdefaulttimeout(5); sys.exit(0 if 200<=urllib.request.urlopen('http://localhost:5000/live', timeout=5).getcode()<300 else 1)"

# 启动命令
CMD ["python", "main.py", "--env", "staging", "--mode", "all"]

# 生产环境阶段
FROM base as production

# 复制应用代码（排除开发文件）
COPY 02DataSpider/app/ ./app/
COPY 02DataSpider/config/ ./config/
COPY 02DataSpider/scripts/ ./scripts/
COPY 02DataSpider/main.py 02DataSpider/requirements.txt ./

# 创建数据目录
RUN mkdir -p data logs temp \
    && chown -R appuser:appuser /app

# 设置环境变量
ENV PATH="/opt/venv/bin:$PATH" \
    APP_ENV=production \
    NTN_ENV=production \
    PYTHONPATH=/app \
    LOG_LEVEL=INFO

# 切换到应用用户
USER appuser

# 暴露端口
EXPOSE 5000 5555 5556

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=90s --retries=5 \
    CMD python -c "import sys,urllib.request,socket; socket.setdefaulttimeout(5); sys.exit(0 if 200<=urllib.request.urlopen('http://localhost:5000/live', timeout=5).getcode()<300 else 1)"

# 启动命令
CMD ["python", "main.py", "--env", "production", "--mode", "all"]
