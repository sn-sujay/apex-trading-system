#!/usr/bin/env bash
# APEX Trading System — Production Deployment Script
set -euo pipefail

APP_NAME="apex-trading-system"
IMAGE_NAME="apex-trading"
CONTAINER_NAME="apex-trading"
PORT_API=8000
PORT_DASHBOARD=8501
LOG_DIR="/var/log/apex"

echo "==================================================="
echo " APEX Trading System — Deployment"
echo " $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
echo "==================================================="

# 1. Pull latest code
echo "[1/6] Pulling latest code..."
git pull origin main

# 2. Build Docker image
echo "[2/6] Building Docker image..."
docker build -f infrastructure/Dockerfile -t ${IMAGE_NAME}:latest -t ${IMAGE_NAME}:$(git rev-parse --short HEAD) .

# 3. Stop existing container gracefully
echo "[3/6] Stopping existing container..."
if docker ps -q --filter name=${CONTAINER_NAME} | grep -q .; then
    docker stop ${CONTAINER_NAME} --time 30
    docker rm ${CONTAINER_NAME}
    echo "  Stopped and removed existing container."
else
    echo "  No existing container found."
fi

# 4. Create log directory
mkdir -p ${LOG_DIR}

# 5. Start new container
echo "[5/6] Starting new container..."
docker run -d \
    --name ${CONTAINER_NAME} \
    --restart unless-stopped \
    -p ${PORT_API}:8000 \
    -p ${PORT_DASHBOARD}:8501 \
    -p 80:80 \
    -v ${LOG_DIR}:/var/log/apex \
    -v $(pwd)/data:/app/data \
    --env-file .env \
    --memory="2g" \
    --cpus="2" \
    ${IMAGE_NAME}:latest

# 6. Health check
echo "[6/6] Waiting for health check..."
for i in $(seq 1 12); do
    if curl -sf http://localhost:${PORT_API}/health > /dev/null 2>&1; then
        echo "  Health check passed after ${i}x5s wait."
        break
    fi
    if [ $i -eq 12 ]; then
        echo "  ERROR: Health check failed after 60s. Rolling back..."
        docker stop ${CONTAINER_NAME}
        docker rm ${CONTAINER_NAME}
        exit 1
    fi
    echo "  Waiting... (${i}/12)"
    sleep 5
done

echo "==================================================="
echo " Deployment successful!"
echo " API:       http://localhost:${PORT_API}/docs"
echo " Dashboard: http://localhost:${PORT_DASHBOARD}"
echo "==================================================="
