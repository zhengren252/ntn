# NeuroTrade Nexus (NTN) - Strategy Optimization Module Docker Configuration
# Optimized Multi-stage Build for CI/CD Efficiency and Size Reduction
# Version: 2.0 - Deep Optimization with Dependency Separation

# =================================================================
# Builder Stage - Compile Dependencies Only
# =================================================================
FROM python:3.11-slim AS builder

# Build-only environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive

WORKDIR /build

# Install build dependencies (compile-time only)
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || \
    sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list && \
    apt-get update && apt-get install -y --no-install-recommends --fix-missing \
        # Core build tools
        build-essential gcc g++ make cmake pkg-config \
        # Library development headers (compile-time only)
        libffi-dev libssl-dev libzmq3-dev libhdf5-dev \
        libatlas3-base gfortran libblas-dev liblapack-dev \
        libfreetype6-dev libpng-dev libjpeg-dev libsqlite3-dev \
        # Download tools
        curl wget git \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Install TA-Lib C library (Financial Technical Analysis)
RUN cd /tmp && \
    wget -q http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz && \
    tar -xzf ta-lib-0.4.0-src.tar.gz && \
    cd ta-lib/ && \
    ./configure --prefix=/usr --disable-static && \
    make -j$(nproc) && make install && \
    ldconfig && \
    cd / && rm -rf /tmp/ta-lib*

# Create optimized virtual environment
RUN python -m venv /opt/venv --copies
ENV PATH="/opt/venv/bin:$PATH"

# Copy and analyze requirements
COPY 04OptiCore/requirements.txt /build/

# Validate requirements and install core dependencies first
RUN echo "=== Dependency Analysis ===" && \
    grep -i zipline requirements.txt || echo "✅ No zipline in requirements" && \
    grep -i sqlite3 requirements.txt || echo "✅ No sqlite3 in requirements" && \
    echo "✅ Critical packages:" && grep -E "(riskfolio-lib|cvxpy|fastapi|numpy|pandas)" requirements.txt

# Optimized installation strategy: Core packages first for better caching
RUN pip install --upgrade pip setuptools wheel && \
    # Install core numerical packages with optimized builds
    pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple \
        numpy==1.25.2 pandas==2.1.4 scipy==1.11.4 && \
    # Install remaining dependencies in batches for better error handling
    pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt && \
    # Cleanup build artifacts
    find /opt/venv -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true && \
    find /opt/venv -name "*.pyc" -delete && \
    find /opt/venv -name "*.pyo" -delete

# =================================================================
# Production Stage - Runtime Environment Only
# =================================================================
FROM python:3.11-slim AS production

# Production metadata
LABEL maintainer="NeuroTrade Nexus Team" \
      description="Strategy Optimization Module - Production Optimized" \
      version="2.0.0" \
      component="opticore" \
      build-optimization="multi-stage-v2"

# Runtime-only environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    NTN_ENVIRONMENT=production \
    PYTHONPATH=/app \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Install minimal runtime dependencies only
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || \
    sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list && \
    apt-get update && apt-get install -y --no-install-recommends \
        # Minimal runtime libraries (no dev packages)
        libzmq5 libhdf5-310 libatlas3-base \
        libfreetype6 libpng16-16 libjpeg62-turbo \
        # Essential utilities
        curl ca-certificates \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* /root/.cache

# Copy optimized virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Copy TA-Lib runtime libraries only
COPY --from=builder /usr/lib/libta_lib.so* /usr/lib/
COPY --from=builder /usr/include/ta-lib/ /usr/include/ta-lib/

# Update shared library cache
RUN ldconfig

# Create secure non-root user with minimal permissions
RUN groupadd -r -g 1000 ntn && \
    useradd -r -u 1000 -g ntn -d /app -s /bin/bash \
            --no-log-init --create-home ntn

# Create optimized directory structure
RUN mkdir -p /app/{logs,data,cache,temp,config} \
             /app/tests/logs \
             /app/supabase/migrations && \
    # Set secure permissions
    chown -R ntn:ntn /app && \
    chmod 750 /app && \
    chmod -R 755 /app/{logs,data,cache,temp,config}

# Copy application code with proper ownership
COPY --chown=ntn:ntn 04OptiCore/. .

# Set executable permissions for scripts
RUN find /app -name "*.sh" -type f -exec chmod +x {} \; 2>/dev/null || true

# Create optimized health check script
RUN printf '#!/bin/bash\n\
curl -f -m 10 --retry 3 http://localhost:8000/health || exit 1\n' > /app/healthcheck.sh && \
    chmod +x /app/healthcheck.sh && \
    chown ntn:ntn /app/healthcheck.sh

# Expose application ports
EXPOSE 8000 5555 5556

# Optimized health check with better intervals
HEALTHCHECK --interval=30s --timeout=15s --start-period=60s --retries=3 \
    CMD /app/healthcheck.sh

# Switch to non-root user for security
USER ntn

# Production startup command with optimized worker configuration
CMD ["uvicorn", "api.app:app", "--host", "0.0.0.0", "--port", "8000", \
     "--workers", "2", "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--access-log", "--log-level", "info"]

# =================================================================
# Build Instructions & Optimization Notes
# =================================================================
# Optimized Build: docker build --target production -t ntn-opticore:v2 .
# Size Comparison: docker images | grep opticore
# 
# Key Optimizations in v2.0:
# 1. Separated build and runtime dependencies completely
# 2. Removed all dev packages from production stage
# 3. Optimized layer caching with better dependency ordering
# 4. Enhanced security with minimal attack surface
# 5. Reduced worker count for better resource utilization
# 6. Improved health check with retry mechanism
# 
# Expected Size Reduction: 40-60% compared to v1.0
# =================================================================