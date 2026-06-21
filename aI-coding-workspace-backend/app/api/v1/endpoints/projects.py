"""项目文件树、文件内容、项目列表接口。"""
import zipfile
from io import BytesIO
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from app.core.config import get_settings
from app.core.dependencies import DbSession
from app.models.project import Project, ProjectFile

router = APIRouter(prefix="/projects", tags=["Projects"])

settings = get_settings()

# 忽略的目录
IGNORED_DIRS = {
    ".git", ".idea", ".vscode", ".venv", "venv", "env",
    "__pycache__", "node_modules", "dist", "build", ".next",
    ".pytest_cache", ".mypy_cache", ".ruff_cache", "egg-info",
}

# 忽略的文件后缀
IGNORED_SUFFIXES = {
    ".pyc", ".pyo", ".so", ".dll", ".dylib", ".exe",
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg", ".bmp",
    ".zip", ".tar", ".gz", ".rar", ".7z",
    ".mp3", ".mp4", ".wav", ".avi",
    ".pdf", ".doc", ".docx",
    ".lock", ".bin",
}

# 最大文件大小（读入 DB 的限制）
MAX_FILE_SIZE = 256 * 1024  # 256KB


def _detect_language(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    mapping = {
        ".py": "python", ".js": "javascript", ".ts": "typescript",
        ".tsx": "tsx", ".jsx": "jsx", ".java": "java", ".go": "go",
        ".rs": "rust", ".c": "c", ".cpp": "cpp", ".h": "cpp",
        ".html": "html", ".css": "css", ".scss": "scss",
        ".json": "json", ".yaml": "yaml", ".yml": "yaml", ".toml": "toml",
        ".md": "markdown", ".txt": "text", ".sh": "shell", ".bat": "bat",
        ".sql": "sql", ".vue": "vue",
    }
    return mapping.get(suffix, "text")


def _should_ignore(path: Path) -> bool:
    parts = path.parts
    if any(part in IGNORED_DIRS for part in parts):
        return True
    if path.suffix.lower() in IGNORED_SUFFIXES:
        return True
    return False


@router.get("")
async def list_projects(session: DbSession) -> dict:
    """列出所有项目。"""
    result = await session.execute(select(Project).order_by(Project.created_at.desc()))
    projects = result.scalars().all()
    return {
        "projects": [
            {
                "id": str(p.id),
                "name": p.name,
                "description": p.description,
                "is_indexed": p.is_indexed,
                "file_count": 0,  # 后面可以 join 统计
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in projects
        ]
    }


@router.post("/upload")
async def upload_project(
    session: DbSession,
    file: UploadFile = File(...),
) -> dict:
    """上传 ZIP 项目并解压、扫描文件结构、存入数据库。

    流程：
    1. 接收 zip 文件
    2. 解压到 runtime/projects/{uuid}/
    3. 扫描所有文件，存入 project_files 表
    4. 创建 project 记录
    """
    if not file.filename or not file.filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="只支持 .zip 文件")

    content = await file.read()
    if len(content) > 100 * 1024 * 1024:  # 100MB
        raise HTTPException(status_code=400, detail="ZIP 文件不能超过 100MB")

    project_id = uuid4()
    project_name = Path(file.filename).stem  # 去掉 .zip
    project_root = settings.runtime_dir / "projects" / str(project_id)
    project_root.mkdir(parents=True, exist_ok=True)

    # 解压
    try:
        with zipfile.ZipFile(BytesIO(content)) as zf:
            zf.extractall(project_root)
    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="无效的 ZIP 文件")

    # 找到真正的项目根目录（zip 可能有一层额外包裹）
    children = list(project_root.iterdir())
    if len(children) == 1 and children[0].is_dir():
        actual_root = children[0]
    else:
        actual_root = project_root

    # 扫描文件
    file_records = []
    for path in sorted(actual_root.rglob("*")):
        if not path.is_file():
            continue
        if _should_ignore(path.relative_to(actual_root)):
            continue
        if path.stat().st_size > MAX_FILE_SIZE:
            continue

        rel_path = str(path.relative_to(actual_root)).replace("\\", "/")
        try:
            text_content = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        pf = ProjectFile(
            id=uuid4(),
            project_id=project_id,
            path=rel_path,
            language=_detect_language(rel_path),
            size_bytes=path.stat().st_size,
            content_hash=str(hash(text_content) % (10**12)),
            symbol_index={},
        )
        # 用 symbol_index 临时存文件内容（避免新增表，快速实现）
        pf.symbol_index = {"content": text_content}
        file_records.append(pf)

    # 创建 project
    project = Project(
        id=project_id,
        name=project_name,
        original_zip_name=file.filename,
        root_path=str(actual_root),
        description=f"Uploaded project with {len(file_records)} files",
        is_indexed=False,
    )
    session.add(project)
    for pf in file_records:
        session.add(pf)

    await session.commit()

    return {
        "id": str(project_id),
        "name": project_name,
        "file_count": len(file_records),
        "message": f"项目上传成功，共 {len(file_records)} 个文件",
    }


