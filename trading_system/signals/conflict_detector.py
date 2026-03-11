"""
ConflictDetectionEngine — identifies when Layer 1/2 and Layer 3/4 agents
disagree, flags high-conflict states, and applies confidence penalties.
"""
from __future__ import annotations
from typing import Any, Dict, List, Tuple
from ..core.signal_schema import AgentSignal, SignalDirection


class ConflictDetectionEngine:
    """
    Detects structural conflicts between agent groups (e.g. technical bullish
    but macro bearish) and quantifies the conflict intensity.
    """

    LAYER_GROUPS = {
        "technical": ["TechnicalAnalysisAgent", "AlgoStrategyAgent", "MarketRegimeAgent"],
        "quant": ["OptionsDerivativesAgent", "ZeroDTEExpiryAgent", "SGXPreMarketAgent"],
        "data": ["IndianMarketDataAgent", "GlobalMarketDataAgent", "CommoditiesAgent"],
        "fundamental": ["FundamentalAnalysisAgent", "FIIDIIFlowAgent", "RBIMacroAgent", "GlobalMacroAgent"],
        "sentiment": ["IndianNewsEventsAgent", "GlobalNewsAgent", "SentimentPositioningAgent"],
    }

    def analyze_conflicts(
        self, signals: Dict[str, AgentSignal]
    ) -> Dict[str, Any]:
        """
        Returns conflict analysis including:
        - group_directions: consensus direction per group
        - inter_group_conflicts: list of conflicting group pairs
        - conflict_score: 0-1 (1 = max conflict)
        - confidence_penalty: reduction to apply to final confidence
        """
        group_dirs = self._get_group_directions(signals)
        conflicts = self._find_conflicts(group_dirs)
        conflict_score = len(conflicts) / max(len(group_dirs) - 1, 1)
        confidence_penalty = conflict_score * 0.30

        return {
            "group_directions": group_dirs,
            "inter_group_conflicts": conflicts,
            "conflict_score": conflict_score,
            "confidence_penalty": confidence_penalty,
            "high_conflict": conflict_score > 0.5,
        }

    def _get_group_directions(
            self, signals: Dict[str, AgentSignal]) -> Dict[str, str]:
        group_dirs = {}
        for group, agent_names in self.LAYER_GROUPS.items():
            group_signals = [
                signals[name] for name in agent_names if name in signals
            ]
            if not group_signals:
                continue
            bull = sum(1 for s in group_signals if s.direction ==
                       SignalDirection.BULLISH)
            bear = sum(1 for s in group_signals if s.direction ==
                       SignalDirection.BEARISH)
            if bull > bear:
                group_dirs[group] = "BULLISH"
            elif bear > bull:
                group_dirs[group] = "BEARISH"
            else:
                group_dirs[group] = "NEUTRAL"
        return group_dirs

    def _find_conflicts(
            self, group_dirs: Dict[str, str]) -> List[Tuple[str, str]]:
        groups = list(group_dirs.items())
        conflicts = []
        for i in range(len(groups)):
            for j in range(i + 1, len(groups)):
                g1, d1 = groups[i]
                g2, d2 = groups[j]
                if d1 != "NEUTRAL" and d2 != "NEUTRAL" and d1 != d2:
                    conflicts.append((g1, g2))
        return conflicts


ConflictDetector = ConflictDetectionEngine
