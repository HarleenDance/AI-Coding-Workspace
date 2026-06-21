from app.engine.agents.llm import DeepSeekClient
from app.engine.state import GraphState


async def coder_agent(state: GraphState) -> dict:
    llm = DeepSeekClient()
    context = "\n\n".join(
        f"### {item['file_path']}\n```{item['language']}\n{item['content']}\n```"
        for item in state.get("context_files", [])
    )

    diff = await llm.complete_chat(
        messages=[
            {
                "role": "system",
                "content": (
                    "你是代码生成 Agent。请严格基于已批准方案和代码上下文生成 "
                    "unified diff。只输出 diff，不要输出无关解释。"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"已批准方案：\n{state['proposed_plan']}\n\n"
                    f"人工反馈：\n{state.get('review_feedback', '')}\n\n"
                    f"代码上下文：\n{context}"
                ),
            },
        ],
    )

    return {
        "generated_artifacts": {"diff": diff},
        "current_node": "coder_agent",
    }

