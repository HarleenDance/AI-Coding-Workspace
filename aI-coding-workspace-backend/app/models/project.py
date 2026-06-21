from uuid import UUID

from pgvector.sqlalchemy import Vector
from sqlalchemy import BigInteger, Boolean, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Project(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "projects"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    owner_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))
    original_zip_name: Mapped[str] = mapped_column(String(512), nullable=False)
    root_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    is_indexed: Mapped[bool] = mapped_column(Boolean, default=False)

    files: Mapped[list["ProjectFile"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    chunks: Mapped[list["CodeChunk"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class ProjectFile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "project_files"

    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    path: Mapped[str] = mapped_column(String(1024), nullable=False)
    language: Mapped[str] = mapped_column(String(64), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, default=0)
    content_hash: Mapped[str] = mapped_column(String(128), index=True)
    symbol_index: Mapped[dict] = mapped_column(JSONB, default=dict)

    project: Mapped[Project] = relationship(back_populates="files")
    chunks: Mapped[list["CodeChunk"]] = relationship(
        back_populates="file",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class CodeChunk(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "code_chunks"

    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    file_id: Mapped[UUID] = mapped_column(
        ForeignKey("project_files.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    language: Mapped[str] = mapped_column(String(64), nullable=False)
    symbol_name: Mapped[str | None] = mapped_column(String(512))
    symbol_type: Mapped[str] = mapped_column(String(64), default="module")
    start_line: Mapped[int] = mapped_column(Integer, nullable=False)
    end_line: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)

    # 维度必须与 DashScope / Qwen Embedding 返回值一致。
    # 如需切换 1536/2048 维模型，请同步调整迁移脚本和 settings。
    embedding: Mapped[list[float]] = mapped_column(Vector(1024), nullable=False)

    project: Mapped[Project] = relationship(back_populates="chunks")
    file: Mapped[ProjectFile] = relationship(back_populates="chunks")

    __table_args__ = (
        Index(
            "ix_code_chunks_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )


class AgentTask(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "agent_tasks"

    thread_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    project_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    task_type: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(32), default="running")
    input_payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    output_payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    error_message: Mapped[str | None] = mapped_column(Text)


class AgentLog(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "agent_logs"

    task_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("agent_tasks.id", ondelete="CASCADE"),
    )
    thread_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    node_name: Mapped[str] = mapped_column(String(128), index=True)
    level: Mapped[str] = mapped_column(String(16), default="info")
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    message: Mapped[str] = mapped_column(Text)
    payload: Mapped[dict] = mapped_column(JSONB, default=dict)

