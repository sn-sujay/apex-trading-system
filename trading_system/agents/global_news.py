"""
GlobalNews Agent — monitors US Fed minutes, ECB policy, geopolitical events,
and global macro news headlines for overnight risk-on/risk-off bias.
"""
from __future__ import annotations
from typing import Any, Dict, List
from ..core.base_agent import APEXBaseAgent
from ..core.signal_schema import AgentSignal, SignalDirection, SignalTimeframe, AssetClass


class GlobalNewsAgent(APEXBaseAgent):
    """
    Layer 4 Sentiment Agent: geopolitical risk scoring, Fed/ECB rhetoric parsing,
    war/conflict escalation detection, and global trade flow monitoring.
    """

    AGENT_NAME = "GlobalNewsAgent"
    AGENT_LAYER = 4
    SIGNAL_WEIGHT = 0.06

    RISK_OFF_KEYWORDS = [
        "war escalation", "nuclear", "sanctions", "trade war", "tariff",
        "bank failure", "credit crisis", "recession", "default sovereign",
        "fed hike surprise", "inflation surge", "stagflation",
        "pandemic", "lockdown", "supply shock",
    ]

    RISK_ON_KEYWORDS = [
        "ceasefire", "peace deal", "fed pause", "rate cut", "stimulus",
        "trade deal", "china reopening", "soft landing", "strong jobs",
        "earnings beat", "gdp beat", "manufacturing expansion",
    ]

    async def analyze(self, market_data: Dict[str, Any]) -> AgentSignal:
        global_headlines = market_data.get("global_headlines", [])
        geopolitical_risk = market_data.get("geopolitical_risk_index", 50)
        vix_level = market_data.get("vix_us", 20)

        # 1. Traditional scoring (Fast Path)
        headline_score = self._score_headlines(global_headlines)
        geo_score = self._score_geopolitical_risk(geopolitical_risk)
        vix_score = self._score_vix(vix_level)
        total_score = headline_score * 0.50 + geo_score * 0.30 + vix_score * 0.20

        # 2. Memory-Augmented Reasoning (Deep Path)
        mem_str = await self.get_long_term_memory(market_data)
        context = {
            "headlines": [h.get("title") for h in global_headlines[:5]],
            "geopolitical_risk": geopolitical_risk,
            "vix": vix_level,
            "fast_score": total_score
        }
        
        from ..core.llm import get_llm
        llm = get_llm(self.config)
        ai_analysis = await llm.analyze_with_memory(
            self.AGENT_NAME, 
            json.dumps(context), 
            mem_str
        )

        direction_val = ai_analysis.get("direction", "NEUTRAL")
        direction = (
            SignalDirection.BULLISH if direction_val == "BULLISH"
            else SignalDirection.BEARISH if direction_val == "BEARISH"
            else SignalDirection.NEUTRAL
        )
        
        confidence = ai_analysis.get("confidence", abs(total_score) / 40)

        return AgentSignal(
            agent_name=self.AGENT_NAME,
            direction=direction,
            confidence=min(confidence, 1.0),
            timeframe=SignalTimeframe.SHORT_TERM,
            asset_class=AssetClass.INDEX,
            reasoning=ai_analysis.get("reasoning", f"Fast Score: {total_score:.1f}"),
            metadata={
                "fast_score": total_score,
                "ai_factors": ai_analysis.get("key_factors", []),
                "memory_utilised": "No prior experience" not in mem_str
            },
        )

    def _score_headlines(self, headlines: List[Dict]) -> float:
        score = 0.0
        for item in headlines:
            text = (
                item.get(
                    "title",
                    "") +
                " " +
                item.get(
                    "summary",
                    "")).lower()
            for kw in self.RISK_OFF_KEYWORDS:
                if kw in text:
                    score -= 12
                    break
            for kw in self.RISK_ON_KEYWORDS:
                if kw in text:
                    score += 10
                    break
        return max(min(score, 40), -40)

    def _score_geopolitical_risk(self, risk_index: float) -> float:
        if risk_index > 200:
            return -30
        elif risk_index > 150:
            return -20
        elif risk_index > 100:
            return -10
        elif risk_index < 50:
            return 15
        return 0

    def _score_vix(self, vix: float) -> float:
        if vix > 35:
            return -30
        elif vix > 25:
            return -15
        elif vix > 20:
            return -5
        elif vix < 15:
            return 20
        elif vix < 18:
            return 10
        return 0
