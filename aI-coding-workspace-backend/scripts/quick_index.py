"""快速索引脚本：跳过 tree-sitter，直接用文件级切片验证 Code RAG 链路。"""
import asyncio
from pathlib import Path
from uuid import UUID, uuid4
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.core.database import AsyncSessionLocal
from app.engine.vector.embeddings import EmbeddingClient
from app.models.project import CodeChunk, ProjectFile


PROJECT_ID = UUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890")

# 手动挑选几个核心文件做文件级切片
TARGET_FILES = [
    PROJECT_ROOT / "app" / "main.py",
    PROJECT_ROOT / "app" / "core" / "config.py",
    PROJECT_ROOT / "app" / "engine" / "workflow.py",
    PROJECT_ROOT / "app" / "api" / "v1" / "endpoints" / "chat.py",
    PROJECT_ROOT / "app" / "api" / "v1" / "endpoints" / "vibe.py",
    PROJECT_ROOT / "app" / "engine" / "agents" / "qa.py",
    PROJECT_ROOT / "app" / "engine" / "agents" / "planner.py",
    PROJECT_ROOT / "app" / "engine" / "agents" / "coder.py",
    PROJECT_ROOT / "README.md",
]


async def main() -> None:
    print(f"Loading {len(TARGET_FILES)} files...", flush=True)
    contents = []
    for f in TARGET_FILES:
        rel = str(f.relative_to(PROJECT_ROOT)).replace("\\", "/")
        text = f.read_text(encoding="utf-8", errors="ignore")
        contents.append((rel, text))
        print(f"  - {rel} ({len(text)} chars)", flush=True)

    print(f"\nGenerating embeddings for {len(contents)} files...", flush=True)
    client = EmbeddingClient()
    embeddings = await client.embed_texts([c[1] for c in contents])
    print(f"Got {len(embeddings)} embeddings, dim={len(embeddings[0])}", flush=True)

    print("\nWriting to DB...", flush=True)
    async with AsyncSessionLocal() as session:
        for (rel, text), emb in zip(contents, embeddings, strict=True):
            pf = ProjectFile(
                id=uuid4(),
                project_id=PROJECT_ID,
                path=rel,
                language="python" if rel.endswith(".py") else "markdown",
                size_bytes=len(text.encode("utf-8")),
                content_hash="manual",
                symbol_index={},
            )
            session.add(pf)
            await session.flush()

            session.add(
                CodeChunk(
                    project_id=PROJECT_ID,
                    file_id=pf.id,
                    file_path=rel,
                    language="python" if rel.endswith(".py") else "markdown",
                    symbol_name=None,
                    symbol_type="module",
                    start_line=1,
                    end_line=text.count("\n") + 1,
                    content=text,
                    metadata_={"fallback": "manual_file_level"},
                    embedding=emb,
                ),
            )

        from app.models.project import Project
        project = await session.get(Project, PROJECT_ID)
        if project:
            project.is_indexed = True

        await session.commit()

    print(f"\nDone! Indexed {len(contents)} file-level chunks.", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
