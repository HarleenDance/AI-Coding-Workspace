"""多模型 LLM 客户端。

设计：以 OpenAI 兼容协议为统一接口，通过 ModelConfig 动态构建客户端。
- 默认用环境变量配置的 DeepSeek（无需数据库）
- 支持运行时从数据库加载自定义 provider 配置
"""
from collections.abc import AsyncGenerator
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.model_config import ModelConfig

settings = get_settings()

ChatMessagePayload = dict[str, str]


def _to_langchain_messages(messages: list[ChatMessagePayload]) -> list[BaseMessage]:
    """转换消息格式。"""
    converted: list[BaseMessage] = []
    for message in messages:
        role = message["role"]
        content = message["content"]
        if role == "system":
            converted.append(SystemMessage(content=content))
        elif role == "assistant":
            converted.append(AIMessage(content=content))
        else:
            converted.append(HumanMessage(content=content))
    return converted


def _stringify_content(content: Any) -> str:
    if isinstance(content, str):
        return content
    return str(content)


def build_chat_model(
    *,
    base_url: str,
    api_key: str,
    model_name: str,
    temperature: float = 0.3,
    streaming: bool = False,
    max_tokens: int = 4096,
) -> ChatOpenAI:
    """构建 OpenAI 兼容的 ChatOpenAI 实例。"""
    return ChatOpenAI(
        model=model_name,
        base_url=base_url,
        api_key=api_key,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=120,
        streaming=streaming,
        stream_usage=False,
    )


async def get_model_config(
    session: AsyncSession | None,
    model_id: str | None = None,
) -> dict[str, Any]:
    """获取模型配置。

    优先级：model_id 指定 > 默认模型 > 环境变量 DeepSeek。
    """
    if session and model_id:
        mc = await session.get(ModelConfig, model_id)
        if mc and mc.is_active:
            return {
                "base_url": mc.base_url,
                "api_key": mc.api_key,
                "chat_model": mc.chat_model,
                "reasoner_model": mc.reasoner_model or mc.chat_model,
                "temperature": mc.temperature,
                "max_tokens": mc.max_tokens,
                "provider": mc.provider,
                "name": mc.name,
            }

    # 查默认模型
    if session:
        result = await session.execute(
            select(ModelConfig).where(
                ModelConfig.is_default == True,
                ModelConfig.is_active == True,
            )
        )
        mc = result.scalar_one_or_none()
        if mc:
            return {
                "base_url": mc.base_url,
                "api_key": mc.api_key,
                "chat_model": mc.chat_model,
                "reasoner_model": mc.reasoner_model or mc.chat_model,
                "temperature": mc.temperature,
                "max_tokens": mc.max_tokens,
                "provider": mc.provider,
                "name": mc.name,
            }

    # fallback 到环境变量 DeepSeek
    return {
        "base_url": settings.deepseek_base_url,
        "api_key": settings.deepseek_api_key,
        "chat_model": settings.deepseek_chat_model,
        "reasoner_model": settings.deepseek_reasoner_model,
        "temperature": 0.3,
        "max_tokens": 4096,
        "provider": "deepseek",
        "name": "DeepSeek (env)",
    }


class MultiModelClient:
    """多模型客户端：按 provider 配置动态构建。"""

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config
        if not config.get("api_key"):
            raise RuntimeError(f"模型 {config.get('name', '?')} 未配置 api_key")

    def _build(
        self,
        *,
        reasoner: bool = False,
        temperature: float | None = None,
        streaming: bool = False,
    ) -> ChatOpenAI:
        model_name = (
            self.config["reasoner_model"] if reasoner else self.config["chat_model"]
        )
        return build_chat_model(
            base_url=self.config["base_url"],
            api_key=self.config["api_key"],
            model_name=model_name,
            temperature=temperature if temperature is not None else self.config["temperature"],
            streaming=streaming,
            max_tokens=self.config["max_tokens"],
        )

    async def complete_chat(
        self,
        *,
        messages: list[ChatMessagePayload],
        reasoner: bool = False,
        temperature: float = 0.2,
    ) -> str:
        model = self._build(reasoner=reasoner, temperature=temperature)
        response = await model.ainvoke(
            _to_langchain_messages(messages),
            config={"metadata": {"provider": self.config["provider"]}},
        )
        return _stringify_content(response.content)

    async def stream_chat(
        self,
        *,
        messages: list[ChatMessagePayload],
        temperature: float = 0.3,
    ) -> AsyncGenerator[dict[str, Any], None]:
        model = self._build(temperature=temperature, streaming=True)
        async for chunk in model.astream(
            _to_langchain_messages(messages),
            config={"metadata": {"provider": self.config["provider"]}},
        ):
            content = _stringify_content(chunk.content)
            if content:
                yield {"type": "llm_delta", "content": content}


# 向后兼容：DeepSeekClient 保留，内部委托给 MultiModelClient
class DeepSeekClient:
    """兼容旧代码的 DeepSeek 客户端包装。

    新代码请直接用 MultiModelClient。
    """

    def __init__(self) -> None:
        if not settings.deepseek_api_key:
            raise RuntimeError("AI_IDE_DEEPSEEK_API_KEY is required")
        self._client = MultiModelClient({
            "base_url": settings.deepseek_base_url,
            "api_key": settings.deepseek_api_key,
            "chat_model": settings.deepseek_chat_model,
            "reasoner_model": settings.deepseek_reasoner_model,
            "temperature": 0.3,
            "max_tokens": 4096,
            "provider": "deepseek",
            "name": "DeepSeek (env)",
        })

    async def complete_chat(
        self,
        *,
        messages: list[ChatMessagePayload],
        reasoner: bool = False,
        temperature: float = 0.2,
    ) -> str:
        return await self._client.complete_chat(
            messages=messages, reasoner=reasoner, temperature=temperature
        )

    async def stream_reasoner(
        self,
        *,
        messages: list[ChatMessagePayload],
    ) -> AsyncGenerator[dict[str, Any], None]:
        async for delta in self._client.stream_chat(messages=messages, temperature=0.1):
            yield delta

    async def stream_chat(
        self,
        *,
        messages: list[ChatMessagePayload],
        temperature: float = 0.3,
    ) -> AsyncGenerator[dict[str, Any], None]:
        async for delta in self._client.stream_chat(
            messages=messages, temperature=temperature
        ):
            yield delta
