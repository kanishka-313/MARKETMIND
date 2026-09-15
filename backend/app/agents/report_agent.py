"""Report Agent — compiles a markdown investment brief via an LLM."""
from __future__ import annotations
import json
from typing import Any
from openai import AsyncOpenAI

from .base import BaseAgent, EmitFn
from ..config import settings


SYSTEM_PROMPT = """You are a senior equity research analyst at a buy-side firm.
Write a concise, fact-driven market brief in Markdown.

Rules:
- Use only facts from the supplied data. Do not invent numbers.
- If a data point is missing, say so plainly — do not guess.
- Be direct. Avoid filler like "in conclusion" or "it is important to note".
- Keep the tone of a professional analyst writing for a PM, not a retail blog.
- This is research, not financial advice. Add a one-line disclaimer at the end.

Required sections (in this order):
1. **Snapshot** — one-paragraph thesis.
2. **Company** — sector, what they do, scale.
3. **Fundamentals** — valuation, margins, growth.
4. **Technicals** — trend, momentum, key levels.
5. **News & Catalysts** — 3–5 bullets citing source names.
6. **Risks** — 2–3 bullets.
7. **Outlook** — 2–3 sentences.
"""


class ReportAgent(BaseAgent):
    name = "Report Compiler"

    async def execute(self, context: dict[str, Any], emit: EmitFn) -> dict[str, Any]:
        if not settings.llm_api_key:
            raise RuntimeError("LLM_API_KEY is not set. Add it to backend/.env")

        await emit("progress", "Composing brief with LLM", None)
        client = AsyncOpenAI(api_key=settings.llm_api_key, base_url=settings.llm_base_url)

        user_payload = {
            "symbol": context["symbol"],
            "fundamentals": context.get("fundamentals"),
            "technical": context.get("technical"),
            "news": context.get("news", []),
        }

        resp = await client.chat.completions.create(
            model=settings.llm_model,
            temperature=0.3,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(user_payload, default=str)},
            ],
        )
        report = resp.choices[0].message.content or ""
        await emit("progress", f"Brief generated ({len(report)} chars)", None)
        return {"final_report": report}

    def summarize(self, result: dict[str, Any]) -> str:
        return f"{len(result.get('final_report', ''))} chars"
