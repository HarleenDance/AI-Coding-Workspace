from pathlib import Path
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.engine.parser.code_slicer import slice_project_files
from app.engine.vector.embeddings import EmbeddingClient
from app.models.project import CodeChunk, Project, ProjectFile


async def index_project_code(
    *,
    session: AsyncSession,
    project_id: UUID,
    project_root: Path,
    embedding_client: EmbeddingClient,
) -> int:
    """AST 语义切片 + Embedding + pgvector 入库。"""
    slices = await slice_project_files(project_id, project_root)
    if not slices:
        return 0

    embeddings = await embedding_client.embed_texts(
        [item.content for item in slices],
    )

    inserted = 0
    file_cache: dict[str, ProjectFile] = {}

    for code_slice, embedding in zip(slices, embeddings, strict=True):
        project_file = file_cache.get(code_slice.file_path)
        if project_file is None:
            result = await session.execute(
                select(ProjectFile).where(
                    ProjectFile.project_id == project_id,
                    ProjectFile.path == code_slice.file_path,
                ),
            )
            project_file = result.scalar_one_or_none()

        if project_file is None:
            project_file = ProjectFile(
                project_id=project_id,
                path=code_slice.file_path,
                language=code_slice.language,
                size_bytes=len(code_slice.content.encode("utf-8")),
                content_hash="pending",
                symbol_index={},
            )
            session.add(project_file)
            await session.flush()

        file_cache[code_slice.file_path] = project_file

        session.add(
            CodeChunk(
                project_id=project_id,
                file_id=project_file.id,
                file_path=code_slice.file_path,
                language=code_slice.language,
                symbol_name=code_slice.symbol_name,
                symbol_type=code_slice.symbol_type,
                start_line=code_slice.start_line,
                end_line=code_slice.end_line,
                content=code_slice.content,
                metadata_=code_slice.metadata,
                embedding=embedding,
            ),
        )
        inserted += 1

    project = await session.get(Project, project_id)
    if project is not None:
        project.is_indexed = True

    await session.commit()
    return inserted

