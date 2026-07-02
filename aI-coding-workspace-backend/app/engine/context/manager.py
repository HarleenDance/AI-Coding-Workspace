from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from app.engine.state import ContextFile


ChatMessage = dict[str, str]


@dataclass(frozen=True)
class ContextBudget:
    """Character budgets used as a lightweight proxy for input token budgets."""

    total_chars: int = 48_000
    system_chars: int = 6_000
    history_chars: int = 10_000
    code_chars: int = 26_000
    current_task_chars: int = 6_000
    per_file_chars: int = 5_000
    recent_history_turns: int = 8


@dataclass(frozen=True)
class ManagedPrompt:
    messages: list[ChatMessage]
    context_text: str
    history_summary: str
    diagnostics: dict[str, Any]


def _char_len(value: str | None) -> int:
    return len(value or "")


def _trim_middle(text: str, max_chars: int) -> tuple[str, bool]:
    if len(text) <= max_chars:
        return text, False
    if max_chars <= 200:
        return text[:max_chars], True

    head_chars = int(max_chars * 0.65)
    tail_chars = max_chars - head_chars - 80
    omitted = len(text) - head_chars - tail_chars
    marker = f"\n\n...[omitted {omitted} chars to fit context budget]...\n\n"
    return text[:head_chars] + marker + text[-tail_chars:], True


def _normalize_message(message: Any) -> ChatMessage:
    if isinstance(message, dict):
        role = str(message.get("role", "user"))
        content = str(message.get("content", ""))
    else:
        role = str(getattr(message, "role", "user"))
        content = str(getattr(message, "content", ""))

    if role not in {"user", "assistant", "system"}:
        role = "user"
    return {"role": role, "content": content}


def _dedupe_context_files(context_files: Iterable[ContextFile]) -> list[ContextFile]:
    seen: set[tuple[str, str]] = set()
    deduped: list[ContextFile] = []
    for item in context_files:
        key = (item.get("file_path", ""), item.get("content", ""))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def summarize_history(
    history: Iterable[Any],
    *,
    budget: ContextBudget | None = None,
) -> tuple[list[ChatMessage], str, dict[str, Any]]:
    """Keep recent turns verbatim and compress older turns extractively."""

    budget = budget or ContextBudget()
    messages = [_normalize_message(item) for item in history]
    if not messages:
        return [], "", {"history_items": 0, "history_chars": 0, "summarized_items": 0}

    recent = messages[-budget.recent_history_turns :]
    older = messages[: -budget.recent_history_turns]

    summary_lines: list[str] = []
    if older:
        for item in older[-12:]:
            content = " ".join(item["content"].split())
            content, _ = _trim_middle(content, 360)
            summary_lines.append(f"- {item['role']}: {content}")

    summary = "\n".join(summary_lines)
    if summary:
        summary = "Earlier conversation summary:\n" + summary

    available_for_recent = max(budget.history_chars - len(summary), 1_000)
    selected: list[ChatMessage] = []
    used = 0
    for item in reversed(recent):
        cost = _char_len(item["content"]) + 32
        if selected and used + cost > available_for_recent:
            break
        selected.append(item)
        used += cost
    selected.reverse()

    diagnostics = {
        "history_items": len(messages),
        "history_chars": sum(_char_len(item["content"]) for item in messages),
        "summarized_items": len(older),
        "kept_history_items": len(selected),
    }
    return selected, summary, diagnostics


def render_code_context(
    context_files: Iterable[ContextFile],
    *,
    budget: ContextBudget | None = None,
) -> tuple[str, dict[str, Any]]:
    """Render retrieved code with dedupe, per-file caps, and total budget caps."""

    budget = budget or ContextBudget()
    files = _dedupe_context_files(context_files)
    rendered: list[str] = []
    used = 0
    trimmed_files = 0
    skipped_files = 0
    included_paths: list[str] = []

    for item in files:
        path = item.get("file_path", "unknown")
        language = item.get("language", "")
        symbols = ", ".join(item.get("symbols", []))
        content = item.get("content", "")

        remaining = budget.code_chars - used
        if remaining <= 600:
            skipped_files += 1
            continue

        file_budget = min(budget.per_file_chars, remaining)
        trimmed_content, was_trimmed = _trim_middle(content, file_budget)
        if was_trimmed:
            trimmed_files += 1

        header = f"### {path}"
        if symbols:
            header += f"\nSymbols: {symbols}"
        block = f"{header}\n```{language}\n{trimmed_content}\n```"
        block_cost = len(block) + 2
        if rendered and used + block_cost > budget.code_chars:
            skipped_files += 1
            continue

        rendered.append(block)
        included_paths.append(path)
        used += block_cost

    diagnostics = {
        "retrieved_files": len(files),
        "included_files": len(included_paths),
        "included_paths": included_paths,
        "trimmed_files": trimmed_files,
        "skipped_files": skipped_files,
        "code_chars": used,
        "code_budget_chars": budget.code_chars,
    }
    return "\n\n".join(rendered), diagnostics


def build_chat_prompt(
    *,
    system_prompt: str,
    question: str,
    context_files: Iterable[ContextFile],
    history: Iterable[Any] = (),
    budget: ContextBudget | None = None,
) -> ManagedPrompt:
    """Build a budgeted prompt with differentiated buckets."""

    budget = budget or ContextBudget()
    system_prompt, system_trimmed = _trim_middle(system_prompt, budget.system_chars)
    question, question_trimmed = _trim_middle(question, budget.current_task_chars)
    kept_history, history_summary, history_diag = summarize_history(
        history,
        budget=budget,
    )
    context_text, context_diag = render_code_context(context_files, budget=budget)

    messages: list[ChatMessage] = [{"role": "system", "content": system_prompt}]
    if history_summary:
        messages.append({"role": "system", "content": history_summary})
    messages.extend(kept_history)
    messages.append(
        {
            "role": "user",
            "content": (
                f"Question:\n{question}\n\n"
                "Retrieved code context:\n"
                f"{context_text or '(no relevant code context found)'}"
            ),
        }
    )

    total_chars = sum(_char_len(item["content"]) for item in messages)
    diagnostics = {
        "total_chars": total_chars,
        "total_budget_chars": budget.total_chars,
        "system_trimmed": system_trimmed,
        "question_trimmed": question_trimmed,
        **history_diag,
        **context_diag,
    }
    return ManagedPrompt(
        messages=messages,
        context_text=context_text,
        history_summary=history_summary,
        diagnostics=diagnostics,
    )
