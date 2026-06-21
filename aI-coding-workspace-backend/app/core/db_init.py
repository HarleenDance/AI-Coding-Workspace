from sqlalchemy import text

from app.core.database import engine
from app.models import Base


async def create_pgvector_extension() -> None:
    """初始化 pgvector 扩展。

    pgvector 的 Vector 字段和 HNSW 索引都依赖数据库扩展。该操作必须在
    metadata.create_all() 之前执行，否则建表阶段可能因为 vector 类型不存在失败。
    """

    async with engine.begin() as connection:
        await connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))


async def create_database_schema() -> None:
    """创建数据库表结构。

    当前项目处于核心骨架阶段，使用 SQLAlchemy metadata.create_all() 快速建表。
    正式生产环境建议后续接入 Alembic 管理结构变更。
    """

    await create_pgvector_extension()
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)


async def check_database_connection() -> str:
    async with engine.connect() as connection:
        version = await connection.scalar(text("SELECT version()"))
    return str(version)

