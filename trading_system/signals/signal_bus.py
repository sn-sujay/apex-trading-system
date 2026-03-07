"""
InterAgentSignalBus — collects signals from all 20 agents, normalises them,
and broadcasts the aggregated view to the MasterDecisionMaker.
"""
from __future__ import annotations
import asyncio
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List
from ..core.signal_schema import AgentSignal, SignalDirection


class InterAgentSignalBus:
    """
    Pub/Sub bus for agent signal distribution.
    Agents publish signals; downstream consumers subscribe to the aggregated feed.
    """

    def __init__(self, redis_client=None):
        self.redis = redis_client
        self._signals: Dict[str, AgentSignal] = {}  # agent_name -> latest signal
        self._subscribers: List[Callable] = []
        self._signal_history: List[Dict] = []
        self._lock = asyncio.Lock()

    async def publish(self, signal: AgentSignal):
        """Agent calls this to publish its signal."""
        async with self._lock:
            self._signals[signal.agent_name] = signal
            self._signal_history.append({
                "agent": signal.agent_name,
                "direction": signal.direction.value,
                "confidence": signal.confidence,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            if len(self._signal_history) > 1000:
                self._signal_history = self._signal_history[-500:]

        for subscriber in self._subscribers:
            try:
                await subscriber(signal)
            except Exception:
                pass

    def subscribe(self, callback: Callable):
        """Subscribe to new signal events."""
        self._subscribers.append(callback)

    def get_all_signals(self) -> Dict[str, AgentSignal]:
        return dict(self._signals)

    def get_signal_summary(self) -> Dict[str, Any]:
        signals = list(self._signals.values())
        if not signals:
            return {"total": 0, "bullish": 0, "bearish": 0, "neutral": 0}

        bullish = [s for s in signals if s.direction == SignalDirection.BULLISH]
        bearish = [s for s in signals if s.direction == SignalDirection.BEARISH]
        neutral = [s for s in signals if s.direction == SignalDirection.NEUTRAL]

        weighted_bull = sum(s.confidence * s.signal_weight for s in bullish)
        weighted_bear = sum(s.confidence * s.signal_weight for s in bearish)

        return {
            "total": len(signals),
            "bullish": len(bullish),
            "bearish": len(bearish),
            "neutral": len(neutral),
            "weighted_bull_score": weighted_bull,
            "weighted_bear_score": weighted_bear,
            "net_score": weighted_bull - weighted_bear,
            "agents_reporting": [s.agent_name for s in signals],
        }

    def clear(self):
        self._signals.clear()


SignalBus = InterAgentSignalBus
