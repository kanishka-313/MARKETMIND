"""Technical Agent — computes RSI, MACD, SMA, volatility from price history."""
from __future__ import annotations
import asyncio
from typing import Any
import pandas as pd
import yfinance as yf
from ta.momentum import RSIIndicator
from ta.trend import MACD, SMAIndicator
from ta.volatility import BollingerBands

from .base import BaseAgent, EmitFn


class TechnicalAgent(BaseAgent):
    name = "Technical Agent"

    async def execute(self, context: dict[str, Any], emit: EmitFn) -> dict[str, Any]:
        symbol = context["symbol"]
        await emit("progress", "Downloading 6 months of price history", None)
        df = await asyncio.to_thread(self._download, symbol)
        if df.empty:
            raise ValueError(f"No price data for '{symbol}'.")
        await emit("progress", f"Computing indicators on {len(df)} bars", None)
        indicators = self._compute(df)
        return {"technical": indicators}

    def _download(self, symbol: str) -> pd.DataFrame:
        return yf.download(symbol, period="6mo", interval="1d", progress=False, auto_adjust=True)

    def _compute(self, df: pd.DataFrame) -> dict[str, Any]:
        close = df["Close"].squeeze()
        rsi = RSIIndicator(close=close, window=14).rsi()
        macd = MACD(close=close)
        sma20 = SMAIndicator(close=close, window=20).sma_indicator()
        sma50 = SMAIndicator(close=close, window=50).sma_indicator()
        bb = BollingerBands(close=close, window=20)

        latest_close = float(close.iloc[-1])
        return {
            "latest_close": round(latest_close, 2),
            "rsi_14": round(float(rsi.iloc[-1]), 2),
            "macd": round(float(macd.macd().iloc[-1]), 4),
            "macd_signal": round(float(macd.macd_signal().iloc[-1]), 4),
            "sma_20": round(float(sma20.iloc[-1]), 2),
            "sma_50": round(float(sma50.iloc[-1]), 2),
            "bb_high": round(float(bb.bollinger_hband().iloc[-1]), 2),
            "bb_low": round(float(bb.bollinger_lband().iloc[-1]), 2),
            "above_sma20": bool(latest_close > float(sma20.iloc[-1])),
            "above_sma50": bool(latest_close > float(sma50.iloc[-1])),
            "pct_change_1m": round(float((close.iloc[-1] / close.iloc[-21] - 1) * 100), 2) if len(close) >= 21 else None,
            "pct_change_3m": round(float((close.iloc[-1] / close.iloc[-63] - 1) * 100), 2) if len(close) >= 63 else None,
            "volatility_annualized_pct": round(float(close.pct_change().std() * (252 ** 0.5) * 100), 2),
        }

    def summarize(self, result: dict[str, Any]) -> str:
        t = result.get("technical", {}) or {}
        return f"Close {t.get('latest_close')} · RSI {t.get('rsi_14')}"
