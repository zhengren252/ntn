# 扫描器模块 Docker 配置
# 多阶段构建：构建阶段 + 运行阶段

# ===== 构建阶段 =====
FROM python:3.11-slim as builder

# 设置工作目录
WORKDIR /build

# 安装构建依赖
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list && apt-get update && apt-get install -y \
    gcc \
    g++ \
    libzmq3-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY 03ScanPulse/requirements.txt .

# 安装Python依赖到临时目录
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir --target=/build/deps -r requirements.txt

# ===== 运行阶段 =====
FROM python:3.11-slim as runtime

# 设置工作目录
WORKDIR /app

# 环境变量
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH=/app:/app/deps \
    PYTHONUNBUFFERED=1 \
    SCANNER_ENV=production

# 安装运行时依赖（保留必要的）
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list && apt-get update && apt-get install -y \
    libzmq5 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# 从构建阶段复制Python依赖
COPY --from=builder /build/deps /app/deps

# 创建非root用户与组
RUN groupadd -r scanner && useradd -r -g scanner -s /bin/false scanner

# 创建必需目录并设置权限（统一写入 /app/logs，避免 /var/log 权限问题）
RUN mkdir -p /app/logs /app/config && \
    chown -R scanner:scanner /app

# 复制应用代码
COPY 03ScanPulse/. /app/

# 设置文件权限
RUN chown -R scanner:scanner /app

# 切换到非root用户
USER scanner

# 暴露端口（Web 8000, ZMQ 5555/5558）
EXPOSE 8000 5555 5558

# 健康检查（使用 Python stdlib urllib 调用 /live 避免外部依赖）
HEALTHCHECK --interval=30s --timeout=10s --start-period=90s --retries=5 \
    CMD ["python", "-c", "import sys,urllib.request,socket; socket.setdefaulttimeout(5); sys.exit(0 if 200<=urllib.request.urlopen('http://localhost:8000/live', timeout=5).getcode()<300 else 1)"]

# 启动命令
CMD ["python", "main.py", "start", "--environment", "production"]
