# NeuroTrade Nexus (NTN) - Strategy Optimization Module Docker Configuration
# Single-stage build - Final stable version without problematic dependencies
# Version: 9.0 - Ultra-simplified build without compilation dependencies

FROM python:3.11-slim

# Production metadata
LABEL maintainer="NeuroTrade Nexus Team" \
      description="Strategy Optimization Module - Ultra Stable" \
      version="9.0.0" \
      component="opticore"

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    NTN_ENVIRONMENT=production \
    PYTHONPATH=/app \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# 【Step 1: Install basic system dependencies】
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || \
    sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list && \
    apt-get update && apt-get install -y --no-install-recommends \
        # Build tools for basic compilation
        build-essential gcc g++ \
        # Library development headers
        libffi-dev libssl-dev \
        # Download tools
        curl wget \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Create user matching host UID/GID (1000)
RUN groupadd -g 1000 vscode && useradd -m -u 1000 -g 1000 vscode

# Copy requirements file
COPY 04OptiCore/requirements.txt .

# 【Step 2: Create virtual environment and install dependencies】
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# First: Install core runtime dependencies
RUN echo "=== Installing Core Runtime Dependencies ===" && \
    /opt/venv/bin/pip install --upgrade pip==23.3.1 setuptools==69.0.2 wheel==0.42.0 && \
    /opt/venv/bin/pip install --no-cache-dir \
        uvicorn[standard]==0.24.0 \
        fastapi==0.104.1 \
        pydantic==2.5.0 \
        pydantic-settings==2.1.0 && \
    echo "=== Core runtime installation completed ===" && \
    /opt/venv/bin/python -c "import uvicorn; print('✅ uvicorn available')"

# Second: Install minimal financial data libraries (no compilation required)
RUN echo "=== Installing Financial Data Libraries ===" && \
    /opt/venv/bin/pip install --no-cache-dir \
        # Financial computations
        numpy-financial==1.0.0 \
        # Financial data analysis
        yfinance==0.2.28 && \
    echo "=== Financial data libraries installation completed ==="

# Third: Install remaining dependencies (filtered to exclude ALL problematic packages)
RUN echo "=== Installing remaining dependencies ===" && \
    # Create filtered requirements without ALL problematic packages
    grep -v '^TA-Lib' requirements.txt | \
    grep -v '^pandas-ta' | \
    grep -v '^tulipy' | \
    grep -v '^numpy-financial' | \
    grep -v '^yfinance' | \
    grep -v '^vectorbt' | \
    grep -v '^#' | \
    grep -v '^$' > /tmp/filtered_requirements.txt && \
    /opt/venv/bin/pip install --no-cache-dir -r /tmp/filtered_requirements.txt && \
    echo "=== All dependencies installation completed ==="

# Verify installation success
RUN echo "=== Final verification ===" && \
    /opt/venv/bin/python -c "import uvicorn, fastapi, pandas, numpy; print('✅ Core imports successful')" && \
    echo "=== Installation verification completed ==="

# Copy application code
COPY 04OptiCore/. .

# 【Step 3: Configure directories and permissions - Simplified】
RUN mkdir -p /app/{logs,data,cache,temp,config} /app/tests/logs /app/supabase/migrations

# Set executable permissions for scripts (simplified)
RUN find /app -name "*.sh" -type f -exec chmod +x {} \; 2>/dev/null || true

# Pre-create application runtime directories with proper permissions
RUN mkdir -p /app/data/{development,production,test} \
             /app/logs/{development,production,test} \
             /app/cache/{development,production,test} \
             /app/temp/{development,production,test} && \
    # Set ownership for app and virtual environment
    chown -R vscode:vscode /app /opt/venv && \
    chmod -R 755 /app/{logs,data,cache,temp,config}

# Create enhanced health check script with dependency verification
RUN printf '#!/bin/bash\n\
# Verify critical dependencies\n\
/opt/venv/bin/python -c "import uvicorn, fastapi, pandas, numpy" || exit 1\n\
# Check service health\n\
curl -f -m 10 --retry 3 http://localhost:8000/health || exit 1\n' > /app/healthcheck.sh && \
    chmod +x /app/healthcheck.sh && \
    chown vscode:vscode /app/healthcheck.sh

# Switch to non-root user
USER vscode

# Expose application ports
EXPOSE 8000 5555 5556

# Enhanced health check with longer start period
HEALTHCHECK --interval=30s --timeout=15s --start-period=90s --retries=3 \
    CMD /app/healthcheck.sh

# Production startup command - Launch FastAPI via uvicorn
CMD ["/opt/venv/bin/python", "-m", "uvicorn", "api.app:app", "--host", "0.0.0.0", "--port", "8000"]