from app.engine.agents.llm import DeepSeekClient
from app.engine.state import GraphState


def _context_text(state: GraphState) -> str:
    return "\n\n".join(
        f"### {item['file_path']}\n```{item['language']}\n{item['content']}\n```"
        for item in state.get("context_files", [])
    )


async def coder_agent(state: GraphState) -> dict:
    context = _context_text(state)
    artifacts = dict(state.get("generated_artifacts", {}))
    retry_count = int(state.get("retry_count", 0))

    feedback_parts = [
        state.get("review_feedback", ""),
        (state.get("harness_result") or {}).get("summary", ""),
        (state.get("review_report") or {}).get("summary", ""),
    ]
    feedback = "\n".join(part for part in feedback_parts if part)

    messages = [
        {
            "role": "system",
            "content": (
                "你是代码生成 Agent。请严格基于已批准的 SDD 方案和代码上下文生成 unified diff。"
                "要求：只输出 diff；不要输出解释；尽量小步修改；必要时补测试。"
            ),
        },
        {
            "role": "user",
            "content": (
                f"已批准 SDD 方案：\n{state['proposed_plan']}\n\n"
                f"上一轮反馈：\n{feedback}\n\n"
                f"代码上下文：\n{context}"
            ),
        },
    ]

    try:
        diff = await DeepSeekClient().complete_chat(messages=messages, temperature=0.1)
    except Exception as exc:
        diff = ""
        artifacts["coder_error"] = f"模型不可用，未生成 diff：{exc}"

    artifacts["diff"] = diff
    return {
        "generated_artifacts": artifacts,
        "retry_count": retry_count,
        "current_node": "coder_agent",
    }
