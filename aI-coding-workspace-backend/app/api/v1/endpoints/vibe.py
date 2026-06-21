import json
import re
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from langgraph.types import Command
from sqlalchemy import select

from app.core.config import get_settings
from app.core.dependencies import DbSession
from app.engine.vector.embeddings import EmbeddingClient
from app.engine.vector.retriever import retrieve_code_context
from app.engine.workflow import compile_async_workflow
from app.models.project import AgentTask, Project
from app.schemas.vibe import (
    VibeApplyRequest,
    VibeApplyResponse,
    VibeConfirmRequest,
    VibeConfirmResponse,
    VibeStartRequest,
    VibeStartResponse,
)

router = APIRouter(prefix="/vibe", tags=["Vibe Coding"])


@router.post("/start", response_model=VibeStartResponse)
async def start_vibe(
    payload: VibeStartRequest,
    session: DbSession,
) -> VibeStartResponse:
    graph, checkpointer_cm = await compile_async_workflow()
    thread_id = str(uuid4())

    # 创建 AgentTask 记录
    task = AgentTask(
        thread_id=thread_id,
        project_id=payload.project_id,
        task_type="vibe_coding",
        status="running",
        input_payload={"requirement": payload.requirement},
    )
    session.add(task)
    await session.commit()

    try:
        context_files = await retrieve_code_context(
            session=session,
            project_id=payload.project_id,
            query=payload.requirement,
            embedding_client=EmbeddingClient(),
        )

        result = await graph.ainvoke(
            {
                "thread_id": thread_id,
                "project_id": str(payload.project_id),
                "user_intent": payload.requirement,
                "task_type": "vibe_coding",
                "context_files": context_files,
                "proposed_plan": "",
                "human_approved": False,
                "generated_artifacts": {},
                "review_feedback": "",
            },
            config={"configurable": {"thread_id": thread_id}},
        )
    finally:
        await checkpointer_cm.__aexit__(None, None, None)

    interrupts = result.get("__interrupt__")
    interrupt_payload = interrupts[0].value if interrupts else None

    # 更新 task 状态
    task.status = "waiting_approval" if interrupt_payload else "completed"
    task.output_payload = {"interrupt_payload": interrupt_payload or {}}
    await session.commit()

    return VibeStartResponse(
        thread_id=thread_id,
        status="waiting_approval" if interrupt_payload else "completed",
        interrupt_payload=interrupt_payload,
    )


@router.post("/confirm", response_model=VibeConfirmResponse)
async def confirm_vibe(payload: VibeConfirmRequest) -> VibeConfirmResponse:
    graph, checkpointer_cm = await compile_async_workflow()

    try:
        result = await graph.ainvoke(
            Command(
                resume={
                    "approved": payload.approved,
                    "feedback": payload.feedback,
                },
            ),
            config={"configurable": {"thread_id": payload.thread_id}},
        )
    finally:
        await checkpointer_cm.__aexit__(None, None, None)

    return VibeConfirmResponse(
        thread_id=payload.thread_id,
        status="completed",
        result=result,
    )


@router.get("/{thread_id}/events")
async def stream_vibe_events(thread_id: str):
    """SSE 事件流。

    前端可以监听 langgraph 事件，并将节点切换、LLM token、Mermaid 方案等
    转换为 IDE 右侧日志面板。
    """

    async def event_generator():
        graph, checkpointer_cm = await compile_async_workflow()
        try:
            async for event in graph.astream_events(
                None,
                config={"configurable": {"thread_id": thread_id}},
                version="v2",
            ):
                yield (
                    "event: langgraph\n"
                    f"data: {json.dumps(event, ensure_ascii=False, default=str)}\n\n"
                )
        finally:
            await checkpointer_cm.__aexit__(None, None, None)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


def _parse_unified_diff(diff_text: str) -> list[dict]:
    """解析 unified diff，提取每个文件的变更。

    返回 [{"file": "path/to/file", "hunks": [(start, content_lines)]}]
    """
    files = []
    current_file = None
    current_lines: list[str] = []

    for line in diff_text.splitlines():
        # 匹配 +++ b/path/to/file 或 +++ path/to/file
        if line.startswith("+++ "):
            if current_file:
                files.append({"file": current_file, "content": "\n".join(current_lines)})
            # 去掉 b/ 前缀
            path = line[4:].strip()
            if path.startswith("b/"):
                path = path[2:]
            current_file = path
            current_lines = []
        elif line.startswith("--- "):
            continue
        elif line.startswith("@@"):
            continue
        elif line.startswith(("+", "-", " ")) and current_file:
            # 只保留新增和不变的行（去掉删除的行）
            if not line.startswith("-"):
                current_lines.append(line[1:] if line.startswith("+") else line[1:])
        elif current_file and not line.startswith("\\"):
            # 普通行（diff 外的上下文）
            current_lines.append(line)

    if current_file:
        files.append({"file": current_file, "content": "\n".join(current_lines)})

    return files


@router.post("/apply", response_model=VibeApplyResponse)
async def apply_diff(payload: VibeApplyRequest, session: DbSession) -> VibeApplyResponse:
    """将 Vibe 生成的 diff 应用到磁盘文件。"""
    project = await session.get(Project, payload.project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="项目不存在")

    project_root = Path(project.root_path)
    if not project_root.is_dir():
        raise HTTPException(status_code=404, detail=f"项目目录不存在: {project_root}")

    parsed = _parse_unified_diff(payload.diff)
    if not parsed:
        raise HTTPException(status_code=400, detail="无法解析 diff 内容")

    applied = []
    for entry in parsed:
        file_path = project_root / entry["file"]
        # 安全检查：确保在项目根目录内
        try:
            file_path.resolve().relative_to(project_root.resolve())
        except ValueError:
            continue

        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(entry["content"], encoding="utf-8")
        applied.append(entry["file"])

    return VibeApplyResponse(
        applied_files=applied,
        message=f"已应用 diff 到 {len(applied)} 个文件",
    )


@router.get("/history/{project_id}")
async def get_vibe_history(project_id: UUID, session: DbSession) -> dict:
    """获取项目的 Vibe Coding 任务历史。"""
    from sqlalchemy import select as _select

    result = await session.execute(
        _select(AgentTask)
        .where(AgentTask.project_id == project_id)
        .order_by(AgentTask.created_at.desc())
        .limit(50)
    )
    tasks = result.scalars().all()

    return {
        "tasks": [
            {
                "id": str(t.id),
                "thread_id": t.thread_id,
                "task_type": t.task_type,
                "status": t.status,
                "requirement": t.input_payload.get("requirement", ""),
                "created_at": t.created_at.isoformat() if t.created_at else None,
                "updated_at": t.updated_at.isoformat() if t.updated_at else None,
            }
            for t in tasks
        ]
    }

