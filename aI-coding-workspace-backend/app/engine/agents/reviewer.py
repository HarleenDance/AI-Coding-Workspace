import json

from app.engine.agents.llm import DeepSeekClient
from app.engine.state import GraphState


def _fallback_review(state: GraphState) -> dict:
    artifacts = state.get("generated_artifacts", {})
    diff = str(artifacts.get("diff", ""))
    harness = state.get("harness_result") or {}
    findings: list[dict] = []

    if not diff.strip():
        findings.append(
            {
                "severity": "blocker",
                "dimension": "coding_standard",
                "message": "Coder did not produce a unified diff.",
            }
        )
    if not harness.get("passed", False):
        findings.append(
            {
                "severity": "blocker",
                "dimension": "harness_tests",
                "message": harness.get("summary", "Harness validation failed."),
            }
        )

    return {
        "passed": not findings,
        "summary": "本地审查通过。" if not findings else "存在阻断问题，需要重新生成。",
        "findings": findings,
    }


def _parse_review(raw: str, state: GraphState) -> dict:
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            return {
                "passed": bool(parsed.get("passed", False)),
                "summary": str(parsed.get("summary", "")),
                "findings": parsed.get("findings", []),
                "raw": raw,
            }
    except Exception:
        pass

    fallback = _fallback_review(state)
    fallback["raw"] = raw
    if raw.strip() and fallback["passed"]:
        fallback["summary"] = raw.strip()
    return fallback


async def reviewer_agent(state: GraphState) -> dict:
    artifacts = dict(state.get("generated_artifacts", {}))
    diff = str(artifacts.get("diff", ""))
    harness = state.get("harness_result") or {}

    messages = [
        {
            "role": "system",
            "content": (
                "你是代码审查 Agent。请从代码规范、性能、安全、测试结果四个维度审查。"
                "只输出 JSON，格式为："
                '{"passed": boolean, "summary": string, '
                '"findings": [{"severity":"blocker|major|minor",'
                '"dimension":"coding_standard|performance|security|harness_tests",'
                '"message": string}]}。'
                "有 blocker 或 Harness 未通过时 passed 必须为 false。"
            ),
        },
        {
            "role": "user",
            "content": (
                f"SDD 方案：\n{state['proposed_plan']}\n\n"
                f"生成 diff：\n{diff}\n\n"
                f"Harness 结果：\n{json.dumps(harness, ensure_ascii=False)}"
            ),
        },
    ]

    try:
        raw = await DeepSeekClient().complete_chat(messages=messages, temperature=0)
        report = _parse_review(raw, state)
    except Exception as exc:
        report = _fallback_review(state)
        report["raw"] = f"模型不可用，已使用本地审查规则：{exc}"

    artifacts["review"] = report
    return {
        "generated_artifacts": artifacts,
        "review_report": report,
        "review_feedback": report.get("summary", ""),
        "current_node": "reviewer_agent",
    }
