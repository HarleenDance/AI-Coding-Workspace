"""模型配置模型。"""
from sqlalchemy import Boolean, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ModelConfig(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """LLM 模型配置（OpenAI 兼容协议）。"""

    __tablename__ = "model_configs"

    name: Mapped[str] = mapped_column(String(128), nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)  # deepseek/qwen/moonshot/glm/openai
    base_url: Mapped[str] = mapped_column(String(512), nullable=False)
    api_key: Mapped[str] = mapped_column(Text, nullable=False)
    chat_model: Mapped[str] = mapped_column(String(128), nullable=False)
    reasoner_model: Mapped[str] = mapped_column(String(128), default="")
    temperature: Mapped[float] = mapped_column(Float, default=0.3)
    max_tokens: Mapped[int] = mapped_column(default=4096)
    is_builtin: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
