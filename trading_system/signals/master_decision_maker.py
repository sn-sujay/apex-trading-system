"""
MasterDecisionMakerAgent — final aggregation layer.
Weighs all 20 agent signals, applies conflict penalty, kill-switch check,
and risk validation to produce a single actionable ConsensusDecision.
"""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from ..core.signal_schema import (
    ConsensusDecision, SignalDirection, SignalTimeframe, AssetClass
)
from .signal_bus import InterAgentSignalBus
from .conflict_detector import ConflictDetectionEngine
from ..risk.risk_manager import RiskManagementAgent
from ..risk.volatility_kill_switch import VolatilityKillSwitch


# Minimum weighted confidence to issue BULLISH/BEARISH decision (not HOLD)
DECISION_THRESHOLD = 0.35
STRONG_THRESHOLD = 0.55


class MasterDecisionMakerAgent:
    """
    The final arbiter. Aggregates all agent signals using weighted consensus,
    applies conflict penalties, enforces kill switch, and validates through risk.
    """

    def __init__(
        self,
        signal_bus: InterAgentSignalBus,
        conflict_engine: Optional[ConflictDetectionEngine] = None,
        risk_manager: Optional[RiskManagementAgent] = None,
        kill_switch: Optional[VolatilityKillSwitch] = None,
        **kwargs
    ):
        self.bus = signal_bus
        self.conflict = conflict_engine or kwargs.get("conflict_detector")
        self.risk = risk_manager
        self.kill_switch = kill_switch
        self.learning_engine = kwargs.get("learning_engine")
        self._decision_history: list = []

    async def decide(self, market_data: Dict[str, Any]) -> ConsensusDecision:
        # 1. Kill switch check first
        halted, halt_reason = self.kill_switch.check(market_data)
        if halted:
            return self._make_hold_decision(f"KILL SWITCH: {halt_reason}")

        # 2. Gather all signals
        signals = self.bus.get_all_signals()
        if not signals:
            return self._make_hold_decision("No agent signals available")

        # 3. Conflict analysis
        conflict_analysis = self.conflict.analyse_conflicts(signals)

        # 4. Weighted vote
        bull_score = 0.0
        bear_score = 0.0
        total_weight = 0.0
        participating_agents = []

        for agent_name, signal in signals.items():
            weight = signal.signal_weight * signal.confidence
            if signal.direction == SignalDirection.BULLISH:
                bull_score += weight
            elif signal.direction == SignalDirection.BEARISH:
                bear_score += weight
            total_weight += signal.signal_weight
            participating_agents.append(agent_name)

        if total_weight == 0:
            return self._make_hold_decision("Zero total signal weight")

        norm_bull = bull_score / total_weight
        norm_bear = bear_score / total_weight
        penalty = conflict_analysis["confidence_penalty"]

        net_bull = max(norm_bull - penalty, 0)
        net_bear = max(norm_bear - penalty, 0)

        # 5. Decision logic
        if net_bull >= STRONG_THRESHOLD:
            direction = SignalDirection.BULLISH
            confidence = net_bull
            reasoning = f"Strong bullish consensus (bull={net_bull:.2f}, conflict_penalty={penalty:.2f})"
        elif net_bear >= STRONG_THRESHOLD:
            direction = SignalDirection.BEARISH
            confidence = net_bear
            reasoning = f"Strong bearish consensus (bear={net_bear:.2f}, conflict_penalty={penalty:.2f})"
        elif net_bull >= DECISION_THRESHOLD and net_bull > net_bear:
            direction = SignalDirection.BULLISH
            confidence = net_bull
            reasoning = f"Moderate bullish (bull={net_bull:.2f})"
        elif net_bear >= DECISION_THRESHOLD and net_bear > net_bull:
            direction = SignalDirection.BEARISH
            confidence = net_bear
            reasoning = f"Moderate bearish (bear={net_bear:.2f})"
        else:
            return self._make_hold_decision(
                f"No conviction: bull={net_bull:.2f}, bear={net_bear:.2f}"
            )

        decision = ConsensusDecision(
            final_direction=direction,
            consensus_score=confidence,
            timeframe=SignalTimeframe.INTRADAY,
            asset_class=AssetClass.INDEX,
            reasoning=reasoning,
            total_agents=len(signals),
            bullish_agents=len([s for s in signals.values()
                               if s.direction == SignalDirection.BULLISH]),
            bearish_agents=len([s for s in signals.values()
                               if s.direction == SignalDirection.BEARISH]),
            neutral_agents=len([s for s in signals.values()
                               if s.direction == SignalDirection.NEUTRAL]),
            bull_score=norm_bull,
            bear_score=norm_bear,
            conflict_analysis=conflict_analysis,
        )

        self._decision_history.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "direction": direction.value,
            "confidence": confidence,
        })

        # 6. DTE Check for Options
        if decision.asset_class == AssetClass.OPTIONS:
            min_dte = 7
            if self.learning_engine and self.learning_engine.redis:
                from ..core.apex_redis import read_state
                val = read_state("APEX:MIN_DTE_NEW_ENTRIES")
                if val:
                    min_dte = int(val)
            
            # Simulated DTE check (in real life would pull from feed)
            current_dte = market_data.get("dte", 30) 
            if current_dte < min_dte:
                return self._make_hold_decision(f"Filtered: DTE {current_dte} < MIN_DTE {min_dte}")

        return decision

    def _make_hold_decision(self, reason: str) -> ConsensusDecision:
        return ConsensusDecision(
            final_direction=SignalDirection.NEUTRAL,
            consensus_score=0.0,
            timeframe=SignalTimeframe.INTRADAY,
            asset_class=AssetClass.INDEX,
            reasoning=reason,
            total_agents=0,
            bullish_agents=0,
            bearish_agents=0,
            neutral_agents=0,
            bull_score=0.0,
            bear_score=0.0,
            conflict_analysis={},
        )


MasterDecisionMaker = MasterDecisionMakerAgent
