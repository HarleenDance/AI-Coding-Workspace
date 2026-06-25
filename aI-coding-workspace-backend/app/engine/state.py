from typing import Any, Literal, TypedDict

try:
    from typing import NotRequired
except ImportError:  # Python 3.10 compatibility for local development.
    from typing_extensions import NotRequired

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
    project_root: NotRequired[str]
    user_intent: str
    task_type: TaskType
    context_files: list[ContextFile]
    sdd_spec: NotRequired[dict[str, Any]]
    proposed_plan: str
    human_approved: bool
    generated_artifacts: dict[str, Any]
    review_feedback: str
    review_report: NotRequired[dict[str, Any]]
    harness_result: NotRequired[dict[str, Any]]
    retry_count: NotRequired[int]
    max_retries: NotRequired[int]

    # Observable fields used by SSE/debug panels.
    current_node: NotRequired[str]
    error_message: NotRequired[str]
    stream_events: NotRequired[list[dict[str, Any]]]
