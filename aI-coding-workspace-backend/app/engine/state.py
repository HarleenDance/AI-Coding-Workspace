from typing import Any, Literal, NotRequired, TypedDict

TaskType = Literal[
    "project_analysis",
    "code_qa",
    "vibe_coding",
    "defect_scan",
    "unknown",
]


class ContextFile(TypedDict):
    file_path: str
    language: str
    symbols: list[str]
    content: str


class GraphState(TypedDict):
    thread_id: str
    project_id: str
    user_intent: str
    task_type: TaskType
    context_files: list[ContextFile]
    proposed_plan: str
    human_approved: bool
    generated_artifacts: dict[str, Any]
    review_feedback: str

    # 可观测性字段：用于 SSE / WebSocket 推送和调试。
    current_node: NotRequired[str]
    error_message: NotRequired[str]
    stream_events: NotRequired[list[dict[str, Any]]]

