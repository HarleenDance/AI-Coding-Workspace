"""模型配置 schemas。"""
from uuid import UUID

from pydantic import BaseModel, Field


class ModelConfigBase(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    provider: str = Field(min_length=1, max_length=64)
    base_url: str = Field(min_length=1, max_length=512)
    api_key: str = Field(min_length=1)
    chat_model: str = Field(min_length=1, max_length=128)
    reasoner_model: str = ""
    temperature: float = Field(ge=0, le=2, default=0.3)
    max_tokens: int = Field(ge=256, le=32768, default=4096)


class ModelConfigCreate(ModelConfigBase):
    is_default: bool = False


class ModelConfigUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=128)
    base_url: str | None = None
    api_key: str | None = None
    chat_model: str | None = None
    reasoner_model: str | None = None
    temperature: float | None = Field(None, ge=0, le=2)
    max_tokens: int | None = Field(None, ge=256, le=32768)
    is_active: bool | None = None
    is_default: bool | None = None


class ModelConfigResponse(ModelConfigBase):
    id: UUID
    is_builtin: bool
    is_active: bool
    is_default: bool
    # 脱敏的 api_key（只返回前 8 位 + ***）
    api_key_masked: str = ""

    model_config = {"from_attributes": True}
