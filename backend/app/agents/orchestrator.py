"""Orchestrator — wires agents together, persists logs, and broadcasts events via a Queue.

This is *minimal* multi-agent: a deterministic DAG. News + Fundamentals + Technical run
concurrently, then Report compiles. Real-world LangGraph adds branching / replanning,
but this layout already shows the multi-agent pattern cleanly for a project.
"""
from __future__ import annotations
import asyncio
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from .base import EmitFn
from .news_agent import NewsAgent
from .fundamentals_agent import FundamentalsAgent
from .technical_agent import TechnicalAgent
from .report_agent import ReportAgent
from .. import models
from ..database import SessionLocal

# In-memory pubsub: run_id -> list[asyncio.Queue]
_subscribers: dict[str, list[asyncio.Queue]] = {}


def subscribe(run_id: str) -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue()
    _subscribers.setdefault(run_id, []).append(q)
    return q


def unsubscribe(run_id: str, q: asyncio.Queue) -> None:
    if run_id in _subscribers and q in _subscribers[run_id]:
        _subscribers[run_id].remove(q)
        if not _subscribers[run_id]:
            del _subscribers[run_id]


async def _broadcast(run_id: str, event: dict) -> None:
    for q in list(_subscribers.get(run_id, [])):
        await q.put(event)


def _make_emit(run_id: UUID, agent_name: str) -> EmitFn:
    async def emit(status: str, message: str, payload: dict | None) -> None:
        # Persist
        db: Session = SessionLocal()
        try:
            log = models.AgentLog(
                run_id=run_id, agent_name=agent_name, status=status,
                message=message, payload=payload,
            )
            db.add(log)
            db.commit()
        finally:
            db.close()
        # Broadcast
        await _broadcast(str(run_id), {
            "type": "agent_log",
            "agent": agent_name,
            "status": status,
            "message": message,
            "payload": payload,
            "ts": datetime.utcnow().isoformat(),
        })
    return emit


async def _run_agent(agent, context, run_id: UUID):
    emit = _make_emit(run_id, agent.name)
    return await agent.run(context, emit)


async def run_research(run_id: UUID, symbol: str) -> None:
    """Top-level orchestration coroutine. Designed to be launched as a background task."""
    # Mark running
    db = SessionLocal()
    try:
        run = db.get(models.ResearchRun, run_id)
        if not run:
            return
        run.status = "running"
        db.commit()
    finally:
        db.close()

    context: dict[str, Any] = {"symbol": symbol}

    try:
        # Stage 1: parallel data agents
        news_agent = NewsAgent()
        fund_agent = FundamentalsAgent()
        tech_agent = TechnicalAgent()

        results = await asyncio.gather(
            _run_agent(news_agent, context, run_id),
            _run_agent(fund_agent, context, run_id),
            _run_agent(tech_agent, context, run_id),
            return_exceptions=True,
        )
        for r in results:
            if isinstance(r, Exception):
                raise r
            context.update(r)

        # Stage 2: compile
        report_agent = ReportAgent()
        report_result = await _run_agent(report_agent, context, run_id)
        final_report = report_result.get("final_report", "")

        # Persist final
        db = SessionLocal()
        try:
            run = db.get(models.ResearchRun, run_id)
            run.status = "completed"
            run.completed_at = datetime.utcnow()
            run.final_report = final_report
            db.commit()
        finally:
            db.close()

        await _broadcast(str(run_id), {
            "type": "run_completed",
            "report": final_report,
            "ts": datetime.utcnow().isoformat(),
        })

    except Exception as e:  # noqa: BLE001
        db = SessionLocal()
        try:
            run = db.get(models.ResearchRun, run_id)
            run.status = "failed"
            run.completed_at = datetime.utcnow()
            run.error = str(e)
            db.commit()
        finally:
            db.close()
        await _broadcast(str(run_id), {
            "type": "run_failed",
            "error": str(e),
            "ts": datetime.utcnow().isoformat(),
        })
    finally:
        # Signal end-of-stream to subscribers
        await _broadcast(str(run_id), {"type": "stream_end"})
