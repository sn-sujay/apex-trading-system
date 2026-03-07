"""
ZeroDTE / Expiry Day Agent — specialized logic for Nifty/BankNifty/FinNifty/Sensex
weekly expiry dynamics: gamma squeeze, max pain gravity, 0DTE flows, and pin risk.
"""
from __future__ import annotations
from typing import Any, Dict
from ..core.base_agent import APEXBaseAgent
from ..core.signal_schema import AgentSignal, SignalDirection, SignalTimeframe, AssetClass


class ZeroDTEExpiryAgent(APEXBaseAgent):
    """
    Expiry-day specialist: detects gamma exposure imbalances, max pain attraction,
    pin risk zones, and 0DTE vega crush setups.
    """

    AGENT_NAME = "ZeroDTEExpiryAgent"
    AGENT_LAYER = 2
    SIGNAL_WEIGHT = 0.10

    EXPIRY_SCHEDULE = {
        "NIFTY": "Thursday",
        "BANKNIFTY": "Wednesday",
        "FINNIFTY": "Tuesday",
        "MIDCPNIFTY": "Monday",
        "SENSEX": "Friday",
    }

    async def analyze(self, market_data: Dict[str, Any]) -> AgentSignal:
        is_expiry = market_data.get("is_expiry_day", False)
        expiry_index = market_data.get("expiry_index", "NIFTY")

        if not is_expiry:
            return AgentSignal(
                agent_name=self.AGENT_NAME,
                direction=SignalDirection.NEUTRAL,
                confidence=0.0,
                timeframe=SignalTimeframe.INTRADAY,
                asset_class=AssetClass.INDEX,
                reasoning="Not an expiry day — agent inactive",
                metadata={"active": False},
            )

        gamma_score = self._score_gamma_exposure(market_data)
        max_pain_score = self._score_max_pain_gravity(market_data)
        oi_concentration_score = self._score_oi_concentration(market_data)
        time_score = self._score_time_of_day(market_data)

        total = (
            gamma_score * 0.35
            + max_pain_score * 0.30
            + oi_concentration_score * 0.25
            + time_score * 0.10
        )

        direction = (
            SignalDirection.BULLISH if total > 15
            else SignalDirection.BEARISH if total < -15
            else SignalDirection.NEUTRAL
        )

        return AgentSignal(
            agent_name=self.AGENT_NAME,
            direction=direction,
            confidence=min(abs(total) / 60, 1.0),
            timeframe=SignalTimeframe.INTRADAY,
            asset_class=AssetClass.INDEX,
            reasoning=(
                f"EXPIRY DAY ({expiry_index}) — "
                f"Gamma: {gamma_score:.1f} | MaxPain: {max_pain_score:.1f} | "
                f"OI Conc: {oi_concentration_score:.1f} | Time: {time_score:.1f}"
            ),
            metadata={
                "is_expiry": True,
                "expiry_index": expiry_index,
                "gamma_score": gamma_score,
                "max_pain_score": max_pain_score,
                "oi_concentration_score": oi_concentration_score,
                "total": total,
            },
        )

    def _score_gamma_exposure(self, data: Dict) -> float:
        net_gamma_exposure = data.get("net_gamma_exposure_cr", 0)
        current_price = data.get("ltp", 0)
        gamma_flip_level = data.get("gamma_flip_level", 0)
        score = 0.0
        if gamma_flip_level and current_price:
            if current_price > gamma_flip_level:
                score += 20
            else:
                score -= 20
        if net_gamma_exposure > 0:
            score += min(net_gamma_exposure / 500, 15)
        else:
            score += max(net_gamma_exposure / 500, -15)
        return score

    def _score_max_pain_gravity(self, data: Dict) -> float:
        max_pain = data.get("max_pain", 0)
        current_price = data.get("ltp", 0)
        time_to_close_mins = data.get("mins_to_expiry_close", 375)
        if not max_pain or not current_price:
            return 0.0
        diff_pct = (max_pain - current_price) / current_price * 100
        gravity_factor = max(0, 1 - time_to_close_mins / 375)
        if diff_pct > 0:
            return min(diff_pct * 10 * gravity_factor, 30)
        else:
            return max(diff_pct * 10 * gravity_factor, -30)

    def _score_oi_concentration(self, data: Dict) -> float:
        ce_wall = data.get("highest_ce_oi_strike", 0)
        pe_wall = data.get("highest_pe_oi_strike", 0)
        current_price = data.get("ltp", 0)
        if not current_price:
            return 0.0
        score = 0.0
        if ce_wall and current_price < ce_wall:
            ce_dist_pct = (ce_wall - current_price) / current_price * 100
            score -= min(ce_dist_pct * 5, 20)
        if pe_wall and current_price > pe_wall:
            pe_dist_pct = (current_price - pe_wall) / current_price * 100
            score += min(pe_dist_pct * 5, 20)
        return score

    def _score_time_of_day(self, data: Dict) -> float:
        hour = data.get("current_hour_ist", 12)
        minute = data.get("current_minute_ist", 0)
        total_mins = hour * 60 + minute
        if total_mins >= 15 * 60:
            return -10
        elif total_mins >= 14 * 60:
            return -5
        elif total_mins <= 9 * 60 + 30:
            return 5
        return 0
