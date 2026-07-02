from app.engine.agents.llm import DeepSeekClient
from app.engine.context import render_code_context
from app.engine.state import GraphState


def _context_text(state: GraphState) -> str:
    context, _ = render_code_context(state.get("context_files", []))
    return context


def _fallback_plan(state: GraphState) -> str:
    files = ", ".join(item["file_path"] for item in state.get("context_files", [])[:6])
    return f"""# SDD 实施方案

## 需求目标
{state["user_intent"]}

## 规范拆解
- 输入输出契约：明确 API、函数签名、边界条件和错误返回。
- 工程规范：沿用当前项目目录结构、命名、异常处理和日志风格。
- 测试规范：优先补单元测试，再用 Harness 执行集成验证。

## 影响范围
{files or "当前未检索到强相关文件，Coder 需要先基于项目结构定位改动点。"}

## 实现步骤
1. 基于检索到的代码语义切片确认改动入口。
2. 按规范生成最小可审查 diff。
3. 将 diff 应用到临时工作区并运行 Harness 测试。
4. Reviewer 从代码规范、性能、安全三个维度审查结果。
5. 若测试或审查失败，携带反馈进入下一轮修复。

## 验收标准
- Harness 测试通过。
- Reviewer 不存在阻断级问题。
- 生成代码与现有工程风格一致。
"""


async def planner_agent(state: GraphState) -> dict:
    context = _context_text(state)
    sdd_spec = {
        "requirement": state["user_intent"],
        "quality_gates": ["coding_standard", "performance", "security", "harness_tests"],
        "max_retries": state.get("max_retries", 2),
    }

    messages = [
        {
            "role": "system",
            "content": (
                "你是资深架构师 Agent，负责把自然语言需求转成 SDD（规范驱动开发）方案。"
                "请输出 Markdown，必须包含：需求目标、接口/数据契约、影响文件、实现步骤、"
                "测试策略、风险与回滚策略。不要直接写代码。"
            ),
        },
        {
            "role": "user",
            "content": f"用户需求：{state['user_intent']}\n\n代码上下文：\n{context}",
        },
    ]

    try:
        plan = await DeepSeekClient().complete_chat(
            reasoner=True,
            temperature=0.1,
            messages=messages,
        )
    except Exception as exc:
        plan = _fallback_plan(state) + f"\n> 模型不可用，已使用本地 SDD 模板生成方案：{exc}\n"

    return {
        "sdd_spec": sdd_spec,
        "proposed_plan": plan,
        "current_node": "planner_agent",
    }
