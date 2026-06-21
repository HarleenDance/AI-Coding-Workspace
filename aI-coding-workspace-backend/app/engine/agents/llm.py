from collections.abc import AsyncGenerator
from typing import Any

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.core.config import get_settings

settings = get_settings()

ChatMessagePayload = dict[str, str]


class DeepSeekClient:
    """DeepSeek 模型路由客户端。

    - 普通问答 / 代码解释 / Diff 生成：deepseek-chat
    - 复杂推理 / 多步规划：deepseek-reasoner

    当前实现使用 LangChain 1.x 的 langchain-openai 集成。DeepSeek 暴露
    OpenAI 兼容接口，因此只需要替换 base_url、api_key 和 model。
    """

    def __init__(self) -> None:
        if not settings.deepseek_api_key:
            raise RuntimeError("AI_IDE_DEEPSEEK_API_KEY is required")

    def _build_model(
        self,
        *,
        reasoner: bool = False,
        temperature: float = 0.2,
        streaming: bool = False,
    ) -> ChatOpenAI:
        model_name = (
            settings.deepseek_reasoner_model
            if reasoner
            else settings.deepseek_chat_model
        )
        return ChatOpenAI(
            model=model_name,
            base_url=settings.deepseek_base_url,
            api_key=settings.deepseek_api_key,
            temperature=temperature,
            timeout=120,
            streaming=streaming,
            # OpenAI 兼容服务未必支持 token usage streaming，显式关闭更稳。
            stream_usage=False,
        )

    @staticmethod
    def _to_langchain_messages(
        messages: list[ChatMessagePayload],
    ) -> list[BaseMessage]:
        converted: list[BaseMessage] = []
        for message in messages:
            role = message["role"]
            content = message["content"]
            if role == "system":
                converted.append(SystemMessage(content=content))
            else:
                converted.append(HumanMessage(content=content))
        return converted

    @staticmethod
    def _stringify_content(content: Any) -> str:
        if isinstance(content, str):
            return content
        return str(content)

    async def complete_chat(
        self,
        *,
        messages: list[ChatMessagePayload],
        reasoner: bool = False,
        temperature: float = 0.2,
    ) -> str:
        model = self._build_model(
            reasoner=reasoner,
            temperature=temperature,
        )
        response = await model.ainvoke(
            self._to_langchain_messages(messages),
            config={
                "metadata": {
                    "model_route": "reasoner" if reasoner else "chat",
                    "provider": "deepseek",
                },
            },
        )
        return self._stringify_content(response.content)

    async def stream_reasoner(
        self,
        *,
        messages: list[ChatMessagePayload],
    ) -> AsyncGenerator[dict[str, Any], None]:
        model = self._build_model(
            reasoner=True,
            temperature=0.1,
            streaming=True,
        )
        async for chunk in model.astream(
            self._to_langchain_messages(messages),
            config={
                "metadata": {
                    "model_route": "reasoner",
                    "provider": "deepseek",
                },
            },
        ):
            content = self._stringify_content(chunk.content)
            if content:
                yield {"type": "llm_delta", "content": content}

    async def stream_chat(
        self,
        *,
        messages: list[ChatMessagePayload],
        temperature: float = 0.3,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """流式输出普通 chat 模型的回复。"""
        model = self._build_model(
            reasoner=False,
            temperature=temperature,
            streaming=True,
        )
        async for chunk in model.astream(
            self._to_langchain_messages(messages),
            config={
                "metadata": {
                    "model_route": "chat",
                    "provider": "deepseek",
                },
            },
        ):
            content = self._stringify_content(chunk.content)
            if content:
                yield {"type": "llm_delta", "content": content}
