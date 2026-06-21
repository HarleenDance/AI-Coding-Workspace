from typing import Literal

from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from app.core.config import get_settings
from app.engine.agents.coder import coder_agent
from app.engine.agents.planner import planner_agent
from app.engine.agents.qa import qa_agent
from app.engine.agents.router import router_agent
from app.engine.state import GraphState

settings = get_settings()


def human_approval_node(
    state: GraphState,
) -> Command[Literal["coder_agent", "__end__"]]:
    """Vibe Coding 人工确认节点。

    这里是 HIL 闭环的关键：
    1. planner_agent 先生成 proposed_plan。
    2. interrupt() 持久化当前状态并暂停图执行。
    3. 前端展示 proposed_plan，用户 Accept / Reject。
    4. /api/vibe/confirm 调用 Command(resume=...) 恢复到此节点。
    5. resume 的 payload 成为 interrupt() 返回值。
    """

    resume_payload = interrupt(
        {
            "type": "vibe_plan_approval",
            "thread_id": state["thread_id"],
            "project_id": state["project_id"],
            "proposed_plan": state["proposed_plan"],
        },
    )

    approved = bool(resume_payload.get("approved"))
    feedback = str(resume_payload.get("feedback", ""))

    if not approved:
        return Command(
            update={
                "human_approved": False,
                "review_feedback": feedback,
                "current_node": "human_approval_node",
            },
            goto=END,
        )

    return Command(
        update={
            "human_approved": True,
            "review_feedback": feedback,
            "current_node": "human_approval_node",
        },
        goto="coder_agent",
    )


def build_workflow() -> StateGraph:
    builder = StateGraph(GraphState)

    builder.add_node("router_agent", router_agent)
    builder.add_node("planner_agent", planner_agent)
    builder.add_node("human_approval_node", human_approval_node)
    builder.add_node("coder_agent", coder_agent)
    builder.add_node("qa_agent", qa_agent)

    builder.add_edge(START, "router_agent")
    builder.add_edge("planner_agent", "human_approval_node")
    builder.add_edge("coder_agent", END)
    builder.add_edge("qa_agent", END)

    return builder


async def compile_async_workflow():
    """编译 LangGraph。

    开发环境使用 AsyncSqliteSaver；生产多实例应替换为共享式 checkpointer。
    注意：checkpointer 必须启用，否则 interrupt/resume 无法可靠恢复。
    """

    from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

    settings.runtime_dir.mkdir(parents=True, exist_ok=True)
    checkpointer_cm = AsyncSqliteSaver.from_conn_string(
        str(settings.checkpoint_sqlite_path),
    )
    checkpointer = await checkpointer_cm.__aenter__()
    graph = build_workflow().compile(checkpointer=checkpointer)
    return graph, checkpointer_cm

