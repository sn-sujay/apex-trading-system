"""
APEX Agent 6: OptionsDerivativesAgent
Analyzes options chain data: PCR, OI buildup, max pain, IV surface.
"""
from __future__ import annotations
from typing import Dict, Any
import pandas as pd

from ..core.base_agent import APEXBaseAgent
from ..core.signal_schema import AgentSignal, SignalDirection, SignalTimeframe, AssetClass


class OptionsDerivativesAgent(APEXBaseAgent):
    """
    Reads NSE options chain for Nifty/BankNifty.
    Signals from: PCR, max pain, IV skew, OI concentration.
    """

    def __init__(self, config=None):
        super().__init__("OptionsDerivativesAgent", "1.0.0", config)

    async def _fetch_data(self) -> Dict[str, Any]:
        """Fetch NSE options chain via NSE India API."""
        import httpx
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept-Language": "en-US,en;q=0.9",
        }
        data = {}
        async with httpx.AsyncClient(headers=headers, timeout=15.0) as client:
            # First get cookies
            try:
                await client.get("https://www.nseindia.com", timeout=10)
                resp = await client.get(
                    "https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY",
                    timeout=10,
                )
                if resp.status_code == 200:
                    data["nifty_chain"] = resp.json()
            except Exception as e:
                self.logger.warning(f"NSE options fetch failed: {e}")
        return data

    def _parse_chain(self, chain_data: dict) -> Dict[str, Any]:
        """Parse NSE options chain into structured analysis."""
        if not chain_data or "records" not in chain_data:
            return {}
        records = chain_data["records"]
        current_price = records.get("underlyingValue", 0)
        data_rows = records.get("data", [])
        total_ce_oi = 0
        total_pe_oi = 0
        iv_data = []

        for row in data_rows:
            strike = row.get("strikePrice", 0)
            ce = row.get("CE", {})
            pe = row.get("PE", {})
            ce_oi = ce.get("openInterest", 0)
            pe_oi = pe.get("openInterest", 0)
            total_ce_oi += ce_oi
            total_pe_oi += pe_oi
            if ce.get("impliedVolatility"):
                iv_data.append({"strike": strike, "type": "CE", "iv": ce["impliedVolatility"], "oi": ce_oi})
            if pe.get("impliedVolatility"):
                iv_data.append({"strike": strike, "type": "PE", "iv": pe["impliedVolatility"], "oi": pe_oi})

        pcr = total_pe_oi / total_ce_oi if total_ce_oi > 0 else 1.0
        iv_df = pd.DataFrame(iv_data)
        avg_call_iv = float(iv_df[iv_df["type"] == "CE"]["iv"].mean()) if not iv_df.empty else 15.0
        avg_put_iv = float(iv_df[iv_df["type"] == "PE"]["iv"].mean()) if not iv_df.empty else 15.0
        put_call_iv_skew = avg_put_iv - avg_call_iv

        return {
            "pcr": pcr,
            "total_ce_oi": total_ce_oi,
            "total_pe_oi": total_pe_oi,
            "current_price": current_price,
            "avg_call_iv": avg_call_iv,
            "avg_put_iv": avg_put_iv,
            "iv_skew": put_call_iv_skew,
        }

    async def analyze(self) -> AgentSignal:
        data = await self._fetch_data()
        chain = data.get("nifty_chain")
        if not chain:
            return self._no_signal("NSE options chain unavailable")

        parsed = self._parse_chain(chain)
        if not parsed:
            return self._no_signal("Failed to parse options chain")

        pcr = parsed.get("pcr", 1.0)
        iv_skew = parsed.get("iv_skew", 0.0)
        score = 0.0
        key_factors = [f"PCR={pcr:.2f}", f"IV Skew={iv_skew:.2f}"]

        # PCR interpretation
        if pcr > 1.5:
            score += 0.4
            key_factors.append("PCR > 1.5: extreme put buying, contrarian bullish")
        elif pcr > 1.2:
            score += 0.2
            key_factors.append("PCR > 1.2: mild put bias, mildly bullish")
        elif pcr < 0.7:
            score -= 0.4
            key_factors.append("PCR < 0.7: heavy call buying, contrarian bearish")
        elif pcr < 0.9:
            score -= 0.2
            key_factors.append("PCR < 0.9: call bias, mildly bearish")

        # IV skew: positive skew = market fears downside
        if iv_skew > 3:
            score -= 0.25
            key_factors.append(f"Positive IV skew {iv_skew:.1f}: downside fear")
        elif iv_skew < -2:
            score += 0.25
            key_factors.append(f"Negative IV skew {iv_skew:.1f}: upside demand")

        confidence = min(abs(score) * 1.5, 0.85)
        if score > 0.25:
            direction = SignalDirection.BUY
        elif score < -0.25:
            direction = SignalDirection.SELL
        else:
            direction = SignalDirection.NEUTRAL
            confidence = 0.3

        return self._make_signal(
            direction=direction,
            confidence=confidence,
            symbol="NIFTY 50",
            reasoning=f"Options chain analysis: PCR={pcr:.2f}, IV Skew={iv_skew:.2f}",
            key_factors=key_factors,
            timeframe=SignalTimeframe.INTRADAY,
            asset_class=AssetClass.OPTIONS,
            supporting_data=parsed,
        )
