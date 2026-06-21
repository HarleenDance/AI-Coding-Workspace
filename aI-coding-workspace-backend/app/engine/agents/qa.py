from app.engine.agents.llm import DeepSeekClient
from app.engine.state import GraphState


async def qa_agent(state: GraphState) -> dict:
    llm = DeepSeekClient()
    context = "\n\n".join(
        f"### {item['file_path']}\n```{item['language']}\n{item['content']}\n```"
        for item in state.get("context_files", [])
    )
    answer = await llm.complete_chat(
        messages=[
            {
                "role": "system",
                "content": "你是代码库问答 Agent，请只基于检索上下文回答。",
            },
            {
                "role": "user",
                "content": f"问题：{state['user_intent']}\n\n上下文：{context}",
            },
        ],
    )
    return {
        "generated_artifacts": {"answer": answer},
        "current_node": "qa_agent",
    }

