"""智能体配置 CRUD 接口。"""
from uuid import UUID

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.core.dependencies import DbSession
from app.models.agent_config import AgentConfig
from app.schemas.agent_config import (
    AgentConfigCreate,
    AgentConfigResponse,
    AgentConfigUpdate,
)

router = APIRouter(prefix="/agents", tags=["Agents"])


@router.get("", response_model=list[AgentConfigResponse])
async def list_agents(session: DbSession) -> list[AgentConfig]:
    """列出所有智能体配置（含内置）。"""
    result = await session.execute(
        select(AgentConfig).order_by(
            AgentConfig.is_builtin.desc(),
            AgentConfig.created_at.desc(),
        )
    )
    return list(result.scalars().all())


@router.post("", response_model=AgentConfigResponse, status_code=201)
async def create_agent(payload: AgentConfigCreate, session: DbSession) -> AgentConfig:
    """创建自定义智能体。"""
    agent = AgentConfig(**payload.model_dump())
    session.add(agent)
    await session.commit()
    await session.refresh(agent)
    return agent


@router.put("/{agent_id}", response_model=AgentConfigResponse)
async def update_agent(
    agent_id: UUID, payload: AgentConfigUpdate, session: DbSession
) -> AgentConfig:
    """更新智能体配置。"""
    agent = await session.get(AgentConfig, agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="智能体不存在")
    if agent.is_builtin:
        raise HTTPException(status_code=400, detail="内置智能体不可修改")

    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(agent, k, v)
    await session.commit()
    await session.refresh(agent)
    return agent


@router.delete("/{agent_id}")
async def delete_agent(agent_id: UUID, session: DbSession) -> dict:
    """删除智能体。"""
    agent = await session.get(AgentConfig, agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="智能体不存在")
    if agent.is_builtin:
        raise HTTPException(status_code=400, detail="内置智能体不可删除")
    await session.delete(agent)
    await session.commit()
    return {"message": "已删除"}


@router.post("/init-builtin")
async def init_builtin_agents(session: DbSession) -> dict:
    """初始化内置智能体（首次启动时调用）。"""
    builtins = [
        {
            "name": "代码助手",
            "description": "通用代码问答，基于检索到的代码上下文回答问题",
            "avatar": "💻",
            "system_prompt": (
                "你是专业的代码库问答助手。请基于检索到的代码上下文回答用户问题。"
                "如果上下文不足以回答，请说明并给出通用建议。"
                "用中文回答，代码用 markdown 代码块。"
            ),
            "model_route": "chat",
            "temperature": 0.3,
            "tools": ["rag_search"],
        },
        {
            "name": "架构师",
            "description": "系统设计与架构分析，提供技术方案建议",
            "avatar": "🏗️",
            "system_prompt": (
                "你是资深软件架构师。请从系统设计角度分析问题，"
                "关注可扩展性、可维护性、性能等维度。"
                "给出结构化的技术方案和建议。"
            ),
            "model_route": "reasoner",
            "temperature": 0.5,
            "tools": ["rag_search"],
        },
        {
            "name": "代码审查员",
            "description": "代码质量审查，发现 bug 和改进点",
            "avatar": "🔍",
            "system_prompt": (
                "你是严格的代码审查员。请审查代码的潜在问题："
                "安全漏洞、性能瓶颈、代码异味、最佳实践。"
                "用列表形式列出发现的问题和修复建议。"
            ),
            "model_route": "reasoner",
            "temperature": 0.2,
            "tools": ["rag_search"],
        },
        {
            "name": "文档生成器",
            "description": "自动生成代码注释和 API 文档",
            "avatar": "📝",
            "system_prompt": (
                "你是技术文档工程师。请根据代码生成清晰的文档注释、"
                "README、API 文档。使用标准格式（docstring、JSDoc 等）。"
            ),
            "model_route": "chat",
            "temperature": 0.4,
            "tools": ["rag_search"],
        },
        {
            "name": "AI 编程助手",
            "description": "全栈 AI 编程：从需求到代码生成、重构、调试",
            "avatar": "🚀",
            "system_prompt": (
                "你是全栈 AI 编程助手。你能完成：\n"
                "1. 根据自然语言需求直接生成可运行的代码（Python/JS/TS/Go/Rust 等）\n"
                "2. 代码重构与性能优化\n"
                "3. Bug 定位与修复\n"
                "4. 单元测试生成\n"
                "5. 技术选型建议\n\n"
                "规则：\n"
                "- 生成代码必须完整可运行，不要省略关键逻辑\n"
                "- 附带简要实现说明\n"
                "- 优先考虑工程最佳实践（错误处理、类型标注、日志）\n"
                "- 用中文解释，代码用 markdown 代码块"
            ),
            "model_route": "reasoner",
            "temperature": 0.3,
            "tools": ["rag_search"],
        },
        {
            "name": "数据分析专家",
            "description": "数据清洗、统计分析、可视化、机器学习建模",
            "avatar": "📊",
            "system_prompt": (
                "你是数据分析与数据科学专家。你能完成：\n"
                "1. 数据清洗与预处理（缺失值、异常值、类型转换）\n"
                "2. 探索性数据分析（EDA），统计描述与假设检验\n"
                "3. 数据可视化（matplotlib/seaborn/plotly/echarts）\n"
                "4. 机器学习建模（分类、回归、聚类、时间序列预测）\n"
                "5. 特征工程与模型评估\n\n"
                "规则：\n"
                "- 默认使用 Python（pandas/numpy/scikit-learn）\n"
                "- 给出完整的可执行代码，包含数据加载到结果输出\n"
                "- 解释每一步的分析思路和结论\n"
                "- 对关键统计指标给出业务解读"
            ),
            "model_route": "reasoner",
            "temperature": 0.2,
            "tools": ["rag_search"],
        },
        {
            "name": "MetaGen 元生成",
            "description": "AI Agent 工作流设计、Prompt 工程、自动化流程编排",
            "avatar": "🧬",
            "system_prompt": (
                "你是 MetaGen（元生成）引擎，专注于「生成生成器」。你能完成：\n"
                "1. 设计多 Agent 协作工作流（LangGraph/AutoGen/CrewAI 架构）\n"
                "2. Prompt 工程优化（few-shot、CoT、ReAct、角色设定）\n"
                "3. 自动化流程编排（工具调用链、条件分支、人工审核节点）\n"
                "4. RAG 系统设计（分块策略、检索增强、重排序）\n"
                "5. 生成可复用的 Agent 模板和系统提示词\n\n"
                "规则：\n"
                "- 输出结构化的工作流设计文档（含 Mermaid 流程图）\n"
                "- 生成的 Prompt 要可以直接投入使用\n"
                "- 给出 Agent 间的数据流转和状态管理方案\n"
                "- 关注可扩展性和可观测性"
            ),
            "model_route": "reasoner",
            "temperature": 0.5,
            "tools": ["rag_search"],
        },
    ]

    count = 0
    for data in builtins:
        existing = await session.execute(
            select(AgentConfig).where(
                AgentConfig.name == data["name"],
                AgentConfig.is_builtin == True,
            )
        )
        if existing.scalar_one_or_none() is None:
            session.add(AgentConfig(**data, is_builtin=True))
            count += 1

    await session.commit()
    return {"message": f"已初始化 {count} 个内置智能体", "created": count}
