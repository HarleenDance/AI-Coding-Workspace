"""智能体配置 schemas。"""
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class AgentConfigBase(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    description: str = ""
    avatar: str = "🤖"
    system_prompt: str = Field(min_length=1)
    temperature: float = Field(ge=0, le=2, default=0.3)
    model_route: str = "chat"
    tools: list[str] = Field(default_factory=list)


class AgentConfigCreate(AgentConfigBase):
    pass


class AgentConfigUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=128)
    description: str | None = None
    avatar: str | None = None
    system_prompt: str | None = None
    temperature: float | None = Field(None, ge=0, le=2)
    model_route: str | None = None
    tools: list[str] | None = None
    is_active: bool | None = None


class AgentConfigResponse(AgentConfigBase):
    id: UUID
    is_builtin: bool
    is_active: bool

    model_config = {"from_attributes": True}
