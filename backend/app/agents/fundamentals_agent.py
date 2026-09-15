"""Fundamentals Agent — pulls company financial structure via yfinance."""
from __future__ import annotations
import asyncio
from typing import Any
import yfinance as yf

from .base import BaseAgent, EmitFn


class FundamentalsAgent(BaseAgent):
    name = "Fundamentals Agent"

    async def execute(self, context: dict[str, Any], emit: EmitFn) -> dict[str, Any]:
        symbol = context["symbol"]
        await emit("progress", f"Pulling fundamentals for {symbol}", None)
        fundamentals = await asyncio.to_thread(self._fetch, symbol)
        if not fundamentals.get("longName"):
            raise ValueError(f"No fundamentals found for symbol '{symbol}'. Is the ticker valid?")
        await emit("progress", f"Loaded {fundamentals['longName']}", None)
        return {"fundamentals": fundamentals}

    def _fetch(self, symbol: str) -> dict[str, Any]:
        t = yf.Ticker(symbol)
        info = t.info or {}
        keys = [
            "longName", "sector", "industry", "country", "website",
            "marketCap", "trailingPE", "forwardPE", "priceToBook",
            "dividendYield", "beta", "fiftyTwoWeekHigh", "fiftyTwoWeekLow",
            "profitMargins", "operatingMargins", "returnOnEquity",
            "totalRevenue", "revenueGrowth", "earningsGrowth", "debtToEquity",
            "currency", "longBusinessSummary",
        ]
        return {k: info.get(k) for k in keys}

    def summarize(self, result: dict[str, Any]) -> str:
        f = result.get("fundamentals", {}) or {}
        return f"{f.get('longName')} · {f.get('sector')} · MC {f.get('marketCap')}"
