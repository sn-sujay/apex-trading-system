#!/usr/bin/env bash
# APEX Trading Intelligence System — Deploy Script
# Usage: ./infrastructure/deploy.sh [dev|prod|stop|logs|status|migrate|clean]

set -euo pipefail

COMPOSE_FILE="docker-compose.yml"
PROJECT="apex"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
log()  { echo -e "${GREEN}[APEX]${NC} $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
err()  { echo -e "${RED}[ERROR]${NC} $*" >&2; exit 1; }

check_deps() {
    command -v docker  >/dev/null 2>&1 || err "docker not found"
    command -v docker compose >/dev/null 2>&1 || err "docker compose not found"
}

cmd="${1:-dev}"

case "$cmd" in
  dev)
    log "Starting APEX in DEVELOPMENT mode..."
    check_deps
    [ -f .env ] || { cp env.example .env; warn "Created .env from env.example — fill in your API keys!"; }
    docker compose -p "$PROJECT" -f "$COMPOSE_FILE" up --build -d
    log "API: http://localhost:8000 | Dashboard: http://localhost:8501"
    ;;
  prod)
    log "Starting APEX in PRODUCTION mode..."
    check_deps
    [ -f .env ] || err ".env file required for production."
    docker compose -p "$PROJECT" -f "$COMPOSE_FILE" up --build -d
    log "Production deployment complete."
    ;;
  stop)
    docker compose -p "$PROJECT" down
    log "All services stopped."
    ;;
  restart)
    docker compose -p "$PROJECT" down
    docker compose -p "$PROJECT" up --build -d
    log "Restart complete."
    ;;
  logs)
    service="${2:-}"
    if [ -n "$service" ]; then
      docker compose -p "$PROJECT" logs -f "$service"
    else
      docker compose -p "$PROJECT" logs -f
    fi
    ;;
  status)
    docker compose -p "$PROJECT" ps
    ;;
  migrate)
    log "Running TimescaleDB migrations..."
    docker compose -p "$PROJECT" exec timescaledb \
      psql -U apex_user -d apex_trading -f /docker-entrypoint-initdb.d/db_schema.sql
    log "Migrations complete."
    ;;
  clean)
    warn "This will remove all containers, volumes, and images. Are you sure? (y/N)"
    read -r confirm
    [ "$confirm" = "y" ] || exit 0
    docker compose -p "$PROJECT" down -v --rmi all
    log "Clean complete."
    ;;
  *)
    echo "Usage: $0 [dev|prod|stop|restart|logs [service]|status|migrate|clean]"
    exit 1
    ;;
esac
