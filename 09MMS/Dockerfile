# 甯傚満寰粨鏋勪豢鐪熷紩鎿?MMS) Docker閰嶇疆鏂囦欢
# 澶氶樁娈垫瀯寤猴紝浼樺寲闀滃儚澶у皬鍜屽畨鍏ㄦ€?

# 鏋勫缓闃舵
FROM python:3.11-slim as builder

# 璁剧疆宸ヤ綔鐩綍
WORKDIR /app

# 瀹夎绯荤粺渚濊禆
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list && apt-get update && apt-get install -y --fix-missing -o Acquire::Retries=3 -o Acquire::http::Timeout=30 \
    gcc \
    g++ \
    make \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# 澶嶅埗渚濊禆鏂囦欢
COPY 09MMS/requirements.txt .

# 鍒涘缓铏氭嫙鐜骞跺畨瑁匬ython渚濊禆
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir --upgrade pip setuptools wheel
RUN pip install --no-cache-dir --default-timeout=100 --retries 3 --index-url https://pypi.org/simple -r requirements.txt

# 杩愯闃舵
FROM python:3.11-slim as runtime

# 璁剧疆鐜鍙橀噺
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    APP_ENV=production

# 鍒涘缓闈瀝oot鐢ㄦ埛
RUN groupadd -r mms && useradd -r -g mms mms

# 瀹夎杩愯鏃朵緷璧?
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list && apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 澶嶅埗铏氭嫙鐜
COPY --from=builder /opt/venv /opt/venv

# 璁剧疆宸ヤ綔鐩綍
WORKDIR /app

# 鍒涘缓蹇呰鐨勭洰褰?
RUN mkdir -p /app/data /app/logs /app/config && \
    chown -R mms:mms /app

# 澶嶅埗搴旂敤浠ｇ爜
COPY --chown=mms:mms 09MMS/src/ ./src/
COPY --chown=mms:mms 09MMS/scripts/ ./scripts/
COPY --chown=mms:mms 09MMS/config/ ./config/
COPY --chown=mms:mms 09MMS/*.py ./
COPY --chown=mms:mms 09MMS/*.md ./
COPY --chown=mms:mms 09MMS/*.txt ./

# 鍒囨崲鍒伴潪root鐢ㄦ埛
USER mms

# 鏆撮湶绔彛
EXPOSE 8000 5555 5556 5557

# 鍋ュ悍妫€鏌?
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 鍚姩鍛戒护
CMD ["python", "-m", "uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]

# 鍏冩暟鎹爣绛?
LABEL maintainer="NeuroTrade Nexus Team" \
      version="1.0.0" \
      description="Market Microstructure Simulation Engine" \
      org.opencontainers.image.title="MMS" \
      org.opencontainers.image.description="Market Microstructure Simulation Engine" \
      org.opencontainers.image.version="1.0.0" \
      org.opencontainers.image.vendor="NeuroTrade Nexus" \
      org.opencontainers.image.licenses="MIT"
