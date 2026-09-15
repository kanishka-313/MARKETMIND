"""News Agent — pulls recent headlines for the symbol.

Uses NewsAPI if a key is set, otherwise falls back to yfinance's free news endpoint.
"""
from __future__ import annotations
import asyncio
from typing import Any
import httpx
import yfinance as yf

from .base import BaseAgent, EmitFn
from ..config import settings


class NewsAgent(BaseAgent):
    name = "News Agent"

    async def execute(self, context: dict[str, Any], emit: EmitFn) -> dict[str, Any]:
        symbol = context["symbol"]
        await emit("progress", f"Searching news for {symbol}", None)

        articles: list[dict] = []
        if settings.newsapi_key:
            articles = await self._fetch_newsapi(symbol)
        if not articles:
            await emit("progress", "Falling back to yfinance news", None)
            articles = await asyncio.to_thread(self._fetch_yfinance, symbol)

        await emit("progress", f"Collected {len(articles)} articles", None)
        return {"news": articles[:10]}

    async def _fetch_newsapi(self, symbol: str) -> list[dict]:
        url = "https://newsapi.org/v2/everything"
        params = {
            "q": symbol,
            "sortBy": "publishedAt",
            "language": "en",
            "pageSize": 10,
            "apiKey": settings.newsapi_key,
        }
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                r = await client.get(url, params=params)
                r.raise_for_status()
                data = r.json()
                return [
                    {
                        "title": a.get("title"),
                        "source": (a.get("source") or {}).get("name"),
                        "url": a.get("url"),
                        "published_at": a.get("publishedAt"),
                        "description": a.get("description"),
                    }
                    for a in data.get("articles", [])
                ]
        except Exception:
            return []

    def _fetch_yfinance(self, symbol: str) -> list[dict]:
        try:
            ticker = yf.Ticker(symbol)
            raw = ticker.news or []
        except Exception:
            return []
        out = []
        for n in raw:
            content = n.get("content") or n
            out.append({
                "title": content.get("title"),
                "source": (content.get("provider") or {}).get("displayName") if isinstance(content.get("provider"), dict) else content.get("publisher"),
                "url": (content.get("canonicalUrl") or {}).get("url") if isinstance(content.get("canonicalUrl"), dict) else content.get("link"),
                "published_at": content.get("pubDate") or content.get("providerPublishTime"),
                "description": content.get("summary") or content.get("description"),
            })
        return out

    def summarize(self, result: dict[str, Any]) -> str:
        return f"{len(result.get('news', []))} headlines collected"
