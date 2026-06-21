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
