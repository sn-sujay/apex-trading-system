# ============================================================
# APEX Trading Intelligence System — Makefile
# ============================================================

.PHONY: help install infra-up infra-down db-init kafka-topics \
        backtest paper-trade live-trade dashboard test lint clean

PYTHON := python3
PIP    := pip3
DC     := docker-compose

# ---- Help --------------------------------------------------
help:
	@echo ""
	@echo "  APEX Trading Intelligence System"
	@echo "  ================================="
	@echo ""
	@echo "  Setup:"
	@echo "    make install        Install Python dependencies"
	@echo "    make infra-up       Start all infrastructure (DB, Kafka, Redis)"
	@echo "    make infra-down     Stop all infrastructure"
	@echo "    make db-init        Initialize TimescaleDB schema + seed data"
	@echo "    make kafka-topics   Create all Kafka topics"
	@echo ""
	@echo "  Trading:"
	@echo "    make backtest       Run full backtesting suite (10yr NSE data)"
	@echo "    make paper-trade    Start paper trading (no real money)"
	@echo "    make live-trade     Start live trading (real money — use with caution)"
	@echo "    make dashboard      Open monitoring dashboard"
	@echo ""
	@echo "  Development:"
	@echo "    make test           Run full test suite"
	@echo "    make lint           Run linter and type checker"
	@echo "    make clean          Remove build artifacts"
	@echo ""

# ---- Setup -------------------------------------------------
install:
	@echo "[APEX] Installing Python dependencies..."
	$(PIP) install -r requirements.txt
	@echo "[APEX] Done."

infra-up:
	@echo "[APEX] Starting infrastructure services..."
	$(DC) up -d timescaledb zookeeper kafka redis
	@echo "[APEX] Waiting for services to be healthy..."
	@sleep 10
	@$(MAKE) kafka-topics
	@echo "[APEX] Infrastructure ready."

infra-down:
	@echo "[APEX] Stopping infrastructure..."
	$(DC) down
	@echo "[APEX] Done."

infra-clean:
	@echo "[APEX] Stopping and removing all volumes..."
	$(DC) down -v
	@echo "[APEX] Done."

db-init:
	@echo "[APEX] Initializing TimescaleDB schema..."
	$(PYTHON) -c "from trading_system.data.db_init import init_db; init_db()"
	@echo "[APEX] Database initialized."

kafka-topics:
	@echo "[APEX] Creating Kafka topics..."
	docker exec apex-kafka kafka-topics --bootstrap-server localhost:9092 \
		--create --if-not-exists --topic market.ticks \
		--partitions 12 --replication-factor 1
	docker exec apex-kafka kafka-topics --bootstrap-server localhost:9092 \
		--create --if-not-exists --topic agent.signals \
		--partitions 6 --replication-factor 1
	docker exec apex-kafka kafka-topics --bootstrap-server localhost:9092 \
		--create --if-not-exists --topic decisions.output \
		--partitions 3 --replication-factor 1
	docker exec apex-kafka kafka-topics --bootstrap-server localhost:9092 \
		--create --if-not-exists --topic risk.alerts \
		--partitions 3 --replication-factor 1
	docker exec apex-kafka kafka-topics --bootstrap-server localhost:9092 \
		--create --if-not-exists --topic execution.orders \
		--partitions 6 --replication-factor 1
	@echo "[APEX] Kafka topics created."

# ---- Trading -----------------------------------------------
backtest:
	@echo "[APEX] Running backtesting suite..."
	@echo "[APEX] WARNING: This downloads 10yr NSE historical data (~2GB)."
	$(PYTHON) -m backtesting.run_full_suite
	@echo "[APEX] Backtesting complete. Results in backtesting/results/"

paper-trade:
	@echo "[APEX] Starting APEX in PAPER TRADING mode..."
	@echo "[APEX] No real money will be used."
	PAPER_TRADE_MODE=true ENABLE_LIVE_TRADING=false \
		$(PYTHON) -m trading_system.main
	
live-trade:
	@echo ""
	@echo "  !! WARNING: LIVE TRADING MODE !!"
	@echo "  Real money will be used. Ensure:"
	@echo "    1. Backtesting passed with Sharpe > 1.5"
	@echo "    2. Paper trading ran successfully for >= 30 days"
	@echo "    3. Risk limits in .env are correctly configured"
	@echo "    4. Zerodha Kite access token is fresh (< 24hrs)"
	@echo ""
	@read -p "  Type CONFIRM to proceed: " confirm; \
		[ "$$confirm" = "CONFIRM" ] || (echo "Aborted." && exit 1)
	PAPER_TRADE_MODE=false ENABLE_LIVE_TRADING=true \
		$(PYTHON) -m trading_system.main

dashboard:
	@echo "[APEX] Starting dashboard..."
	$(DC) up -d apex-app
	@echo "[APEX] Dashboard available at http://localhost:8080"
	@open http://localhost:8080 2>/dev/null || true

# ---- Development -------------------------------------------
test:
	@echo "[APEX] Running test suite..."
	$(PYTHON) -m pytest tests/ -v --cov=. --cov-report=html
	@echo "[APEX] Tests complete. Coverage report in htmlcov/"

test-agents:
	@echo "[APEX] Running agent unit tests..."
	$(PYTHON) -m pytest tests/agents/ -v

test-risk:
	@echo "[APEX] Running risk engine tests..."
	$(PYTHON) -m pytest tests/risk/ -v

test-execution:
	@echo "[APEX] Running execution layer tests..."
	$(PYTHON) -m pytest tests/execution/ -v

lint:
	@echo "[APEX] Running linter..."
	ruff check .
	@echo "[APEX] Running type checker..."
	mypy . --ignore-missing-imports
	@echo "[APEX] Lint complete."

format:
	@echo "[APEX] Formatting code..."
	black .
	ruff check . --fix
	@echo "[APEX] Done."

# ---- Data --------------------------------------------------
download-history:
	@echo "[APEX] Downloading 10yr NSE historical data..."
	$(PYTHON) -m data.download_history --start 2015-01-01 --end 2025-12-31
	@echo "[APEX] Historical data ready."

# ---- Agents ------------------------------------------------
agents-status:
	@echo "[APEX] Checking agent status..."
	$(PYTHON) -c "from core.agent_runner import status; status()"

# ---- Logs --------------------------------------------------
logs:
	$(DC) logs -f apex-app apex-agents

logs-app:
	$(DC) logs -f apex-app

logs-agents:
	$(DC) logs -f apex-agents

logs-kafka:
	$(DC) logs -f kafka

# ---- Clean -------------------------------------------------
clean:
	@echo "[APEX] Cleaning build artifacts..."
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name ".coverage" -delete 2>/dev/null || true
	@echo "[APEX] Clean done."
