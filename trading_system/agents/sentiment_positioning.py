"""
SentimentPositioning Agent — aggregates retail sentiment, options positioning,
futures OI, FII derivative stats, and put/call ratio for contrarian signals.
"""
from __future__ import annotations
from typing import Any, Dict
from ..core.base_agent import APEXBaseAgent
from ..core.signal_schema import AgentSignal, SignalDirection, SignalTimeframe, AssetClass


class SentimentPositioningAgent(APEXBaseAgent):
    """
    Layer 4 Sentiment Agent: contrarian signals from extreme retail positioning,
    OI buildup patterns, FII derivatives, and India VIX analysis.
    """

    AGENT_NAME = "SentimentPositioningAgent"
    AGENT_LAYER = 4
    SIGNAL_WEIGHT = 0.07

    async def analyze(self, market_data: Dict[str, Any]) -> AgentSignal:
        pcr_score = self._score_pcr(market_data)
        oi_score = self._score_oi_analysis(market_data)
        india_vix_score = self._score_india_vix(market_data)
        fii_deriv_score = self._score_fii_derivatives(market_data)
        retail_score = self._score_retail_sentiment(market_data)

        total = (
            pcr_score * 0.25
            + oi_score * 0.25
            + india_vix_score * 0.20
            + fii_deriv_score * 0.20
            + retail_score * 0.10
        )

        direction = (
            SignalDirection.BULLISH if total > 10
            else SignalDirection.BEARISH if total < -10
            else SignalDirection.NEUTRAL
        )

        return AgentSignal(
            agent_name=self.AGENT_NAME,
            direction=direction,
            confidence=min(abs(total) / 45, 1.0),
            timeframe=SignalTimeframe.SHORT_TERM,
            asset_class=AssetClass.INDEX,
            reasoning=(
                f"PCR: {pcr_score:.1f} | OI: {oi_score:.1f} | VIX: {india_vix_score:.1f} | "
                f"FII Deriv: {fii_deriv_score:.1f} | Retail: {retail_score:.1f}"
            ),
            metadata={
                "pcr_score": pcr_score, "oi_score": oi_score,
                "india_vix_score": india_vix_score, "fii_deriv_score": fii_deriv_score,
                "retail_score": retail_score, "total": total,
            },
        )

    def _score_pcr(self, data: Dict) -> float:
        pcr_oi = data.get("pcr_oi", 1.0)
        pcr_vol = data.get("pcr_volume", 1.0)
        score = 0.0
        if pcr_oi > 1.5:
            score += 25
        elif pcr_oi > 1.2:
            score += 12
        elif pcr_oi < 0.6:
            score -= 25
        elif pcr_oi < 0.8:
            score -= 12
        if pcr_vol > 1.4:
            score += 10
        elif pcr_vol < 0.7:
            score -= 10
        return score

    def _score_oi_analysis(self, data: Dict) -> float:
        nifty_ce_oi_change = data.get("nifty_ce_oi_change_cr", 0)
        nifty_pe_oi_change = data.get("nifty_pe_oi_change_cr", 0)
        max_pain = data.get("max_pain", 0)
        current_price = data.get("nifty_ltp", 0)
        score = 0.0
        if nifty_pe_oi_change > nifty_ce_oi_change:
            score += 15
        elif nifty_ce_oi_change > nifty_pe_oi_change:
            score -= 15
        if max_pain and current_price:
            diff_pct = (current_price - max_pain) / max_pain * 100
            if diff_pct > 1.5:
                score -= 10
            elif diff_pct < -1.5:
                score += 10
        return score

    def _score_india_vix(self, data: Dict) -> float:
        india_vix = data.get("india_vix", 15)
        vix_change_pct = data.get("india_vix_change_pct", 0)
        score = 0.0
        if india_vix < 12:
            score += 10
        elif india_vix > 25:
            score -= 20
        elif india_vix > 20:
            score -= 10
        if vix_change_pct > 10:
            score -= 15
        elif vix_change_pct < -10:
            score += 10
        return score

    def _score_fii_derivatives(self, data: Dict) -> float:
        fii_index_fut_net = data.get("fii_index_fut_net_cr", 0)
        data.get("fii_index_opt_net_cr", 0)
        score = 0.0
        if fii_index_fut_net > 2000:
            score += 20
        elif fii_index_fut_net < -2000:
            score -= 20
        else:
            score += fii_index_fut_net / 200
        return max(min(score, 25), -25)

    def _score_retail_sentiment(self, data: Dict) -> float:
        demat_growth = data.get("demat_account_growth_pct", 0)
        sip_flow = data.get("sip_monthly_flow_cr", 18000)
        score = 0.0
        if sip_flow > 20000:
            score += 10
        elif sip_flow < 15000:
            score -= 5
        if demat_growth > 20:
            score -= 5
        return score
