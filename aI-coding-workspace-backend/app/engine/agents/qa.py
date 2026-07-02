from app.engine.agents.llm import DeepSeekClient
from app.engine.context import render_code_context
from app.engine.state import GraphState


async def qa_agent(state: GraphState) -> dict:
    context, context_diag = render_code_context(state.get("context_files", []))
    messages = [
        {
            "role": "system",
            "content": (
                "你是代码库问答 Agent。请优先基于检索到的代码上下文回答，"
                "上下文不足时明确说明缺口，并给出下一步排查建议。"
            ),
        },
        {
            "role": "user",
            "content": f"问题：{state['user_intent']}\n\n上下文：\n{context}",
        },
    ]
    try:
        answer = await DeepSeekClient().complete_chat(messages=messages)
    except Exception as exc:
        answer = f"模型不可用，无法完成代码问答：{exc}"

    return {
        "generated_artifacts": {
            "answer": answer,
            "context_budget": context_diag,
        },
        "current_node": "qa_agent",
    }
