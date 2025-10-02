# 多阶段构建Dockerfile for API Factory
# Stage 1: 构建阶段
FROM mcr.microsoft.com/devcontainers/python:3.11-bookworm as builder

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY 01APIForge/requirements.txt .

# 创建虚拟环境
RUN python -m venv /opt/venv

# 安装Python依赖
RUN /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

# Stage 2: 运行阶段
FROM mcr.microsoft.com/devcontainers/python:3.11-bookworm as runtime

# 在运行阶段安装健康检查所需工具（curl）
RUN apt-get update && apt-get install -y curl ca-certificates && rm -rf /var/lib/apt/lists/*

# 创建非root用户
RUN groupadd -r apiuser && useradd -r -g apiuser apiuser

# 设置工作目录
WORKDIR /app

# 从构建阶段复制虚拟环境
COPY --from=builder /opt/venv /opt/venv

# 复制应用代码
COPY 01APIForge/api_factory/ ./api_factory/
COPY config/ ./config/
COPY 01APIForge/tests/ ./tests/

# 复制pytest配置，确保标记已注册
COPY 01APIForge/pytest.ini ./

# 创建运行时需要的目录
RUN mkdir -p /app/data /app/logs && \
    chown -R apiuser:apiuser /app

# 切换到非root用户
USER apiuser

# 设置环境变量
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONPATH=/app

# 暴露端口
EXPOSE 8000 5555 5556

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 启动应用
CMD ["python", "-m", "api_factory.main"]
