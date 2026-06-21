from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    project_id: UUID
    question: str = Field(min_length=1, max_length=8000)


class ChatResponse(BaseModel):
    answer: str
    artifacts: dict[str, Any] = {}


class ChatHistoryItem(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str


class ChatStreamRequest(BaseModel):
    project_id: UUID
    question: str = Field(min_length=1, max_length=8000)
    history: list[ChatHistoryItem] = Field(default_factory=list)
    agent_id: UUID | None = None
    model_id: UUID | None = None

