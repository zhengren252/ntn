# 澶氶樁娈垫瀯寤?Dockerfile for API Factory
# Stage 1: 鏋勫缓闃舵
FROM mcr.microsoft.com/devcontainers/python:3.11-bookworm as builder

# 璁剧疆宸ヤ綔鐩綍
WORKDIR /app

# 瀹夎绯荤粺渚濊禆
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# 澶嶅埗渚濊禆鏂囦欢
COPY requirements.txt .

# 瀹夎Python渚濊禆
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: 杩愯闃舵
FROM mcr.microsoft.com/devcontainers/python:3.11-bookworm as runtime

# 在运行阶段安装健康检查所需工具（curl）
RUN apt-get update && apt-get install -y curl ca-certificates && rm -rf /var/lib/apt/lists/*

# 鍒涘缓闈瀝oot鐢ㄦ埛
RUN groupadd -r apiuser && useradd -r -g apiuser apiuser

# 璁剧疆宸ヤ綔鐩綍
WORKDIR /app

# 浠庢瀯寤洪樁娈靛鍒禤ython鍖?
COPY --from=builder /root/.local /home/apiuser/.local

# 澶嶅埗搴旂敤浠ｇ爜
COPY api_factory/ ./api_factory/
COPY config/ ./config/
COPY tests/ ./tests/

# 复制pytest配置，确保标记已注册
COPY pytest.ini ./

# 鍒涘缓蹇呰鐨勭洰褰?
RUN mkdir -p /app/data /app/logs && \
    chown -R apiuser:apiuser /app

# 鍒囨崲鍒伴潪root鐢ㄦ埛
USER apiuser

# 璁剧疆鐜鍙橀噺
ENV PATH=/home/apiuser/.local/bin:$PATH
ENV PYTHONPATH=/app

# 鏆撮湶绔彛
EXPOSE 8000 5555 5556

# 鍋ュ悍妫€鏌?
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 鍚姩鍛戒护
CMD ["python", "-m", "api_factory.main"]
