from pydantic import BaseModel
from typing import Any, Optional


class AnalyzeRequest(BaseModel):
    session_id: str
    user_id: str
    question: str


class ExecuteRequest(BaseModel):
    session_id: str
    approved: bool
    execution_plan: dict[str, Any]
    intent: Optional[dict[str, Any]] = None


class ContinueRequest(BaseModel):
    session_id: str
    intent: dict[str, Any]
    updates: dict[str, Any]