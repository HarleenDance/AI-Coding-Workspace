from app.engine.agents.llm import DeepSeekClient
from app.engine.state import GraphState


async def planner_agent(state: GraphState) -> dict:
    llm = DeepSeekClient()
    context = "\n\n".join(
        f"### {item['file_path']}\n```{item['language']}\n{item['content']}\n```"
        for item in state.get("context_files", [])
    )

    plan = await llm.complete_chat(
        reasoner=True,
        temperature=0.1,
        messages=[
            {
                "role": "system",
                "content": (
                    "你是资深后端架构师 Agent。请基于代码上下文输出 Vibe Coding "
                    "实施方案，必须包含：目标、影响文件、实现步骤、风险、测试策略、"
                    "回滚策略，以及 Mermaid 架构图。不要直接写代码。"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"用户需求：{state['user_intent']}\n\n"
                    f"代码上下文：\n{context}"
                ),
            },
        ],
    )

    return {
        "proposed_plan": plan,
        "current_node": "planner_agent",
    }

