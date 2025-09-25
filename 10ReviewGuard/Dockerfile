# ReviewGuard妯＄粍涓籇ockerfile
# 浜哄伐瀹℃牳妯＄粍 - 鍩轰簬Python 3.11-slim锛屾敮鎸丗astAPI + ZeroMQ + Redis
# 閬靛惊AI鏅鸿兘浣撻┍鍔ㄤ氦鏄撶郴缁熸灦鏋勮鑼?

FROM python:3.11-slim as base

# 璁剧疆鐜鍙橀噺
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app/backend/src \
    APP_ENV=production

# 璁剧疆宸ヤ綔鐩綍
WORKDIR /app

# 鍒涘缓闈瀝oot鐢ㄦ埛
RUN groupadd --gid 1001 reviewguard && \
    useradd --uid 1001 --gid reviewguard --shell /bin/bash --create-home reviewguard

# 瀹夎绯荤粺渚濊禆
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list && apt-get update && apt-get install -y \
    build-essential \
    libzmq3-dev \
    pkg-config \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# 澶嶅埗鍚庣渚濊禆鏂囦欢
COPY backend/requirements.txt ./backend/

# 瀹夎Python渚濊禆
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r backend/requirements.txt

# 澶嶅埗鍚庣婧愪唬鐮?
COPY backend/ ./backend/

# 澶嶅埗閰嶇疆鏂囦欢
COPY .env.production .env.staging .env.example ./
COPY docker-compose.yml ./

# 鍒涘缓蹇呰鐩綍骞惰缃潈闄?
RUN mkdir -p /app/data /app/logs /app/config && \
    chown -R reviewguard:reviewguard /app

# 鍒囨崲鍒伴潪root鐢ㄦ埛
USER reviewguard

# 鍋ュ悍妫€鏌?
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 鏆撮湶绔彛
# 8000: FastAPI HTTP API
# 5555: ZeroMQ璁㈤槄绔彛
# 5556: ZeroMQ鍙戝竷绔彛
EXPOSE 8000 5555 5556

# 鍚姩鍛戒护 - 鍚姩ReviewGuard鍚庣鏈嶅姟
CMD ["uvicorn", "backend.src.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
