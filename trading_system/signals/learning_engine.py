
"""
LearningEngine — tracks decision outcomes, updates agent weight adjustments,
and provides performance attribution for continuous improvement.
"""
from __future__ import annotations
from collections import defaultdict
from datetime import datetime, timezone
from typing import Dict, List, Any
import json
from ..core.memory import ExperienceMemory


class LearningEngine:
    """
    Post-trade attribution engine. Tracks which agents were right/wrong,
    adjusts dynamic weights, and surfaces regime-conditioned accuracy.
    """

    WEIGHT_LEARNING_RATE = 0.02
    MIN_WEIGHT = 0.01
    MAX_WEIGHT = 0.25

    def __init__(self, redis_client=None):
        self.redis = redis_client
        self._agent_stats: Dict[str, Dict] = defaultdict(lambda: {
            "correct": 0, "incorrect": 0, "total": 0,
            "dynamic_weight_adj": 0.0,
        })
        self._decision_log: List[Dict] = []

    async def record_outcome(
        self, decision_id: str, actual_direction: str,
        agent_signals: Dict[str, Dict[str, Any]], predicted_direction: str,
        regime: str = "SIDEWAYS"
    ):
        """Called after a trade closes to record which agents were right."""
        was_correct = actual_direction == predicted_direction
        
        for agent_name, signal_data in agent_signals.items():
            stats = self._agent_stats[agent_name]
            stats["total"] += 1
            
            signal_dir = signal_data.get("direction")
            if signal_dir == actual_direction:
                stats["correct"] += 1
                stats["dynamic_weight_adj"] += self.WEIGHT_LEARNING_RATE
            else:
                stats["incorrect"] += 1
                stats["dynamic_weight_adj"] -= self.WEIGHT_LEARNING_RATE
            
            # Store in Memory Bank
            memory = ExperienceMemory(agent_name)
            await memory.store_experience(regime, {
                "factors": signal_data.get("key_factors", []),
                "reasoning": signal_data.get("reasoning", "No reasoning provided"),
                "outcome": "SUCCESS" if (signal_dir == actual_direction) else "FAILURE"
            })
            
            stats["dynamic_weight_adj"] = max(
                -0.10, min(0.10, stats["dynamic_weight_adj"])
            )
            
        self._decision_log.append({
            "decision_id": decision_id,
            "predicted": predicted_direction,
            "actual": actual_direction,
            "correct": was_correct,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def get_agent_accuracy(self) -> Dict[str, Dict]:
        result = {}
        for agent, stats in self._agent_stats.items():
            total = stats["total"]
            result[agent] = {
                "accuracy_pct": (stats["correct"] / total * 100) if total else 0,
                "total_signals": total,
                "weight_adjustment": stats["dynamic_weight_adj"],
            }
        return result

    def get_weight_adjustments(self) -> Dict[str, float]:
        return {
            agent: stats["dynamic_weight_adj"]
            for agent, stats in self._agent_stats.items()
        }

    def export_stats(self) -> str:
        return json.dumps({
            "agent_stats": dict(self._agent_stats),
            "recent_decisions": self._decision_log[-50:],
        }, indent=2)
