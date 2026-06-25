import json
import subprocess
import tempfile
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from langgraph.types import Command
from sqlalchemy import select

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


def _json_safe(value):
    """Convert LangGraph/runtime objects to JSON-safe data for JSONB storage."""
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


@router.post("/start", response_model=VibeStartResponse)
async def start_vibe(
    payload: VibeStartRequest,
    session: DbSession,
) -> VibeStartResponse:
    project = await session.get(Project, payload.project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    graph, checkpointer_cm = await compile_async_workflow()
    thread_id = str(uuid4())

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
                "project_root": project.root_path,
                "user_intent": payload.requirement,
                "task_type": "vibe_coding",
                "context_files": context_files,
                "proposed_plan": "",
                "human_approved": False,
                "generated_artifacts": {},
                "review_feedback": "",
                "retry_count": 0,
                "max_retries": 2,
            },
            config={"configurable": {"thread_id": thread_id}},
        )
    finally:
        await checkpointer_cm.__aexit__(None, None, None)

    interrupts = result.get("__interrupt__")
    interrupt_payload = interrupts[0].value if interrupts else None
    status = "waiting_approval" if interrupt_payload else "completed"

    task.status = status
    task.output_payload = _json_safe(
        {"interrupt_payload": interrupt_payload or {}, "result": result}
    )
    await session.commit()

    return VibeStartResponse(
        thread_id=thread_id,
        status=status,
        interrupt_payload=interrupt_payload,
    )


@router.post("/confirm", response_model=VibeConfirmResponse)
async def confirm_vibe(
    payload: VibeConfirmRequest,
    session: DbSession,
) -> VibeConfirmResponse:
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

    task = (
        await session.execute(
            select(AgentTask).where(AgentTask.thread_id == payload.thread_id).limit(1)
        )
    ).scalar_one_or_none()
    status = "completed" if payload.approved else "rejected"
    if task:
        task.status = status
        task.output_payload = _json_safe({"result": result})
        await session.commit()

    return VibeConfirmResponse(
        thread_id=payload.thread_id,
        status=status,
        result=result,
    )


@router.get("/{thread_id}/events")
async def stream_vibe_events(thread_id: str):
    """Stream LangGraph events for the Vibe Coding panel."""

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


def _apply_diff_with_git(project_root: Path, diff_text: str) -> list[str]:
    with tempfile.NamedTemporaryFile("w", suffix=".diff", delete=False, encoding="utf-8") as fh:
        fh.write(diff_text)
        diff_path = Path(fh.name)
    try:
        check = subprocess.run(
            ["git", "apply", "--check", str(diff_path)],
            cwd=project_root,
            text=True,
            capture_output=True,
            timeout=30,
            check=False,
        )
        if check.returncode != 0:
            raise HTTPException(
                status_code=400,
                detail=f"Diff cannot be applied: {check.stderr or check.stdout}",
            )

        before = subprocess.run(
            ["git", "status", "--short"],
            cwd=project_root,
            text=True,
            capture_output=True,
            timeout=30,
            check=False,
        ).stdout
        apply = subprocess.run(
            ["git", "apply", str(diff_path)],
            cwd=project_root,
            text=True,
            capture_output=True,
            timeout=30,
            check=False,
        )
        if apply.returncode != 0:
            raise HTTPException(
                status_code=400,
                detail=f"Diff apply failed: {apply.stderr or apply.stdout}",
            )
        after = subprocess.run(
            ["git", "status", "--short"],
            cwd=project_root,
            text=True,
            capture_output=True,
            timeout=30,
            check=False,
        ).stdout
    finally:
        diff_path.unlink(missing_ok=True)

    changed = set()
    for line in (before + "\n" + after).splitlines():
        if len(line) > 3:
            changed.add(line[3:].strip())
    return sorted(changed)


@router.post("/apply", response_model=VibeApplyResponse)
async def apply_diff(payload: VibeApplyRequest, session: DbSession) -> VibeApplyResponse:
    """Apply a generated unified diff to project files."""
    project = await session.get(Project, payload.project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    project_root = Path(project.root_path).resolve()
    if not project_root.is_dir():
        raise HTTPException(status_code=404, detail=f"Project root does not exist: {project_root}")

    applied = _apply_diff_with_git(project_root, payload.diff)
    return VibeApplyResponse(
        applied_files=applied,
        message=f"Applied diff to {len(applied)} file(s).",
    )


@router.get("/history/{project_id}")
async def get_vibe_history(project_id: UUID, session: DbSession) -> dict:
    """Return recent Vibe Coding tasks for a project."""
    result = await session.execute(
        select(AgentTask)
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
