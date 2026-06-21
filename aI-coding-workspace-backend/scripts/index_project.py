"""临时索引脚本：把后端项目代码写入 code_chunks 表，让 Code Chat 能检索到上下文。"""
import asyncio
from pathlib import Path
from uuid import UUID
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.core.database import AsyncSessionLocal
from app.engine.parser.code_slicer import slice_project_files
from app.engine.vector.embeddings import EmbeddingClient
from app.engine.vector.indexer import index_project_code


PROJECT_ID = UUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890")
PROJECT_ROOT_TO_INDEX = PROJECT_ROOT / "app"  # 只索引 app 目录，快速验证


async def main() -> None:
    # 先看切片数量，排查是否卡在 tree-sitter
    print("Slicing files...", flush=True)
    slices = await slice_project_files(PROJECT_ID, PROJECT_ROOT_TO_INDEX)
    print(f"Got {len(slices)} slices", flush=True)
    for s in slices[:3]:
        print(f"  - {s.file_path}:{s.start_line}-{s.end_line} ({s.symbol_type})", flush=True)

    print("Indexing (calling embedding API)...", flush=True)
    async with AsyncSessionLocal() as session:
        count = await index_project_code(
            session=session,
            project_id=PROJECT_ID,
            project_root=PROJECT_ROOT_TO_INDEX,
            embedding_client=EmbeddingClient(),
        )
    print(f"Indexed {count} code chunks for project {PROJECT_ID}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