@router.get("/{project_id}/files")
async def get_file_tree(project_id: UUID, session: DbSession) -> dict:
    """获取项目的文件树结构。"""
    result = await session.execute(
        select(ProjectFile)
        .where(ProjectFile.project_id == project_id)
        .order_by(ProjectFile.path)
    )
    files = result.scalars().all()

    # 构建树形结构
    tree: dict = {}
    for f in files:
        parts = f.path.split("/")
        node = tree
        for part in parts[:-1]:
            if part not in node:
                node[part] = {"_type": "dir", "_children": {}}
            node = node[part]["_children"]
        node[parts[-1]] = {
            "_type": "file",
            "_path": f.path,
            "_language": f.language,
            "_size": f.size_bytes,
        }

    return {"project_id": str(project_id), "tree": tree}


@router.get("/{project_id}/file")
async def get_file_content(
    project_id: UUID,
    path: str,
    session: DbSession,
) -> dict:
    """获取单个文件的内容（用 query param 传路径，避免 URL 后缀问题）。"""
    file_path = path
    result = await session.execute(
        select(ProjectFile)
        .where(
            ProjectFile.project_id == project_id,
            ProjectFile.path == file_path,
        )
    )
    pf = result.scalar_one_or_none()
    if pf is None:
        raise HTTPException(status_code=404, detail="文件不存在")

    # 优先从磁盘读取
    content = ""
    project = await session.get(Project, project_id)
    if project and project.root_path:
        disk_path = Path(project.root_path) / file_path
        if disk_path.is_file():
            try:
                content = disk_path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                content = ""

    # fallback 到数据库
    if not content and pf.symbol_index:
        content = pf.symbol_index.get("content", "")

    return {
        "path": pf.path,
        "language": pf.language,
        "size": pf.size_bytes,
        "content": content,
    }


@router.get("/{project_id}/files/{file_path:path}")
async def get_file_content_legacy(project_id: UUID, file_path: str, session: DbSession) -> dict:
    """获取单个文件的内容（旧路径方式，兼容用）。"""
    return await get_file_content(project_id, file_path, session)


class FileUpdateRequest(BaseModel):
    content: str


@router.put("/{project_id}/file")
async def update_file_content(
    project_id: UUID,
    path: str,
    payload: FileUpdateRequest,
    session: DbSession,
) -> dict:
    """保存文件内容到磁盘（用 query param 传路径）。"""
    file_path = path
    project = await session.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="项目不存在")

    result = await session.execute(
        select(ProjectFile).where(
            ProjectFile.project_id == project_id,
            ProjectFile.path == file_path,
        )
    )
    pf = result.scalar_one_or_none()
    if pf is None:
        raise HTTPException(status_code=404, detail="文件不存在")

    project_root = Path(project.root_path)
    disk_path = project_root / file_path
    if not disk_path.is_file():
        raise HTTPException(status_code=404, detail="磁盘文件不存在")

    disk_path.write_text(payload.content, encoding="utf-8")
    pf.size_bytes = len(payload.content.encode("utf-8"))
    await session.commit()

    return {"message": "文件已保存", "path": file_path}


@router.delete("/{project_id}")
async def delete_project(project_id: UUID, session: DbSession) -> dict:
    """删除项目及其所有文件。"""
    project = await session.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="项目不存在")

    await session.delete(project)
    await session.commit()

    return {"message": "项目已删除"}


