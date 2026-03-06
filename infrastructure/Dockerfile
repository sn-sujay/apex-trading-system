# =============================================================================
# APEX Trading Intelligence System -- Multi-Stage Production Dockerfile
# Stage 1: builder  (compiles C extensions, TA-Lib, all deps)
# Stage 2: runtime  (lean image, no build tools)
# =============================================================================

# ---- Stage 1: builder -------------------------------------------------------
FROM python:3.11-slim AS builder

ARG TALIB_VERSION=0.4.28

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    wget \
    curl \
    git \
    libssl-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Build and install TA-Lib C library from source (required by ta-lib Python wheel)
RUN wget -q https://sourceforge.net/projects/ta-lib/files/ta-lib/0.4.0/ta-lib-0.4.0-src.tar.gz/download \
        -O /tmp/ta-lib.tar.gz && \
    tar -xzf /tmp/ta-lib.tar.gz -C /tmp && \
    cd /tmp/ta-lib && \
    ./configure --prefix=/usr/local && \
    make -j$(nproc) && \
    make install && \
    ldconfig && \
    rm -rf /tmp/ta-lib*

WORKDIR /build

# Install Python deps into an isolated prefix we can copy to runtime
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir --prefix=/install -r requirements.txt

# ---- Stage 2: runtime -------------------------------------------------------
FROM python:3.11-slim AS runtime

LABEL maintainer="sn-sujay" \
      description="APEX Multi-Agent AI Trading System" \
      version="1.0.0"

# Runtime system deps only (no build tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    nginx \
    supervisor \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy TA-Lib shared library from builder
COPY --from=builder /usr/local/lib/libta_lib* /usr/local/lib/
COPY --from=builder /usr/local/include/ta-lib /usr/local/include/ta-lib
RUN ldconfig

# Copy installed Python packages from builder
COPY --from=builder /install /usr/local

# Create non-root user
RUN groupadd -g 1000 apex && useradd -m -u 1000 -g apex apex

WORKDIR /app

# Copy application source
COPY trading_system/ ./trading_system/
COPY scripts/ ./scripts/

# Configure nginx
COPY infrastructure/nginx.conf /etc/nginx/nginx.conf
RUN rm -f /etc/nginx/sites-enabled/default /etc/nginx/sites-available/default

# Configure supervisor
COPY infrastructure/supervisord.conf /etc/supervisor/conf.d/apex.conf

# Create all required runtime directories with correct ownership
RUN mkdir -p \
        /app/logs \
        /app/data \
        /var/log/apex \
        /var/log/supervisor \
        /run/nginx && \
    chown -R apex:apex /app/logs /app/data && \
    chown -R root:root /var/log/supervisor /run/nginx

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    ENVIRONMENT=paper \
    LOG_LEVEL=INFO \
    SYSTEM_NAME=APEX \
    REDIS_HOST=redis \
    REDIS_PORT=6379 \
    REDIS_DB=0 \
    KAFKA_BOOTSTRAP_SERVERS=kafka:9092 \
    KAFKA_TOPIC_TICKS=apex.ticks \
    KAFKA_TOPIC_SIGNALS=apex.signals \
    KAFKA_TOPIC_ORDERS=apex.orders \
    API_HOST=0.0.0.0 \
    API_PORT=8000 \
    DASHBOARD_HOST=0.0.0.0 \
    DASHBOARD_PORT=8501 \
    TRADING_MODE=paper \
    PAPER_TRADE_MODE=true \
    ENABLE_LIVE_TRADING=false \
    TOTAL_CAPITAL_INR=1000000 \
    MAX_RISK_PER_TRADE_PCT=2.0 \
    MAX_PORTFOLIO_DRAWDOWN_PCT=15.0 \
    VIX_KILL_SWITCH_THRESHOLD=25.0 \
    LOG_FILE=/app/logs/apex.log

EXPOSE 8000 8501 80

HEALTHCHECK --interval=30s --timeout=10s --start-period=90s --retries=3 \
    CMD curl -fsSL http://localhost:8000/health || exit 1

CMD ["/usr/bin/supervisord", "-n", "-c", "/etc/supervisor/conf.d/apex.conf"]
