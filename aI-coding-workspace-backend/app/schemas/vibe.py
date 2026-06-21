from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class VibeStartRequest(BaseModel):
    project_id: UUID
    requirement: str = Field(min_length=1, max_length=8000)


class VibeStartResponse(BaseModel):
    thread_id: str
    status: str
    interrupt_payload: dict[str, Any] | None = None


class VibeConfirmRequest(BaseModel):
    thread_id: str
    approved: bool
    feedback: str = ""


class VibeConfirmResponse(BaseModel):
    thread_id: str
    status: str
    result: dict[str, Any] | None = None


class VibeApplyRequest(BaseModel):
    project_id: UUID
    diff: str = Field(min_length=1)


class VibeApplyResponse(BaseModel):
    applied_files: list[str]
    message: str

