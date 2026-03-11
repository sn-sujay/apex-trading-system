"""
APEX Trading Intelligence System — Base Agent
All 20 agents inherit from APEXBaseAgent.
Provides: signal publishing, Redis pub/sub, structured logging, health checks.
"""
from __future__ import annotations
import asyncio
import logging
import time
from abc import ABC
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from typing import Optional, Dict, Any, List, Union

from .signal_schema import AgentSignal, SignalDirection, SignalTimeframe, AssetClass
from .config import APEXConfig
from .memory import ExperienceMemory
from .constants import (
    KAFKA_SIGNAL_TOPIC, REDIS_SIGNAL_PREFIX,
    WEAK_SIGNAL_THRESHOLD
)

# IST timezone constant — used everywhere in this module
IST = ZoneInfo("Asia/Kolkata")


logger = logging.getLogger(__name__)


class APEXBaseAgent(ABC):
    """
    Base class for all APEX Trading Intelligence agents.

    Subclasses implement:
        - analyze() -> AgentSignal   (core analysis logic)
        - _fetch_data() -> dict      (data fetching)
    """

    def __init__(
        self,
        agent_name: Optional[str] = None,
        version: str = "1.0.0",
        config: Optional[APEXConfig] = None,
        **kwargs
    ):
        self.agent_name = agent_name or self.__class__.__name__
        self.version = version
        self.config = config or APEXConfig()
        self._redis = kwargs.get("redis_client")

        # State
        self._last_signal: Optional[AgentSignal] = None
        self._signal_history: List[AgentSignal] = []
        self._run_count: int = 0
        self._error_count: int = 0
        self._last_run_ts: Optional[float] = None
        self._is_healthy: bool = True
        self._start_time = time.time()

        # Connections (lazy init)
        self._redis = None
        self._memory = ExperienceMemory(self.agent_name)
        self._kafka_producer = None
        self._db_pool = None

        self._setup_logging()

    def _setup_logging(self):
        self.logger = logging.getLogger(f"apex.agent.{self.agent_name}")
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            f"%(asctime)s | {self.agent_name} | %(levelname)s | %(message)s"
        )
        handler.setFormatter(formatter)
        if not self.logger.handlers:
            self.logger.addHandler(handler)
        self.logger.setLevel(
            getattr(
                logging,
                self.config.LOG_LEVEL,
                logging.INFO))

    # ── Abstract Interface ──────────────────────────────────────────────────

    async def analyze(self, market_data: Dict[str, Any]) -> AgentSignal:
        """
        Core analysis logic. Must return a populated AgentSignal.
        Called by run_cycle() on every tick/interval.
        """
        await self._fetch_data()
        return self._no_signal("Method not implemented")

    async def _fetch_data(self) -> Dict[str, Any]:
        """
        Fetch raw data required for analysis (prices, news, macro data, etc.)
        """
        return {}

    def on_tick(self, tick_data: Dict[str, Any]):
        """
        Hook for processing real-time market ticks.
        Overridden by agents that need per-tick responsiveness.
        """
        pass

    # ── Run Cycle ─────────────────────────────────────────────────

    async def run_cycle(self, **akwargs) -> Optional[AgentSignal]:
        """
        Orchestrates one full run cycle.
        Automatically:
            - Checks market hours
            - Calls analyze()
            - Publishes signal
            - Updates health
        """
        self._run_count += 1
        self._last_run_ts = time.time()

        if not self._is_market_hours():
            self.logger.info("Market closed - skipping cycle")
            return None

        try:
            # If market_data is provided in akwargs, use it; otherwise fetch.
            market_data = akwargs.get("market_data")
            if market_data is None:
                market_data = await self._fetch_data()
            
            signal = await self.analyze(market_data=market_data)
            signal = self._validate_signal(signal)
            await self._publish_signal(signal)
            self._last_signal = signal
            self._signal_history.append(signal)
            self._is_healthy = True
            return signal
        except Exception as e:
            self._error_count += 1
            self._is_healthy = False
            self.logger.error(f"Cycle error: {e}")
            return None

    # ── Market Hours ──• IST-aware ───────────────────────────────────────

    def _is_market_hours(self) -> bool:
        """Check if current time is within NSE market hours (09:15 - 15:30 IST)."""
        from datetime import time as dt_time
        now = datetime.now(IST)  # fix: IST-aware, was naive datetime.now()
        current_time = now.time()
        market_open = dt_time(9, 15)
        market_close = dt_time(15, 30)
        if now.weekday() >= 5:  # Sat/Sun in IST
            return False
        return market_open <= current_time <= market_close

    def _no_signal(self, reason: str = "") -> AgentSignal:
        """Return a no opinion signal."""
        return AgentSignal(
            timestamp=datetime.now(IST).isoformat(),  # fix: IST-aware, was naive datetime.now()
            agent_name=self.agent_name,
            direction=SignalDirection.NO_SIGNAL,
            confidence=0.0,
            reason=reason,
        )

    async def get_long_term_memory(self, market_data: Dict[str, Any]) -> str:
        """
        Retrieves relevant past experiences based on current market regime.
        """
        regime = market_data.get("regime", "SIDEWAYS")
        experiences = await self._memory.retrieve_relevant_experiences(regime)
        return self._memory.format_experiences_for_prompt(experiences)

    def _validate_signal(self, signal: AgentSignal) -> AgentSignal:
        """Validate and normalize signal values."""
        if signal.confidence < WEAK_SIGNAL_THRESHOLD:
            signal.direction = SignalDirection.NO_SIGNAL
        return signal

    async def run_forever(self, interval: int = 60):
        """Infinite loop for the agent, running every `interval` seconds."""
        self.logger.info(f"Starting {self.agent_name} loop (interval={interval}s)")
        while True:
            try:
                await self.run_cycle()
            except Exception as e:
                self.logger.error(f"Error in run_forever: {e}")
            await asyncio.sleep(interval)

    # ── Signal Publishing ──────────────────────────────────────────────

    async def _publish_signal(self, signal: AgentSignal):
        """Publish signal to Redis and (optionally) Kafka."""
        if self._redis:
            key = f"{REDIS_SIGNAL_PREFIX}:{self.agent_name}"
            await self._redis.set(key, signal.json(), ex=300)

    async def _publish_to_kafka(self, signal: AgentSignal):
        """Publish signal to Kafka topic."""
        if self._kafka_producer:
            self._kafka_producer.send(
                KAFKA_SIGNAL_TOPIC,
                value=signal.dict()
            )

    # ── Health & Status ────────────────────────────────────────────────

    def get_health(self) -> Dict[str, Any]:
        """Return agent health status snapshot."""
        return {
            "agent": self.agent_name,
            "version": self.version,
            "healthy": self._is_healthy,
            "run_count": self._run_count,
            "error_count": self._error_count,
            "uptime_secs(": time.time() - self._start_time,
            "last_run_ts": self._last_run_ts,
            "timestamp": datetime.now(IST).isoformat(),  # fix: IST-aware, was naive datetime.now()
        }

    def is_healthy(self) -> bool:
        return self._is_healthy

    def reset_state(self):
        """Reset agent state for testing."""
        self._run_count = 0
        self._error_count = 0
        self._last_signal = None
        self._signal_history = []
        self._is_healthy = True
        self._start_time = time.time()
