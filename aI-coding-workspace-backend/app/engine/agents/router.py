import json
from typing import Literal

from langgraph.types import Command

from app.engine.agents.llm import DeepSeekClient
from app.engine.state import GraphState


async def router_agent(
    state: GraphState,
) -> Command[Literal["planner_agent", "qa_agent"]]:
    llm = DeepSeekClient()
    content = await llm.complete_chat(
        messages=[
            {
                "role": "system",
                "content": (
                    "你是 AI IDE 的意图路由器。只输出 JSON："
                    '{"task_type":"project_analysis|code_qa|vibe_coding|defect_scan"}'
                ),
            },
            {"role": "user", "content": state["user_intent"]},
        ],
        temperature=0,
    )

    try:
        task_type = json.loads(content)["task_type"]
    except Exception:
        task_type = "code_qa"

    # 只有 Vibe Coding 会进入方案生成和人工确认链路。
    goto = "planner_agent" if task_type == "vibe_coding" else "qa_agent"
    return Command(
        update={"task_type": task_type, "current_node": "router_agent"},
        goto=goto,
    )

