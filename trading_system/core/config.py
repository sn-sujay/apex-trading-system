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
    # ── Zerodha Kite ──────────────────────────────────────────────────────────────────────
    kite_api_key: str           = field(default_factory=lambda: os.getenv("KITE_API_KEY", ""))
    kite_api_secret: str        = field(default_factory=lambda: os.getenv("KITE_API_SECRET", ""))
    kite_access_token: str      = field(default_factory=lambda: os.getenv("KITE_ACCESS_TOKEN", ""))
    kite_user_id: str           = field(default_factory=lambda: os.getenv("KITE_USER_ID", ""))

    # ── Upstox ────────────────────────────────────────────────────────────────────────
    upstox_api_key: str         = field(default_factory=lambda: os.getenv("UPSTOX_API_KEY", ""))
    upstox_api_secret: str      = field(default_factory=lambda: os.getenv("UPSTOX_API_SECRET", ""))
    upstox_access_token: str    = field(default_factory=lambda: os.getenv("UPSTOX_ACCESS_TOKEN", ""))

    # ── Database ─────────────────────────────────────────────────────────────────────────
    db_host: str                = field(default_factory=lambda: os.getenv("TIMESCALEDB_HOST", "localhost"))
    db_port: int                = field(default_factory=lambda: int(os.getenv("TIMESCALEDB_PORT", "5432")))
    db_name: str                = field(default_factory=lambda: os.getenv("TIMESCALEDB_DB", "apex_trading"))
    db_user: str                = field(default_factory=lambda: os.getenv("TIMESCALEDB_USER", "apex"))
    db_password: str            = field(default_factory=lambda: os.getenv("TIMESCALEDB_PASSWORD", ""))

    @property
    def db_url(self) -> str:
        return f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"

    @property
    def async_db_url(self) -> str:
        return f"postgresql+asyncpg://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"

    # ── Redis ──────────────────────────────────────────────────────────────────────────
    redis_host: str             = field(default_factory=lambda: os.getenv("REDIS_HOST", "localhost"))
    redis_port: int             = field(default_factory=lambda: int(os.getenv("REDIS_PORT", "6379")))
    redis_password: Optional[str] = field(default_factory=lambda: os.getenv("REDIS_PASSWORD", None))
    redis_db: int               = 0

    # ── Kafka ──────────────────────────────────────────────────────────────────────────
    kafka_bootstrap: str        = field(default_factory=lambda: os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"))
    kafka_group_id: str         = "apex-consumers"

    # ── LLM / AI ─────────────────────────────────────────────────────────────────────────
    openai_api_key: str         = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    anthropic_api_key: str      = field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY", ""))
    groq_api_key: str           = field(default_factory=lambda: os.getenv("GROQ_API_KEY", ""))
    llm_model: str              = field(default_factory=lambda: os.getenv("LLM_MODEL", "gpt-4o-mini"))

    # ── News / Sentiment APIs ────────────────────────────────────────────────────────────
    newsapi_key: str            = field(default_factory=lambda: os.getenv("NEWSAPI_KEY", ""))
    gnews_api_key: str          = field(default_factory=lambda: os.getenv("GNEWS_API_KEY", ""))
    alpha_vantage_key: str      = field(default_factory=lambda: os.getenv("ALPHA_VANTAGE_API_KEY", ""))
    eodhd_api_key: str          = field(default_factory=lambda: os.getenv("EODHD_API_KEY", ""))

    # ── Trading Parameters ────────────────────────────────────────────────────────────────
    paper_trade: bool           = field(default_factory=lambda: os.getenv("PAPER_TRADE", "true").lower() == "true")
    max_daily_loss_pct: float   = field(default_factory=lambda: float(os.getenv("MAX_DAILY_LOSS_PCT", "0.02")))
    max_position_size_pct: float= field(default_factory=lambda: float(os.getenv("MAX_POSITION_SIZE_PCT", "0.05")))
    kill_switch_vix: float      = field(default_factory=lambda: float(os.getenv("KILL_SWITCH_VIX", "30")))

    # ── API Server ────────────────────────────────────────────────────────────────────
    api_host: str               = field(default_factory=lambda: os.getenv("API_HOST", "0.0.0.0"))
    api_port: int               = field(default_factory=lambda: int(os.getenv("API_PORT", "8000")))
    api_secret_key: str         = field(default_factory=lambda: os.getenv("API_SECRET_KEY", "change-me-in-production"))

    # ── Logging ─────────────────────────────────────────────────────────────────────────
    log_level: str              = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    log_file: str               = "logs/apex.log"

    # ── Watchlists ────────────────────────────────────────────────────────────────────────
    nifty50_symbols: List[str]  = field(default_factory=lambda: [
        "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK",
        "HINDUNILVR", "ITC", "SBIN", "BHARTIARTL", "KOTAKBANK",
        "LT", "AXISBANK", "ASIANPAINT", "BAJFINANCE", "HCLTECH",
        "SUNPHARMA", "MARUTI", "WIPRO", "ULTRACEMCO", "TITAN",
        "ONGC", "NESTLEIND", "ADANIENT", "POWERGRID", "NTPC",
        "JSWSTEEL", "TATASTEEL", "TECHM", "GRASIM", "INDUSINDBK",
    ])

    sector_etfs: List[str]      = field(default_factory=lambda: [
        "NIFTYBEES", "BANKBEES", "ITBEES", "PSUBNKBEES",
        "PHARMBEES", "AUTOBEES", "FMCGBEES",
    ])

    _instance = None

    @classmethod
    def get(cls) -> "APEXConfig":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