@router.post("/{project_id}/index")
async def index_project(project_id: UUID, session: DbSession) -> dict:
    """对项目做文件级索引（生成 Embedding 并存入 code_chunks 表）。"""
    from uuid import uuid4 as _uuid4
    from app.engine.vector.embeddings import EmbeddingClient
    from app.models.project import CodeChunk

    project = await session.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="项目不存在")

    project_root = Path(project.root_path)
    if not project_root.is_dir():
        raise HTTPException(status_code=404, detail="项目目录不存在")

    # 清理旧索引
    result = await session.execute(
        select(CodeChunk).where(CodeChunk.project_id == project_id)
    )
    for chunk in result.scalars().all():
        await session.delete(chunk)
    await session.flush()

    # 收集文件
    result = await session.execute(
        select(ProjectFile).where(ProjectFile.project_id == project_id)
    )
    files = result.scalars().all()
    if not files:
        raise HTTPException(status_code=400, detail="项目没有文件记录")

    # 读取内容
    contents = []
    valid_files = []
    for pf in files:
        disk_path = project_root / pf.path
        if not disk_path.is_file():
            continue
        try:
            text = disk_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        contents.append(text)
        valid_files.append(pf)

    if not contents:
        raise HTTPException(status_code=400, detail="没有可索引的文件")

    # 生成 Embedding（分批，每批 16）
    client = EmbeddingClient()
    all_embeddings: list[list[float]] = []
    batch_size = 16
    for i in range(0, len(contents), batch_size):
        batch = contents[i : i + batch_size]
        embs = await client.embed_texts(batch)
        all_embeddings.extend(embs)

    # 写入 code_chunks
    for pf, text, emb in zip(valid_files, contents, all_embeddings, strict=True):
        session.add(
            CodeChunk(
                id=_uuid4(),
                project_id=project_id,
                file_id=pf.id,
                file_path=pf.path,
                language=pf.language,
                symbol_name=None,
                symbol_type="file",
                start_line=1,
                end_line=text.count("\n") + 1,
                content=text,
                metadata_={"index_method": "file_level"},
                embedding=emb,
            ),
        )

    project.is_indexed = True
    await session.commit()

    return {
        "message": f"索引完成，共 {len(valid_files)} 个文件",
        "indexed_count": len(valid_files),
    }


class SearchRequest(BaseModel):
    query: str
    mode: str = "keyword"  # keyword | semantic


@router.post("/{project_id}/search")
async def search_code(
    project_id: UUID,
    payload: SearchRequest,
    session: DbSession,
) -> dict:
    """代码搜索：关键词全文搜索 + 语义向量搜索双模式。"""
    project = await session.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="项目不存在")

    results = []

    if payload.mode == "semantic":
        from app.engine.vector.embeddings import EmbeddingClient
        from app.models.project import CodeChunk

        client = EmbeddingClient()
        embeddings = await client.embed_texts([payload.query])
        query_emb = embeddings[0]

        result = await session.execute(
            select(
                CodeChunk.file_path,
                CodeChunk.content,
                CodeChunk.symbol_name,
                CodeChunk.start_line,
                CodeChunk.end_line,
                (CodeChunk.embedding.cosine_distance(query_emb)).label("distance"),
            )
            .where(CodeChunk.project_id == project_id)
            .order_by("distance")
            .limit(20)
        )
        for row in result:
            results.append(
                {
                    "file_path": row.file_path,
                    "content": row.content[:500],
                    "symbol": row.symbol_name,
                    "start_line": row.start_line,
                    "end_line": row.end_line,
                    "score": 1 - row.distance,
                }
            )
    else:
        result = await session.execute(
            select(ProjectFile)
            .where(ProjectFile.project_id == project_id)
            .order_by(ProjectFile.path)
        )
        files = result.scalars().all()

        project_root = Path(project.root_path)
        keyword = payload.query.lower()
        for pf in files:
            disk_path = project_root / pf.path
            if not disk_path.is_file():
                continue
            try:
                text = disk_path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            lower_text = text.lower()
            if keyword in lower_text:
                lines = text.splitlines()
                matches = [
                    (i + 1, line)
                    for i, line in enumerate(lines)
                    if keyword in line.lower()
                ]
                snippet = ""
                if matches:
                    line_num = matches[0][0]
                    start = max(0, line_num - 2)
                    end = min(len(lines), line_num + 3)
                    snippet = "\n".join(
                        f"{'>' if j + 1 == line_num else ' '} {j+1}: {lines[j]}"
                        for j in range(start, end)
                    )
                results.append(
                    {
                        "file_path": pf.path,
                        "content": snippet,
                        "symbol": None,
                        "start_line": matches[0][0] if matches else 1,
                        "end_line": matches[0][0] if matches else 1,
                        "score": len(matches),
                        "match_count": len(matches),
                    }
                )
            if len(results) >= 20:
                break

    return {"query": payload.query, "mode": payload.mode, "results": results}
