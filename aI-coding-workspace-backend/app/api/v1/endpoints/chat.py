import json
from uuid import uuid4

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.core.dependencies import DbSession
from app.engine.agents.multi_model import MultiModelClient, get_model_config
from app.engine.context import build_chat_prompt
from app.engine.vector.embeddings import EmbeddingClient
from app.engine.vector.retriever import retrieve_code_context
from app.engine.workflow import compile_async_workflow
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    ChatStreamRequest,
)

router = APIRouter(prefix="/chat", tags=["Code Chat"])


@router.post("", response_model=ChatResponse)
async def chat_with_codebase(
    payload: ChatRequest,
    session: DbSession,
) -> ChatResponse:
    graph, checkpointer_cm = await compile_async_workflow()
    thread_id = str(uuid4())

    try:
        context_files = await retrieve_code_context(
            session=session,
            project_id=payload.project_id,
            query=payload.question,
            embedding_client=EmbeddingClient(),
        )

        result = await graph.ainvoke(
            {
                "thread_id": thread_id,
                "project_id": str(payload.project_id),
                "user_intent": payload.question,
                "task_type": "code_qa",
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

    artifacts = result.get("generated_artifacts", {})
    return ChatResponse(
        answer=artifacts.get("answer", ""),
        artifacts=artifacts,
    )


@router.post("/stream")
async def chat_stream(
    payload: ChatStreamRequest,
    session: DbSession,
) -> StreamingResponse:
    """Stream code Q&A with budgeted history and retrieved code context."""

    async def event_generator():
        yield _sse({"type": "status", "message": "正在检索代码上下文..."})

        context_files = await retrieve_code_context(
            session=session,
            project_id=payload.project_id,
            query=payload.question,
            embedding_client=EmbeddingClient(),
        )

        system_prompt = (
            "你是代码库问答 Agent。请基于检索到的代码上下文回答用户问题。"
            "如果上下文不足以回答，请说明缺口并给出下一步排查建议。"
            "用中文回答，代码使用 markdown 代码块。"
        )
        temperature = 0.3

        if payload.agent_id:
            from app.models.agent_config import AgentConfig

            agent = await session.get(AgentConfig, payload.agent_id)
            if agent:
                system_prompt = agent.system_prompt
                temperature = agent.temperature

        managed_prompt = build_chat_prompt(
            system_prompt=system_prompt,
            question=payload.question,
            context_files=context_files,
            history=payload.history,
        )

        yield _sse(
            {
                "type": "context",
                "files": managed_prompt.diagnostics["included_paths"],
                "budget": managed_prompt.diagnostics,
            }
        )

        yield _sse({"type": "status", "message": "AI 思考中..."})

        model_config = await get_model_config(
            session,
            str(payload.model_id) if payload.model_id else None,
        )
        llm = MultiModelClient(model_config)
        full_answer = ""
        try:
            async for delta in llm.stream_chat(
                messages=managed_prompt.messages,
                temperature=temperature,
            ):
                full_answer += delta["content"]
                yield _sse({"type": "token", "content": delta["content"]})
        except Exception as exc:
            yield _sse({"type": "error", "message": str(exc)})
            return

        yield _sse(
            {
                "type": "done",
                "answer": full_answer,
                "budget": managed_prompt.diagnostics,
            }
        )

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


def _sse(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
