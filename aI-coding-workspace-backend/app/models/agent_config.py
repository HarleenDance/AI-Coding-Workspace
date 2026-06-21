"""智能体配置模型。"""
from sqlalchemy import String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class AgentConfig(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """用户自定义智能体配置。"""

    __tablename__ = "agent_configs"

    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    avatar: Mapped[str] = mapped_column(String(32), default="🤖")
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    temperature: Mapped[float] = mapped_column(default=0.3)
    model_route: Mapped[str] = mapped_column(String(32), default="chat")
    tools: Mapped[list] = mapped_column(JSONB, default=list)
    is_builtin: Mapped[bool] = mapped_column(default=False)
    is_active: Mapped[bool] = mapped_column(default=True)
