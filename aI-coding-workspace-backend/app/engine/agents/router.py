import json
from typing import Literal

from langgraph.types import Command

from app.engine.agents.llm import DeepSeekClient
from app.engine.state import GraphState


def _heuristic_task_type(intent: str) -> str:
    lowered = intent.lower()
    coding_keywords = ("实现", "新增", "修改", "修复", "生成", "开发", "add", "fix", "implement")
    qa_keywords = ("解释", "为什么", "如何", "分析", "what", "why", "how")
    if any(word in lowered for word in coding_keywords):
        return "vibe_coding"
    if any(word in lowered for word in qa_keywords):
        return "code_qa"
    return "code_qa"


async def router_agent(
    state: GraphState,
) -> Command[Literal["planner_agent", "qa_agent"]]:
    if state.get("task_type") == "vibe_coding":
        return Command(
            update={"task_type": "vibe_coding", "current_node": "router_agent"},
            goto="planner_agent",
        )

    try:
        content = await DeepSeekClient().complete_chat(
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
        task_type = json.loads(content)["task_type"]
    except Exception:
        task_type = _heuristic_task_type(state["user_intent"])

    goto = "planner_agent" if task_type == "vibe_coding" else "qa_agent"
    return Command(
        update={"task_type": task_type, "current_node": "router_agent"},
        goto=goto,
    )
