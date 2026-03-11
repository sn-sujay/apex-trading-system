"""
APEX Agent 1: IndianMarketDataAgent
Ingests real-time NSE/BSE data via Zerodha Kite WebSocket.
Produces signals based on price action, volume, breadth, and market internals.
"""
from __future__ import annotations
import asyncio
import logging
from datetime import datetime, time as dtime, timezone
from zoneinfo import ZoneInfo
from typing import Dict, Any, Optional, List

import httpx
import pandas as pd
import numpy as np

from ..core.base_agent import APEXBaseAgent
from ..core.signal_schema import (
    AgentSignal, SignalDirection, SignalTimeframe,
    AssetClass, MarketRegime
)
from ..core.constants import (
    NSE_OPEN_TIME, NSE_CLOSE_TIME, NIFTY50_SYMBOL,
    BANKNIFTY_SYMBOL, TIMEFRAME_5M, TIMEFRAME_15M
)

logger = logging.getLogger(__name__)


class IndianMarketDataAgent(APEXBaseAgent):
    """
    Monitors NSE/BSE real-time price action.
    Signals based on:
    - Nifty50 / BankNifty trend and momentum
    - Market breadth (advance/decline ratio)
    - Volume analysis (unusual spikes, VWAP deviation)
    - Opening range breakout / pre-market gap
    """

    def __init__(self, config=None):
        super().__init__("IndianMarketDataAgent", "1.0.0", config)
        self._nifty_data: Optional[pd.DataFrame] = None
        self._banknifty_data: Optional[pd.DataFrame] = None
        self._market_breadth: Dict[str, float] = {}

    async def _fetch_data(self) -> Dict[str, Any]:
        """Fetch OHLCV data from Kite REST API."""
        try:
            from kiteconnect import KiteConnect
            kite = KiteConnect(api_key=self.config.kite_api_key)
            kite.set_access_token(self.config.kite_access_token)

            # Fetch 5-min OHLCV for Nifty and BankNifty
            today = datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d")
            nifty_hist = kite.historical_data(
                256265, today, today, TIMEFRAME_5M
            )
            banknifty_hist = kite.historical_data(
                260105, today, today, TIMEFRAME_5M
            )
            return {
                "nifty": pd.DataFrame(nifty_hist),
                "banknifty": pd.DataFrame(banknifty_hist),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            self.logger.warning(f"Kite fetch failed, using fallback: {e}")
            return await self._fetch_yahoo_fallback()

    async def _fetch_yahoo_fallback(self) -> Dict[str, Any]:
        """Yahoo Finance fallback for Nifty data."""
        import yfinance as yf
        nifty = yf.download("^NSEI", period="1d", interval="5m", progress=False)
        banknifty = yf.download("^NSEBANK", period="1d", interval="5m", progress=False)
        return {
            "nifty": nifty,
            "banknifty": banknifty,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def _compute_market_breadth(self, df: pd.DataFrame) -> Dict[str, float]:
        """Compute advance/decline and momentum breadth."""
        if df is None or df.empty:
            return {}
        close = df["close"] if "close" in df.columns else df["Close"]
        returns = close.pct_change()
        advancing = (returns > 0).sum()
        declining = (returns < 0).sum()
        total = len(returns.dropna())
        adr = advancing / declining if declining > 0 else float("inf")
        return {
            "advance_decline_ratio": float(adr),
            "advancing_pct": float(advancing / total) if total else 0.5,
            "momentum_5": float(close.pct_change(5).iloc[-1]) if len(close) > 5 else 0.0,
        }

    def _compute_vwap(self, df: pd.DataFrame) -> float:
        """Compute VWAP."""
        if df is None or df.empty or len(df) < 2:
            return 0.0
        try:
            close = df["close"] if "close" in df.columns else df["Close"]
            volume = df["volume"] if "volume" in df.columns else df["Volume"]
            high = df["high"] if "high" in df.columns else df["High"]
            low = df["low"] if "low" in df.columns else df["Low"]
            tp = (high + low + close) / 3
            vwap = (tp * volume).cumsum() / volume.cumsum()
            return float(vwap.iloc[-1])
        except Exception:
            return 0.0

    def _score_price_action(self, df: pd.DataFrame, symbol: str) -> tuple[SignalDirection, float, str]:
        """Score price action using EMA crossover + VWAP + RSI."""
        if df is None or df.empty or len(df) < 20:
            return SignalDirection.NO_SIGNAL, 0.0, "Insufficient data"

        close = df["close"] if "close" in df.columns else df["Close"]
        ema9 = close.ewm(span=9).mean()
        ema21 = close.ewm(span=21).mean()

        # RSI
        delta = close.diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = (-delta.clip(upper=0)).rolling(14).mean()
        rs = gain / loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))
        current_rsi = float(rsi.iloc[-1]) if not rsi.empty else 50

        # Current price vs VWAP
        vwap = self._compute_vwap(df)
        current_price = float(close.iloc[-1])
        vwap_deviation = (current_price - vwap) / vwap if vwap else 0.0

        # EMA crossover
        ema_bullish = float(ema9.iloc[-1]) > float(ema21.iloc[-1])
        ema_prev_bullish = float(ema9.iloc[-2]) > float(ema21.iloc[-2]) if len(ema9) > 1 else ema_bullish

        # Scoring
        score = 0.0
        factors = []

        if ema_bullish and not ema_prev_bullish:
            score += 0.35
            factors.append("EMA9 crossed above EMA21 (bullish)")
        elif not ema_bullish and ema_prev_bullish:
            score -= 0.35
            factors.append("EMA9 crossed below EMA21 (bearish)")
        elif ema_bullish:
            score += 0.15
            factors.append("EMA9 > EMA21 (uptrend)")
        else:
            score -= 0.15
            factors.append("EMA9 < EMA21 (downtrend)")

        if current_rsi > 60:
            score += 0.20
            factors.append(f"RSI={current_rsi:.1f} bullish")
        elif current_rsi < 40:
            score -= 0.20
            factors.append(f"RSI={current_rsi:.1f} bearish")
        elif current_rsi > 70:
            score -= 0.10
            factors.append(f"RSI={current_rsi:.1f} overbought")
        elif current_rsi < 30:
            score += 0.10
            factors.append(f"RSI={current_rsi:.1f} oversold")

        if vwap_deviation > 0.003:
            score += 0.15
            factors.append(f"Price above VWAP by {vwap_deviation*100:.2f}%")
        elif vwap_deviation < -0.003:
            score -= 0.15
            factors.append(f"Price below VWAP by {abs(vwap_deviation)*100:.2f}%")

        reasoning = f"{symbol} analysis: " + "; ".join(factors)
        if score >= 0.45:
            return SignalDirection.STRONG_BUY, min(score, 0.95), reasoning
        elif score >= 0.25:
            return SignalDirection.BUY, score, reasoning
        elif score <= -0.45:
            return SignalDirection.STRONG_SELL, min(abs(score), 0.95), reasoning
        elif score <= -0.25:
            return SignalDirection.SELL, abs(score), reasoning
        else:
            return SignalDirection.NEUTRAL, abs(score), reasoning

    async def analyze(self, market_data: Dict[str, Any]) -> AgentSignal:
        data = await self._fetch_data()
        nifty_df = data.get("nifty")
        banknifty_df = data.get("banknifty")

        nifty_dir, nifty_conf, nifty_reason = self._score_price_action(nifty_df, "NIFTY50")
        bank_dir, bank_conf, bank_reason = self._score_price_action(banknifty_df, "BANKNIFTY")
        breadth = self._compute_market_breadth(nifty_df)

        # Combine: if both agree, boost confidence
        if nifty_dir == bank_dir:
            final_conf = min((nifty_conf + bank_conf) / 2 + 0.1, 0.95)
            final_dir = nifty_dir
        else:
            # Disagreement: neutral
            final_dir = SignalDirection.NEUTRAL
            final_conf = 0.3

        current_price = None
        if nifty_df is not None and not nifty_df.empty:
            close_col = "close" if "close" in nifty_df.columns else "Close"
            current_price = float(nifty_df[close_col].iloc[-1])

        return self._make_signal(
            direction=final_dir,
            confidence=final_conf,
            symbol=NIFTY50_SYMBOL,
            reasoning=f"Nifty: {nifty_reason} | BankNifty: {bank_reason}",
            key_factors=[
                nifty_reason, bank_reason,
                f"ADR={breadth.get('advance_decline_ratio', 0):.2f}",
                f"Breadth={breadth.get('advancing_pct', 0.5)*100:.1f}%",
            ],
            current_price=current_price,
            timeframe=SignalTimeframe.INTRADAY,
            asset_class=AssetClass.INDEX,
            exchange="NSE",
            supporting_data=breadth,
        )
