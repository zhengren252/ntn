# NeuroTrade Nexus (NTN) - Strategy Optimization Module Docker Configuration
# Strategy Optimization Module Dockerfile
# Multi-stage build to reduce final image size

# =================================================================
# Builder Stage
# =================================================================
FROM python:3.11-slim AS builder

# Set build stage environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive

# Set working directory
WORKDIR /app

# Install system dependencies
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list && apt-get update && apt-get install -y --fix-missing -o Acquire::Retries=3 -o Acquire::http::Timeout=30 \
    build-essential \
    gcc \
    g++ \
    make \
    cmake \
    pkg-config \
    libffi-dev \
    libssl-dev \
    libzmq3-dev \
    libhdf5-dev \
    libatlas3-base \
    gfortran \
    libblas-dev \
    liblapack-dev \
    libfreetype6-dev \
    libpng-dev \
    libjpeg-dev \
    curl \
    wget \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install TA-Lib C library (Financial Technical Analysis Library)
RUN cd /tmp && \
    wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz && \
    tar -xzf ta-lib-0.4.0-src.tar.gz && \
    cd ta-lib/ && \
    ./configure --prefix=/usr && \
    make && \
    make install && \
    cd / && \
    rm -rf /tmp/ta-lib*

# Create virtual environment and install python dependencies
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements file
COPY 04OptiCore/requirements.txt .

# Verify requirements.txt content to ensure zipline is removed
RUN echo "=== Verifying requirements.txt content ===" && \
    grep -i zipline requirements.txt || echo "✅ No zipline found in requirements.txt" && \
    grep -i sqlite3 requirements.txt || echo "✅ No sqlite3 found in requirements.txt" && \
    grep riskfolio-lib requirements.txt && \
    grep cvxpy requirements.txt

# Install additional system dependencies to support Python package compilation
# Support for sqlite3 and other packages that need compilation
RUN apt-get update && apt-get install -y gcc libsqlite3-dev && rm -rf /var/lib/apt/lists/*

# Upgrade pip and install python dependencies
RUN pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple numpy==1.25.2 pandas==2.1.4 scipy==1.11.4 && \
    pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt

# =================================================================
# Production Stage
# =================================================================
FROM python:3.11-slim AS production

# Set maintainer information and labels
LABEL maintainer="NeuroTrade Nexus Team" \
      description="Strategy Optimization Module for NeuroTrade Nexus" \
      version="1.0.0" \
      component="opticore"

# Set production environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    NTN_ENVIRONMENT=production \
    PYTHONPATH=/app \
    PATH="/opt/venv/bin:$PATH"

# Set working directory
WORKDIR /app

# Install runtime dependencies
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list && apt-get update && apt-get install -y --no-install-recommends \
    libzmq5 \
    libhdf5-310 \
    libatlas3-base \
    libfreetype6 \
    libpng16-16 \
    libjpeg62-turbo \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment and TA-Lib library from builder stage
COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /usr/lib/libta_lib.* /usr/lib/
COPY --from=builder /usr/include/ta-lib/ /usr/include/ta-lib/

# Create non-root user
RUN groupadd -r ntn && useradd -r -g ntn -d /app -s /bin/bash ntn

# Create necessary directory structure
RUN mkdir -p /app/logs \
             /app/data \
             /app/cache \
             /app/temp \
             /app/config \
             /app/tests/logs \
             /app/supabase/migrations && \
    chown -R ntn:ntn /app

# Copy application code
COPY --chown=ntn:ntn 04OptiCore/. .

# Set permissions
RUN chmod +x /app/scripts/*.sh 2>/dev/null || true && \
    chmod 755 /app

# Create health check script
RUN echo '#!/bin/bash\n\
curl -f http://localhost:8000/health || exit 1' > /app/healthcheck.sh && \
    chmod +x /app/healthcheck.sh && \
    chown ntn:ntn /app/healthcheck.sh

# Expose ports
EXPOSE 8000 5555 5556

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD /app/healthcheck.sh

# Switch to non-root user
USER ntn

# Set startup command
CMD ["uvicorn", "api.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]

# =================================================================
# Docker build and run instructions
# =================================================================
# Build: docker build --target production -t ntn-opticore:latest .
# Run: docker run -d -p 8000:8000 -p 5555:5555 -p 5556:5556 \
#      -e NTN_ENVIRONMENT=production \
#      -e DATABASE_PATH=/app/data/opticore.db \
#      -e REDIS_HOST=redis \
#      -e ZMQ_SUBSCRIBER_PORT=5555 \
#      -e ZMQ_PUBLISHER_PORT=5556 \
#      -v /host/data:/app/data \
#      -v /host/logs:/app/logs \
#      --name ntn-opticore \
#      ntn-opticore:latest