"""
AlgoStrategy Agent — generates structured trade signals using multi-factor scoring.
Combines technical patterns, regime context, and options flow into actionable signals.
"""
from __future__ import annotations
from typing import Any, Dict, List
from ..core.base_agent import APEXBaseAgent
from ..core.signal_schema import AgentSignal, SignalDirection, SignalTimeframe, AssetClass


class AlgoStrategyAgent(APEXBaseAgent):
    """
    Layer 2 Quant Agent: converts raw market data + regime context
    into structured, scored trade signals.
    """

    AGENT_NAME = "AlgoStrategyAgent"
    AGENT_LAYER = 2
    SIGNAL_WEIGHT = 0.20

    # Strategy catalogue
    STRATEGIES = [
        "momentum_breakout",
        "mean_reversion_vwap",
        "opening_range_breakout",
        "gap_fill",
        "options_driven_directional",
        "trend_following_ema",
    ]

    async def analyze(self, market_data: Dict[str, Any]) -> AgentSignal:
        """Primary analysis: score all strategies and return best signal."""
        scored = await self._score_strategies(market_data)
        best = max(scored, key=lambda x: abs(x["score"]))

        direction = (
            SignalDirection.BULLISH if best["score"] > 0
            else SignalDirection.BEARISH if best["score"] < 0
            else SignalDirection.NEUTRAL
        )

        return AgentSignal(
            agent_name=self.AGENT_NAME,
            direction=direction,
            confidence=min(abs(best["score"]) / 100, 1.0),
            timeframe=best.get("timeframe", SignalTimeframe.INTRADAY),
            asset_class=AssetClass.INDEX,
            reasoning=best.get("reasoning", ""),
            metadata={
                "strategy": best["name"],
                "all_scores": scored,
                "regime": market_data.get("regime", "unknown"),
            },
        )

    async def _score_strategies(self, data: Dict[str, Any]) -> List[Dict]:
        results = []
        for strategy in self.STRATEGIES:
            method = getattr(self, f"_score_{strategy}", None)
            if method:
                score_data = await method(data)
                results.append(score_data)
        return results

    async def _score_momentum_breakout(self, data: Dict) -> Dict:
        price = data.get("ltp", 0)
        high_52w = data.get("high_52w", price * 1.1)
        volume_surge = data.get("volume_ratio", 1.0)
        score = 0.0
        reasoning = []
        if price > high_52w * 0.98:
            score += 30
            reasoning.append("Near 52W high — breakout candidate")
        if volume_surge > 1.5:
            score += 20
            reasoning.append(f"Volume surge {volume_surge:.1f}x")
        vwap = data.get("vwap", price)
        if price > vwap * 1.002:
            score += 15
            reasoning.append("Trading above VWAP")
        return {
            "name": "momentum_breakout",
            "score": score,
            "timeframe": SignalTimeframe.INTRADAY,
            "reasoning": "; ".join(reasoning) or "No momentum signal",
        }

    async def _score_mean_reversion_vwap(self, data: Dict) -> Dict:
        price = data.get("ltp", 0)
        vwap = data.get("vwap", price)
        score = 0.0
        reasoning = []
        deviation = (price - vwap) / vwap if vwap else 0
        if deviation < -0.005:
            score = 25 + min(abs(deviation) * 1000, 30)
            reasoning.append(f"Price {deviation*100:.2f}% below VWAP — mean reversion long")
        elif deviation > 0.005:
            score = -(25 + min(abs(deviation) * 1000, 30))
            reasoning.append(f"Price {deviation*100:.2f}% above VWAP — mean reversion short")
        return {
            "name": "mean_reversion_vwap",
            "score": score,
            "timeframe": SignalTimeframe.SHORT_TERM,
            "reasoning": "; ".join(reasoning) or "At VWAP — no edge",
        }

    async def _score_opening_range_breakout(self, data: Dict) -> Dict:
        price = data.get("ltp", 0)
        orb_high = data.get("orb_high", 0)
        orb_low = data.get("orb_low", 0)
        score = 0.0
        reasoning = []
        if orb_high and price > orb_high * 1.001:
            score = 40
            reasoning.append(f"ORB breakout above {orb_high}")
        elif orb_low and price < orb_low * 0.999:
            score = -40
            reasoning.append(f"ORB breakdown below {orb_low}")
        return {
            "name": "opening_range_breakout",
            "score": score,
            "timeframe": SignalTimeframe.INTRADAY,
            "reasoning": "; ".join(reasoning) or "Inside opening range",
        }

    async def _score_gap_fill(self, data: Dict) -> Dict:
        price = data.get("ltp", 0)
        prev_close = data.get("prev_close", price)
        open_price = data.get("open_price", price)
        score = 0.0
        reasoning = []
        gap_pct = (open_price - prev_close) / prev_close if prev_close else 0
        if gap_pct > 0.005:
            score = -25
            reasoning.append(f"Gap up {gap_pct*100:.2f}% — potential gap fill short")
        elif gap_pct < -0.005:
            score = 25
            reasoning.append(f"Gap down {gap_pct*100:.2f}% — potential gap fill long")
        return {
            "name": "gap_fill",
            "score": score,
            "timeframe": SignalTimeframe.INTRADAY,
            "reasoning": "; ".join(reasoning) or "No significant gap",
        }

    async def _score_options_driven_directional(self, data: Dict) -> Dict:
        pcr = data.get("pcr", 1.0)
        iv_rank = data.get("iv_rank", 50)
        score = 0.0
        reasoning = []
        if pcr > 1.3:
            score = 20
            reasoning.append(f"PCR {pcr:.2f} — contrarian bullish")
        elif pcr < 0.7:
            score = -20
            reasoning.append(f"PCR {pcr:.2f} — contrarian bearish")
        if iv_rank < 20:
            score *= 0.5
            reasoning.append("Low IV rank — option premium cheap, signal weakened")
        return {
            "name": "options_driven_directional",
            "score": score,
            "timeframe": SignalTimeframe.SHORT_TERM,
            "reasoning": "; ".join(reasoning) or "Neutral options positioning",
        }

    async def _score_trend_following_ema(self, data: Dict) -> Dict:
        ema9 = data.get("ema9", 0)
        ema21 = data.get("ema21", 0)
        ema50 = data.get("ema50", 0)
        price = data.get("ltp", 0)
        score = 0.0
        reasoning = []
        if ema9 and ema21 and ema50:
            if ema9 > ema21 > ema50 and price > ema9:
                score = 35
                reasoning.append("Bullish EMA stack (9>21>50) with price above all")
            elif ema9 < ema21 < ema50 and price < ema9:
                score = -35
                reasoning.append("Bearish EMA stack (9<21<50) with price below all")
            elif ema9 > ema21:
                score = 15
                reasoning.append("Short-term bullish (EMA9 > EMA21)")
            elif ema9 < ema21:
                score = -15
                reasoning.append("Short-term bearish (EMA9 < EMA21)")
        return {
            "name": "trend_following_ema",
            "score": score,
            "timeframe": SignalTimeframe.SWING,
            "reasoning": "; ".join(reasoning) or "EMA data unavailable",
        }
