import asyncio
import json
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse

from .. import models, schemas
from ..database import get_db
from ..agents import orchestrator

router = APIRouter(prefix="/api", tags=["research"])


@router.post("/research", response_model=schemas.ResearchRunSummary, status_code=201)
def start_research(
    payload: schemas.ResearchRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    symbol = payload.symbol.strip().upper()
    run = models.ResearchRun(symbol=symbol, status="pending")
    db.add(run)
    db.commit()
    db.refresh(run)

    background_tasks.add_task(_launch, run.id, symbol)
    return run


def _launch(run_id: UUID, symbol: str):
    """Bridge sync BackgroundTasks -> asyncio task."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(orchestrator.run_research(run_id, symbol))
        else:
            asyncio.run(orchestrator.run_research(run_id, symbol))
    except RuntimeError:
        asyncio.run(orchestrator.run_research(run_id, symbol))


@router.get("/runs", response_model=list[schemas.ResearchRunSummary])
def list_runs(db: Session = Depends(get_db), limit: int = 30):
    return (
        db.query(models.ResearchRun)
        .order_by(models.ResearchRun.created_at.desc())
        .limit(limit)
        .all()
    )


@router.get("/runs/{run_id}", response_model=schemas.ResearchRunDetail)
def get_run(run_id: UUID, db: Session = Depends(get_db)):
    run = db.get(models.ResearchRun, run_id)
    if not run:
        raise HTTPException(404, "Run not found")
    return run


@router.get("/runs/{run_id}/stream")
async def stream_run(run_id: UUID, request: Request):
    """Server-Sent Events stream for live agent updates."""
    queue = orchestrator.subscribe(str(run_id))

    async def event_gen():
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    msg = await asyncio.wait_for(queue.get(), timeout=30.0)
                except asyncio.TimeoutError:
                    # heartbeat to keep connection alive
                    yield {"event": "ping", "data": "{}"}
                    continue
                if msg.get("type") == "stream_end":
                    yield {"event": "end", "data": "{}"}
                    break
                yield {"event": msg.get("type", "message"), "data": json.dumps(msg)}
        finally:
            orchestrator.unsubscribe(str(run_id), queue)

    return EventSourceResponse(event_gen())
