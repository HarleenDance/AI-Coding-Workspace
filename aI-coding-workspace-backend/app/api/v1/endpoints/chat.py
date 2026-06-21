import json
from uuid import uuid4

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.core.dependencies import DbSession
from app.engine.agents.llm import DeepSeekClient
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
    """流式代码问答 SSE 接口，支持多轮对话上下文。"""

    async def event_generator():
        # 1. 检索代码上下文
        yield _sse({"type": "status", "message": "正在检索代码上下文..."})

        context_files = await retrieve_code_context(
            session=session,
            project_id=payload.project_id,
            query=payload.question,
            embedding_client=EmbeddingClient(),
        )

        context_text = "\n\n".join(
            f"### {item['file_path']}\n```{item['language']}\n{item['content']}\n```"
            for item in context_files
        )

        yield _sse({
            "type": "context",
            "files": [item["file_path"] for item in context_files],
        })

        # 2. 加载智能体配置（如果有）
        system_prompt = (
            "你是代码库问答 Agent。请基于检索到的代码上下文回答用户问题。"
            "如果上下文不足以回答，请说明并给出通用建议。"
            "用中文回答，代码用 markdown 代码块。"
        )
        temperature = 0.3

        if payload.agent_id:
            from app.models.agent_config import AgentConfig
            agent = await session.get(AgentConfig, payload.agent_id)
            if agent:
                system_prompt = agent.system_prompt
                temperature = agent.temperature

        # 3. 构建多轮对话消息
        messages = [
            {
                "role": "system",
                "content": system_prompt,
            },
        ]

        # 加入历史对话（最近 10 轮）
        for item in payload.history[-10:]:
            messages.append({"role": item.role, "content": item.content})

        # 加入当前问题 + 检索上下文
        messages.append(
            {
                "role": "user",
                "content": f"问题：{payload.question}\n\n检索到的代码上下文：\n{context_text}",
            }
        )

        # 3. 流式输出 LLM 回复
        yield _sse({"type": "status", "message": "AI 思考中..."})

        # 加载模型配置（优先 model_id > 默认 > 环境变量 DeepSeek）
        from app.engine.agents.multi_model import MultiModelClient, get_model_config
        model_config = await get_model_config(session, str(payload.model_id) if payload.model_id else None)
        llm = MultiModelClient(model_config)
        full_answer = ""
        try:
            async for delta in llm.stream_chat(messages=messages, temperature=temperature):
                full_answer += delta["content"]
                yield _sse({"type": "token", "content": delta["content"]})
        except Exception as e:
            yield _sse({"type": "error", "message": str(e)})
            return

        yield _sse({"type": "done", "answer": full_answer})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


def _sse(data: dict) -> str:
    """格式化为 SSE 数据行。"""
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
