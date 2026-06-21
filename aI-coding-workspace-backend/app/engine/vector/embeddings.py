from collections.abc import Iterable

import httpx

from app.core.config import get_settings

settings = get_settings()


def _batched(items: list[str], batch_size: int) -> Iterable[list[str]]:
    for index in range(0, len(items), batch_size):
        yield items[index : index + batch_size]


class EmbeddingClient:
    """DashScope / Qwen3 Embedding 客户端。

    DashScope 提供 OpenAI 兼容 embeddings 接口，因此这里不引入额外 SDK，
    便于在企业内网环境中统一代理、限流和审计。
    """

    def __init__(self) -> None:
        if not settings.dashscope_api_key:
            raise RuntimeError("AI_IDE_DASHSCOPE_API_KEY is required")

        self._client = httpx.AsyncClient(
            base_url=settings.dashscope_base_url,
            timeout=60,
            headers={"Authorization": f"Bearer {settings.dashscope_api_key}"},
        )

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        embeddings: list[list[float]] = []
        for batch in _batched(texts, settings.embedding_batch_size):
            response = await self._client.post(
                "/embeddings",
                json={
                    "model": settings.embedding_model,
                    "input": batch,
                    "encoding_format": "float",
                },
            )
            response.raise_for_status()
            payload = response.json()
            embeddings.extend(item["embedding"] for item in payload["data"])

        return embeddings

