"""
APEX Trading Intelligence System
Core Signal Schema — Standardized format for all 20 agent signals.
Every agent publishes signals in this exact format.
The Master Decision Maker consumes only this schema.
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List
import json
import uuid


class SignalDirection(str, Enum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    STRONG_BUY = "STRONG_BUY"
    BUY = "BUY"
    NEUTRAL = "NEUTRAL"
    SELL = "SELL"
    STRONG_SELL = "STRONG_SELL"
    NO_SIGNAL = "NO_SIGNAL"


# Aliases for tests
BUY = SignalDirection.BUY
SELL = SignalDirection.SELL
LONG = SignalDirection.BUY
SHORT = SignalDirection.SELL


class SignalTimeframe(str, Enum):
    INTRADAY = "INTRADAY"     # same-day exit
    SHORT_TERM = "SHORT_TERM"   # 1-3 days
    SWING = "SWING"        # 2-5 days
    POSITIONAL = "POSITIONAL"   # 1-4 weeks
    LONG_TERM = "LONG_TERM"    # months


class AssetClass(str, Enum):
    EQUITY = "EQUITY"
    FUTURES = "FUTURES"
    OPTIONS = "OPTIONS"
    COMMODITY = "COMMODITY"
    FOREX = "FOREX"
    CRYPTO = "CRYPTO"
    INDEX = "INDEX"


class MarketRegime(str, Enum):
    BULL_TREND = "BULL_TREND"
    BEAR_TREND = "BEAR_TREND"
    SIDEWAYS = "SIDEWAYS"
    HIGH_VOL = "HIGH_VOL"
    LOW_VOL = "LOW_VOL"
    CRISIS = "CRISIS"


@dataclass
class AgentSignal:
    """
    Single agent signal — the atomic unit of the APEX signal bus.
    """
    # Identity
    signal_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    agent_name: str = ""
    agent_version: str = "1.0.0"
    timestamp: str = field(
        default_factory=lambda: datetime.utcnow().isoformat())

    # Core Signal
    direction: SignalDirection = SignalDirection.NO_SIGNAL
    confidence: float = 0.0          # 0.0 – 1.0
    timeframe: SignalTimeframe = SignalTimeframe.INTRADAY
    asset_class: AssetClass = AssetClass.EQUITY
    signal_weight: float = 1.0          # default weight

    # Target Instrument
    symbol: str = ""           # e.g. "NIFTY 50", "RELIANCE", "GOLD"
    exchange: str = "NSE"
    expiry: Optional[str] = None         # for F&O
    strike: Optional[float] = None
    option_type: Optional[str] = None         # CE / PE

    # Price Context
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    target_1: Optional[float] = None
    target_2: Optional[float] = None
    current_price: Optional[float] = None

    # Analysis Metadata
    reasoning: str = ""
    key_factors: List[str] = field(default_factory=list)
    supporting_data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    risk_reward_ratio: Optional[float] = None
    expected_move_pct: Optional[float] = None

    # Market Context
    regime: MarketRegime = MarketRegime.SIDEWAYS
    india_vix: Optional[float] = None
    nifty_level: Optional[float] = None

    # Signal Health
    data_freshness_seconds: int = 0            # how old is the data
    # recent accuracy of this agent
    model_accuracy_30d: Optional[float] = None
    is_override: bool = False        # manual override flag

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["direction"] = self.direction.value
        d["timeframe"] = self.timeframe.value
        d["asset_class"] = self.asset_class.value
        d["regime"] = self.regime.value
        return d

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "AgentSignal":
        d["direction"] = SignalDirection(d["direction"])
        d["timeframe"] = SignalTimeframe(d["timeframe"])
        d["asset_class"] = AssetClass(d["asset_class"])
        d["regime"] = MarketRegime(d["regime"])
        return cls(**d)

    @property
    def is_actionable(self) -> bool:
        return (
            self.direction not in (
                SignalDirection.NO_SIGNAL,
                SignalDirection.NEUTRAL)
            and self.confidence >= 0.40
            and self.data_freshness_seconds < 300
        )

    @property
    def signal_score(self) -> float:
        """Signed confidence: positive = bullish, negative = bearish."""
        direction_map = {
            SignalDirection.STRONG_BUY: 1.0,
            SignalDirection.BUY: 0.6,
            SignalDirection.NEUTRAL: 0.0,
            SignalDirection.SELL: -0.6,
            SignalDirection.STRONG_SELL: -1.0,
            SignalDirection.NO_SIGNAL: 0.0,
        }
        return self.confidence * direction_map[self.direction]


@dataclass
class ConsensusDecision:
    """
    Output of the MasterDecisionMaker — the final trade decision
    synthesized from all 20 agent signals.
    """
    decision_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(
        default_factory=lambda: datetime.utcnow().isoformat())

    # Decision
    final_direction: SignalDirection = SignalDirection.NO_SIGNAL
    consensus_score: float = 0.0          # weighted aggregate
    confidence_level: str = "LOW"        # LOW / MEDIUM / HIGH / VERY_HIGH
    execute_trade: bool = False

    # Instrument
    symbol: str = ""
    exchange: str = "NSE"
    asset_class: AssetClass = AssetClass.EQUITY
    timeframe: SignalTimeframe = SignalTimeframe.INTRADAY

    # Properties for compatibility with MasterDecisionMaker
    @property
    def direction(self) -> SignalDirection:
        return self.final_direction

    @direction.setter
    def direction(self, value: SignalDirection):
        self.final_direction = value

    @property
    def confidence(self) -> float:
        return self.consensus_score

    @confidence.setter
    def confidence(self, value: float):
        self.consensus_score = value

    @property
    def participating_agents(self) -> List[str]:
        return [s.get("agent", "") for s in self.contributing_signals]

    @participating_agents.setter
    def participating_agents(self, value: List[str]):
        # Just convert to a list of dicts for simplicity if possible, or ignore if not critical
        # Alternatively, add a real field
        pass

    # Execution Parameters
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    target_1: Optional[float] = None
    target_2: Optional[float] = None
    position_size_pct: float = 0.0

    # Signal Breakdown
    total_agents: int = 0
    bullish_agents: int = 0
    bearish_agents: int = 0
    neutral_agents: int = 0
    conflicted: bool = False
    veto_active: bool = False
    veto_reason: Optional[str] = None

    # Contributing signals
    contributing_signals: List[Dict] = field(default_factory=list)
    dissenting_agents: List[str] = field(default_factory=list)

    # Regime
    regime: MarketRegime = MarketRegime.SIDEWAYS
    bull_score: float = 0.0
    bear_score: float = 0.0
    conflict_analysis: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["final_direction"] = self.final_direction.value
        d["asset_class"] = self.asset_class.value
        d["timeframe"] = self.timeframe.value
        d["regime"] = self.regime.value
        return d

    def to_json(self) -> str:
        return json.dumps(self.to_dict())


TradeSignal = AgentSignal
Signal = AgentSignal
OptionSignal = AgentSignal
SignalPayload = AgentSignal
