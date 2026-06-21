"""模型配置 CRUD 接口。"""
from uuid import UUID

from fastapi import APIRouter, HTTPException
from sqlalchemy import select, update

from app.core.dependencies import DbSession
from app.models.model_config import ModelConfig
from app.schemas.model_config import (
    ModelConfigCreate,
    ModelConfigResponse,
    ModelConfigUpdate,
)

router = APIRouter(prefix="/models", tags=["Models"])


def _mask_key(key: str) -> str:
    if len(key) <= 8:
        return "***"
    return key[:8] + "***"


def _to_response(mc: ModelConfig) -> dict:
    return {
        "id": mc.id,
        "name": mc.name,
        "provider": mc.provider,
        "base_url": mc.base_url,
        "api_key": mc.api_key,
        "api_key_masked": _mask_key(mc.api_key),
        "chat_model": mc.chat_model,
        "reasoner_model": mc.reasoner_model,
        "temperature": mc.temperature,
        "max_tokens": mc.max_tokens,
        "is_builtin": mc.is_builtin,
        "is_active": mc.is_active,
        "is_default": mc.is_default,
    }


@router.get("")
async def list_models(session: DbSession) -> list[dict]:
    """列出所有模型配置。"""
    result = await session.execute(
        select(ModelConfig).order_by(
            ModelConfig.is_default.desc(),
            ModelConfig.is_builtin.desc(),
            ModelConfig.created_at.desc(),
        )
    )
    return [_to_response(mc) for mc in result.scalars().all()]


@router.post("", status_code=201)
async def create_model(payload: ModelConfigCreate, session: DbSession) -> dict:
    """创建模型配置。"""
    # 如果设为默认，取消其他默认
    if payload.is_default:
        await session.execute(
            update(ModelConfig).values(is_default=False)
        )

    mc = ModelConfig(**payload.model_dump())
    session.add(mc)
    await session.commit()
    await session.refresh(mc)
    return _to_response(mc)


@router.put("/{model_id}")
async def update_model(
    model_id: UUID, payload: ModelConfigUpdate, session: DbSession
) -> dict:
    """更新模型配置。"""
    mc = await session.get(ModelConfig, model_id)
    if mc is None:
        raise HTTPException(status_code=404, detail="模型不存在")

    data = payload.model_dump(exclude_unset=True)

    # 设为默认时取消其他默认
    if data.get("is_default"):
        await session.execute(
            update(ModelConfig)
            .where(ModelConfig.id != model_id)
            .values(is_default=False)
        )

    for k, v in data.items():
        setattr(mc, k, v)
    await session.commit()
    await session.refresh(mc)
    return _to_response(mc)


@router.delete("/{model_id}")
async def delete_model(model_id: UUID, session: DbSession) -> dict:
    """删除模型配置。"""
    mc = await session.get(ModelConfig, model_id)
    if mc is None:
        raise HTTPException(status_code=404, detail="模型不存在")
    if mc.is_builtin:
        raise HTTPException(status_code=400, detail="内置模型不可删除")
    await session.delete(mc)
    await session.commit()
    return {"message": "已删除"}


@router.post("/init-builtin")
async def init_builtin_models(session: DbSession) -> dict:
    """初始化内置模型配置（基于环境变量）。"""
    from app.core.config import get_settings
    settings = get_settings()

    builtins = []

    # DeepSeek（从环境变量读）
    if settings.deepseek_api_key:
        builtins.append({
            "name": "DeepSeek",
            "provider": "deepseek",
            "base_url": settings.deepseek_base_url,
            "api_key": settings.deepseek_api_key,
            "chat_model": settings.deepseek_chat_model,
            "reasoner_model": settings.deepseek_reasoner_model,
            "temperature": 0.3,
            "max_tokens": 4096,
            "is_builtin": True,
            "is_default": True,
        })

    count = 0
    for data in builtins:
        existing = await session.execute(
            select(ModelConfig).where(
                ModelConfig.provider == data["provider"],
                ModelConfig.is_builtin == True,
            )
        )
        if existing.scalar_one_or_none() is None:
            session.add(ModelConfig(**data))
            count += 1

    await session.commit()
    return {"message": f"已初始化 {count} 个内置模型", "created": count}


@router.post("/{model_id}/test")
async def test_model(model_id: UUID, session: DbSession) -> dict:
    """测试模型连通性。"""
    from app.engine.agents.multi_model import MultiModelClient

    mc = await session.get(ModelConfig, model_id)
    if mc is None:
        raise HTTPException(status_code=404, detail="模型不存在")

    try:
        client = MultiModelClient({
            "base_url": mc.base_url,
            "api_key": mc.api_key,
            "chat_model": mc.chat_model,
            "reasoner_model": mc.reasoner_model or mc.chat_model,
            "temperature": 0.1,
            "max_tokens": 100,
            "provider": mc.provider,
            "name": mc.name,
        })
        reply = await client.complete_chat(
            messages=[
                {"role": "system", "content": "You are a test assistant. Reply 'OK' only."},
                {"role": "user", "content": "ping"},
            ],
            temperature=0.1,
        )
        return {"ok": True, "reply": reply[:200]}
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}
