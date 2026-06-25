from typing import Literal

from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from app.core.config import get_settings
from app.engine.agents.coder import coder_agent
from app.engine.agents.planner import planner_agent
from app.engine.agents.qa import qa_agent
from app.engine.agents.reviewer import reviewer_agent
from app.engine.agents.router import router_agent
from app.engine.agents.tester import tester_agent
from app.engine.state import GraphState

settings = get_settings()


def human_approval_node(
    state: GraphState,
) -> Command[Literal["coder_agent", "__end__"]]:
    """Pause after planning so the user can approve the SDD plan."""
    resume_payload = interrupt(
        {
            "type": "sdd_plan_approval",
            "thread_id": state["thread_id"],
            "project_id": state["project_id"],
            "proposed_plan": state["proposed_plan"],
            "sdd_spec": state.get("sdd_spec", {}),
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


def route_after_review(state: GraphState) -> Literal["coder_agent", "__end__"]:
    harness = state.get("harness_result") or {}
    review = state.get("review_report") or {}
    retry_count = int(state.get("retry_count", 0))
    max_retries = int(state.get("max_retries", 2))
    passed = bool(harness.get("passed")) and bool(review.get("passed"))
    if passed or retry_count >= max_retries:
        return END
    return "coder_agent"


def retry_counter_node(state: GraphState) -> dict:
    return {
        "retry_count": int(state.get("retry_count", 0)) + 1,
        "current_node": "retry_counter_node",
    }


def build_workflow() -> StateGraph:
    builder = StateGraph(GraphState)

    builder.add_node("router_agent", router_agent)
    builder.add_node("planner_agent", planner_agent)
    builder.add_node("human_approval_node", human_approval_node)
    builder.add_node("coder_agent", coder_agent)
    builder.add_node("tester_agent", tester_agent)
    builder.add_node("reviewer_agent", reviewer_agent)
    builder.add_node("retry_counter_node", retry_counter_node)
    builder.add_node("qa_agent", qa_agent)

    builder.add_edge(START, "router_agent")
    builder.add_edge("planner_agent", "human_approval_node")
    builder.add_edge("coder_agent", "tester_agent")
    builder.add_edge("tester_agent", "reviewer_agent")
    builder.add_conditional_edges(
        "reviewer_agent",
        route_after_review,
        {"coder_agent": "retry_counter_node", END: END},
    )
    builder.add_edge("retry_counter_node", "coder_agent")
    builder.add_edge("qa_agent", END)

    return builder


async def compile_async_workflow():
    """Compile LangGraph with an async sqlite checkpointer for interrupt/resume."""
    from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

    settings.runtime_dir.mkdir(parents=True, exist_ok=True)
    checkpointer_cm = AsyncSqliteSaver.from_conn_string(
        str(settings.checkpoint_sqlite_path),
    )
    checkpointer = await checkpointer_cm.__aenter__()
    graph = build_workflow().compile(checkpointer=checkpointer)
    return graph, checkpointer_cm
