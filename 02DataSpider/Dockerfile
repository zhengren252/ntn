# 淇℃伅婧愮埇铏ā缁?- Docker闀滃儚
# 鏀寔涓夌幆澧冮殧绂伙細development/staging/production

FROM python:3.11-slim as base

# 璁剧疆鐜鍙橀噺
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 瀹夎绯荤粺渚濊禆
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list && apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    wget \
    git \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# 鍒涘缓搴旂敤鐢ㄦ埛
RUN groupadd -r appuser && useradd -r -g appuser appuser

# 璁剧疆宸ヤ綔鐩綍
WORKDIR /app

# 澶嶅埗渚濊禆鏂囦欢
COPY requirements.txt .

# 瀹夎Python渚濊禆
RUN pip install --no-cache-dir -r requirements.txt

# 寮€鍙戠幆澧冮樁娈?
FROM base as development

# 瀹夎寮€鍙戜緷璧?
RUN pip install --no-cache-dir \
    pytest \
    pytest-cov \
    black \
    pylint \
    mypy \
    ipython

# 澶嶅埗搴旂敤浠ｇ爜
COPY . .

# 鍒涘缓蹇呰鐩綍
RUN mkdir -p data logs temp \
    && chown -R appuser:appuser /app

# 璁剧疆鐜鍙橀噺
ENV APP_ENV=development \
    NTN_ENV=development \
    PYTHONPATH=/app \
    LOG_LEVEL=DEBUG

# 鍒囨崲鍒板簲鐢ㄧ敤鎴?
USER appuser

# 鏆撮湶绔彛
EXPOSE 5000 5555 5556

# 鍚姩鍛戒护
CMD ["python", "main.py", "--env", "development", "--mode", "all"]

# 娴嬭瘯鐜闃舵
FROM base as staging

# 澶嶅埗搴旂敤浠ｇ爜
COPY . .

# 鍒涘缓蹇呰鐩綍
RUN mkdir -p data logs temp \
    && chown -R appuser:appuser /app

# 璁剧疆鐜鍙橀噺
ENV APP_ENV=staging \
    NTN_ENV=staging \
    PYTHONPATH=/app \
    LOG_LEVEL=INFO

# 鍒囨崲鍒板簲鐢ㄧ敤鎴?
USER appuser

# 鏆撮湶绔彛
EXPOSE 5000 5555 5556

# 鍋ュ悍妫€鏌?
HEALTHCHECK --interval=30s --timeout=10s --start-period=90s --retries=5 \
    CMD python -c "import sys,urllib.request,socket; socket.setdefaulttimeout(5); sys.exit(0 if 200<=urllib.request.urlopen('http://localhost:5000/live', timeout=5).getcode()<300 else 1)"

# 鍚姩鍛戒护
CMD ["python", "main.py", "--env", "staging", "--mode", "all"]

# 鐢熶骇鐜闃舵
FROM base as production

# 澶嶅埗搴旂敤浠ｇ爜锛堟帓闄ゅ紑鍙戞枃浠讹級
COPY app/ ./app/
COPY config/ ./config/
COPY scripts/ ./scripts/
COPY main.py requirements.txt ./

# 鍒涘缓蹇呰鐩綍
RUN mkdir -p data logs temp \
    && chown -R appuser:appuser /app

# 璁剧疆鐜鍙橀噺
ENV APP_ENV=production \
    NTN_ENV=production \
    PYTHONPATH=/app \
    LOG_LEVEL=INFO

# 鍒囨崲鍒板簲鐢ㄧ敤鎴?
USER appuser

# 鏆撮湶绔彛
EXPOSE 5000 5555 5556

# 鍋ュ悍妫€鏌?
HEALTHCHECK --interval=30s --timeout=10s --start-period=90s --retries=5 \
    CMD python -c "import sys,urllib.request,socket; socket.setdefaulttimeout(5); sys.exit(0 if 200<=urllib.request.urlopen('http://localhost:5000/live', timeout=5).getcode()<300 else 1)"

# 鍚姩鍛戒护
CMD ["python", "main.py", "--env", "production", "--mode", "all"]
