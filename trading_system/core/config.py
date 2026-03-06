"""
APEX Trading Intelligence System — Configuration Manager
Loads from environment variables with sensible defaults.
"""
from __future__ import annotations
import os
from dataclasses import dataclass, field
from typing import Optional, List
from dotenv import load_dotenv

load_dotenv()


@dataclass
class APEXConfig:
    # ── Dhan API ───────────────────────────────────────────────────────────────────
    DHAN_CLIENT_ID: str             = field(default_factory=lambda: os.getenv("DHAN_CLIENT_ID", ""))
    DHAN_ACCESS_TOKEN: str          = field(default_factory=lambda: os.getenv("DHAN_ACCESS_TOKEN", ""))

    # ── Database ───────────────────────────────────────────────────────────────────
    db_host: str                    = field(default_factory=lambda: os.getenv("TIMESCALEDB_HOST", "localhost"))
    db_port: int                    = field(default_factory=lambda: int(os.getenv("TIMESCALEDB_PORT", "5432")))
    db_name: str                    = field(default_factory=lambda: os.getenv("TIMESCALEDB_DB", "apex_trading"))
    db_user: str                    = field(default_factory=lambda: os.getenv("TIMESCALEDB_USER", "apex"))
    db_password: str                = field(default_factory=lambda: os.getenv("TIMESCALEDB_PASSWORD", ""))

    @property
    def db_url(self) -> str:
        return f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"

    @property
    def async_db_url(self) -> str:
        return f"postgresql+asyncpg://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"

    # ── Redis ────────────────────────────────────────────────────────────────────────
    REDIS_HOST: str                 = field(default_factory=lambda: os.getenv("REDIS_HOST", "localhost"))
    REDIS_PORT: int                 = field(default_factory=lambda: int(os.getenv("REDIS_PORT", "6379")))
    redis_password: str             = field(default_factory=lambda: os.getenv("REDIS_PASSWORD", ""))

    @property
    def redis_url(self) -> str:
        return f"redis://:{self.redis_password}@{self.REDIS_HOST}:{self.REDIS_PORT}/0"

    # ── Kafka ────────────────────────────────────────────────────────────────────────
    KAFKA_BOOTSTRAP_SERVERS: str    = field(default_factory=lambda: os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"))
    kafka_topic_ticks: str          = field(default_factory=lambda: os.getenv("KAFKA_TOPIC_MARKET_TICKS", "market.ticks"))
    kafka_topic_signals: str        = field(default_factory=lambda: os.getenv("KAFKA_TOPIC_AGENT_SIGNALS", "agent.signals"))
    kafka_topic_orders: str         = field(default_factory=lambda: os.getenv("KAFKA_TOPIC_ORDERS", "execution.orders"))

    # ── Risk ─────────────────────────────────────────────────────────────────────────
    max_risk_per_trade_pct: float   = field(default_factory=lambda: float(os.getenv("MAX_RISK_PER_TRADE_PCT", "2.0")))
    max_daily_loss_pct: float       = field(default_factory=lambda: float(os.getenv("MAX_DAILY_LOSS_PCT", "5.0")))
    max_portfolio_drawdown_pct: float = field(default_factory=lambda: float(os.getenv("MAX_PORTFOLIO_DRAWDOWN_PCT", "15.0")))
    max_position_size_pct: float    = field(default_factory=lambda: float(os.getenv("MAX_POSITION_SIZE_PCT", "10.0")))
    min_agent_consensus: int        = field(default_factory=lambda: int(os.getenv("MIN_AGENT_CONSENSUS", "3")))
    vix_kill_switch_threshold: float = field(default_factory=lambda: float(os.getenv("VIX_KILL_SWITCH_THRESHOLD", "25.0")))
    max_sector_exposure_pct: float  = field(default_factory=lambda: float(os.getenv("MAX_SECTOR_EXPOSURE_PCT", "30.0")))
    max_leverage: float             = field(default_factory=lambda: float(os.getenv("MAX_LEVERAGE", "2.0")))

    # ── Capital ─────────────────────────────────────────────────────────────────────
    total_capital: float            = field(default_factory=lambda: float(os.getenv("TOTAL_CAPITAL_INR", "1000000")))
    core_allocation_pct: float      = field(default_factory=lambda: float(os.getenv("CORE_ALLOCATION_PCT", "60.0")))
    satellite_allocation_pct: float = field(default_factory=lambda: float(os.getenv("SATELLITE_ALLOCATION_PCT", "40.0")))

    # ── Feature Flags ───────────────────────────────────────────────────────────────
    enable_live_trading: bool       = field(default_factory=lambda: os.getenv("ENABLE_LIVE_TRADING", "false").lower() == "true")
    enable_paper_trading: bool      = field(default_factory=lambda: os.getenv("PAPER_TRADE_MODE", "true").lower() == "true")
    enable_options_trading: bool    = field(default_factory=lambda: os.getenv("ENABLE_OPTIONS_TRADING", "false").lower() == "true")
    enable_zero_dte: bool           = field(default_factory=lambda: os.getenv("ENABLE_ZERO_DTE", "false").lower() == "true")
    enable_learning_engine: bool    = field(default_factory=lambda: os.getenv("ENABLE_LEARNING_ENGINE", "true").lower() == "true")

    # ── LLM ──────────────────────────────────────────────────────────────────────────
    openai_api_key: str             = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    openai_model: str               = field(default_factory=lambda: os.getenv("OPENAI_MODEL", "gpt-4o"))
    anthropic_api_key: str          = field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY", ""))


# Singleton instance
Config = APEXConfig
