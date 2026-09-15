from datetime import datetime
from typing import Any, Optional
from uuid import UUID
from pydantic import BaseModel, Field


class ResearchRequest(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=16, examples=["AAPL"])


class AgentLogOut(BaseModel):
    agent_name: str
    status: str
    message: str
    payload: Optional[Any] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ResearchRunSummary(BaseModel):
    id: UUID
    symbol: str
    status: str
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ResearchRunDetail(ResearchRunSummary):
    final_report: Optional[str] = None
    error: Optional[str] = None
    logs: list[AgentLogOut] = []
