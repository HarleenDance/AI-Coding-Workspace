from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.engine.state import ContextFile
from app.engine.vector.embeddings import EmbeddingClient
from app.models.project import CodeChunk


async def retrieve_code_context(
    *,
    session: AsyncSession,
    project_id: UUID,
    query: str,
    embedding_client: EmbeddingClient,
    limit: int = 8,
) -> list[ContextFile]:
    query_vector = (await embedding_client.embed_texts([query]))[0]

    statement = (
        select(CodeChunk)
        .where(CodeChunk.project_id == project_id)
        .order_by(CodeChunk.embedding.cosine_distance(query_vector))
        .limit(limit)
    )
    rows = (await session.execute(statement)).scalars().all()

    return [
        {
            "file_path": row.file_path,
            "language": row.language,
            "symbols": [row.symbol_name] if row.symbol_name else [],
            "content": row.content,
        }
        for row in rows
    ]

