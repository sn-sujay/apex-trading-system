"""
APEX Trading Intelligence System — Base Agent
All 20 agents inherit from APEXBaseAgent.
Provides: signal publishing, Redis pub/sub, structured logging, health checks.
"""
from __future__ import annotations
import asyncio
import logging
import time
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, Dict, Any, List

from .signal_schema import AgentSignal, SignalDirection, MarketRegime, SignalTimeframe, AssetClass
from .config import APEXConfig
from .constants import (
    KAFKA_SIGNAL_TOPIC, REDIS_SIGNAL_PREFIX,
    STRONG_SIGNAL_THRESHOLD, WEAK_SIGNAL_THRESHOLD
)


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
        agent_name: str,
        version: str = "1.0.0",
        config: Optional[APEXConfig] = None,
    ):
        self.agent_name = agent_name
        self.version = version
        self.config = config or APEXConfig.get()

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
        self.logger.setLevel(getattr(logging, self.config.log_level, logging.INFO))

    # ── Abstract Interface ──────────────────────────────────────────────────────────

    @abstractmethod
    async def analyze(self) -> AgentSignal:
        """
        Core analysis logic. Must return a populated AgentSignal.
        Called by run_cycle() on every tick/interval.
        """
        ...

    @abstractmethod
    async def _fetch_data(self) -> Dict[str, Any]:
        """
        Fetch raw data required for analysis (prices, news, macro data, etc.)
        """
        ...

    # ── Run Cycle ─────────────────────────────────────────────────────────────────

    async def run_cycle(self) -> Optional[AgentSignal]:
        """Execute one full analysis cycle: fetch → analyze → publish."""
        start = time.time()
        try:
            self._run_count += 1
            self._last_run_ts = start
            signal = await self.analyze()
            signal.agent_name = self.agent_name
            signal.agent_version = self.version
            signal.data_freshness_seconds = int(time.time() - start)

            self._last_signal = signal
            self._signal_history.append(signal)
            if len(self._signal_history) > 1000:
                self._signal_history.pop(0)

            await self._publish_signal(signal)
            elapsed = time.time() - start
            self.logger.info(
                f"Cycle complete | direction={signal.direction.value} "
                f"confidence={signal.confidence:.2f} | {elapsed*1000:.1f}ms"
            )
            return signal

        except Exception as e:
            self._error_count += 1
            self._is_healthy = self._error_count < 5
            self.logger.error(f"Cycle failed: {e}", exc_info=True)
            return None

    async def run_forever(self, interval_seconds: int = 60):
        """Run analysis in a loop at the given interval."""
        self.logger.info(f"Starting {self.agent_name} — interval={interval_seconds}s")
        while True:
            await self.run_cycle()
            await asyncio.sleep(interval_seconds)

    # ── Signal Publishing ──────────────────────────────────────────────────────────

    async def _publish_signal(self, signal: AgentSignal):
        """Publish signal to Redis and Kafka."""
        await self._publish_to_redis(signal)
        await self._publish_to_kafka(signal)

    async def _publish_to_redis(self, signal: AgentSignal):
        """Store latest signal in Redis for fast access."""
        try:
            if self._redis is None:
                import aioredis
                self._redis = await aioredis.from_url(
                    f"redis://{self.config.redis_host}:{self.config.redis_port}",
                    password=self.config.redis_password,
                    encoding="utf-8",
                    decode_responses=True,
                )
            key = f"{REDIS_SIGNAL_PREFIX}{self.agent_name}"
            await self._redis.setex(key, 300, signal.to_json())  # TTL 5 min
        except Exception as e:
            self.logger.warning(f"Redis publish failed: {e}")

    async def _publish_to_kafka(self, signal: AgentSignal):
        """Publish signal to Kafka topic for stream processing."""
        try:
            if self._kafka_producer is None:
                from aiokafka import AIOKafkaProducer
                self._kafka_producer = AIOKafkaProducer(
                    bootstrap_servers=self.config.kafka_bootstrap,
                    value_serializer=lambda v: v.encode("utf-8"),
                )
                await self._kafka_producer.start()

            await self._kafka_producer.send(
                KAFKA_SIGNAL_TOPIC,
                key=self.agent_name.encode(),
                value=signal.to_json(),
            )
        except Exception as e:
            self.logger.warning(f"Kafka publish failed: {e}")

    # ── Signal Factories ─────────────────────────────────────────────────────────────

    def _make_signal(
        self,
        direction: SignalDirection,
        confidence: float,
        symbol: str,
        reasoning: str,
        key_factors: Optional[List[str]] = None,
        **kwargs,
    ) -> AgentSignal:
        """Helper to build a properly-formed AgentSignal."""
        return AgentSignal(
            agent_name=self.agent_name,
            agent_version=self.version,
            direction=direction,
            confidence=min(max(confidence, 0.0), 1.0),
            symbol=symbol,
            reasoning=reasoning,
            key_factors=key_factors or [],
            **kwargs,
        )

    def _no_signal(self, reason: str = "Insufficient data") -> AgentSignal:
        return AgentSignal(
            agent_name=self.agent_name,
            direction=SignalDirection.NO_SIGNAL,
            confidence=0.0,
            reasoning=reason,
        )

    # ── Health & Diagnostics ───────────────────────────────────────────────────────

    def health_status(self) -> Dict[str, Any]:
        return {
            "agent": self.agent_name,
            "version": self.version,
            "is_healthy": self._is_healthy,
            "run_count": self._run_count,
            "error_count": self._error_count,
            "uptime_seconds": int(time.time() - self._start_time),
            "last_run": self._last_run_ts,
            "last_signal_direction": (
                self._last_signal.direction.value if self._last_signal else None
            ),
            "last_signal_confidence": (
                self._last_signal.confidence if self._last_signal else None
            ),
        }

    @property
    def recent_accuracy(self) -> Optional[float]:
        """
        Rough accuracy estimate: fraction of signals that had positive
        signal_score in the last 30 signals.
        """
        recent = self._signal_history[-30:]
        if not recent:
            return None
        hits = sum(1 for s in recent if abs(s.signal_score) >= WEAK_SIGNAL_THRESHOLD)
        return hits / len(recent)

    async def close(self):
        """Clean up connections."""
        if self._redis:
            await self._redis.close()
        if self._kafka_producer:
            await self._kafka_producer.stop()
        if self._db_pool:
            await self._db_pool.close()
