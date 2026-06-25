"""AI 代码补全接口。

基于 FIM (Fill-In-the-Middle) 模式，用光标前后的代码作为上下文，
调用 LLM 生成补全建议。支持流式与非流式。
"""
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.core.dependencies import DbSession
from app.engine.agents.multi_model import MultiModelClient, get_model_config

router = APIRouter(prefix="/completion", tags=["Code Completion"])


class CompletionRequest(BaseModel):
    """代码补全请求。"""

    # 代码上下文
    prefix: str = Field(..., description="光标前的代码（含当前文件全部上文）")
    suffix: str = Field(default="", description="光标后的代码")
    language: str = Field(default="python", description="编程语言")
    file_path: str = Field(default="", description="文件路径（用于上下文）")

    # 模型选择
    model_id: str | None = None

    # 生成参数
    temperature: float = Field(default=0.2, description="越低越确定")
    max_tokens: int = Field(default=128, description="补全长度上限")
    n: int = Field(default=1, description="候选数量（目前只支持 1）")


class CompletionResponse(BaseModel):
    text: str
    stop: bool = True


# 不同语言的注释提示符
_COMMENT_PREFIX = {
    "python": "#",
    "javascript": "//",
    "typescript": "//",
    "java": "//",
    "go": "//",
    "rust": "//",
    "c": "//",
    "cpp": "//",
    "csharp": "//",
    "html": "<!--",
    "css": "/*",
    "vue": "//",
    "yaml": "#",
    "dockerfile": "#",
    "shell": "#",
    "bash": "#",
    "sql": "--",
    "markdown": "<!--",
}


def _build_fim_messages(req: CompletionRequest) -> list[dict[str, str]]:
    """构造 FIM 提示消息。

    对支持 DeepSeek/Qwen FIM 协议的模型，可以直接用 <｜fim_begin｜>...<｜fim_hole｜>...<｜fim_end｜>
    但为了通用性，这里用 chat 接口 + 明确指令。
    """
    comment = _COMMENT_PREFIX.get(req.language.lower(), "//")

    system = (
        "你是代码补全引擎。只输出要插入到光标处的代码片段，"
        "不要输出任何解释、markdown 标记或对话。"
        "代码必须自然衔接 prefix 末尾和 suffix 开头，不要重复已有代码。"
        f"语言：{req.language}。"
    )

    # 构造用户消息：用清晰的分隔标记
    user_parts = [
        f"{comment} 文件：{req.file_path or 'untitled'}",
        f"{comment} 语言：{req.language}",
        "",
        "===== 光标前 =====",
        req.prefix[-3000:] if len(req.prefix) > 3000 else req.prefix,
        "===== 光标位置（请在此处补全） =====",
        "===== 光标后 =====",
        req.suffix[:1500] if len(req.suffix) > 1500 else req.suffix,
        "===== 光标位置（请在此处补全） =====",
        "",
        f"{comment} 请直接输出要插入的代码，不要包含上面的任何内容，不要包含 markdown 代码块标记：",
    ]

    return [
        {"role": "system", "content": system},
        {"role": "user", "content": "\n".join(user_parts)},
    ]


def _clean_completion(text: str, prefix: str, suffix: str) -> str:
    """清理 LLM 返回的补全文本。"""
    # 去掉常见的 markdown 代码块包裹
    cleaned = text.strip()

    # 去掉 ```lang ... ``` 包裹
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        # 去掉首行 ```
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        # 去掉末尾 ```
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines)

    # 去掉 LLM 重复 prefix 末尾行的情况
    if prefix:
        prefix_last_line = prefix.rstrip().splitlines()[-1].strip() if prefix.strip() else ""
        if prefix_last_line and cleaned.startswith(prefix_last_line):
            cleaned = cleaned[len(prefix_last_line):].lstrip()

    # 如果 suffix 开头和补全结尾相同，截掉重复
    if suffix and cleaned:
        first_suffix_line = suffix.lstrip().splitlines()[0].strip() if suffix.strip() else ""
        if first_suffix_line and cleaned.rstrip().endswith(first_suffix_line):
            idx = cleaned.rstrip().rfind(first_suffix_line)
            cleaned = cleaned[:idx]

    return cleaned


@router.post("", response_model=CompletionResponse)
async def complete(req: CompletionRequest, session: DbSession) -> CompletionResponse:
    """非流式代码补全。"""
    model_config = await get_model_config(session, req.model_id)
    client = MultiModelClient(model_config)

    messages = _build_fim_messages(req)
    raw = await client.complete_chat(
        messages=messages,
        temperature=req.temperature,
    )
    text = _clean_completion(raw, req.prefix, req.suffix)
    return CompletionResponse(text=text)


@router.post("/stream")
async def complete_stream(
    req: CompletionRequest,
    session: DbSession,
) -> StreamingResponse:
    """流式代码补全（SSE）。"""

    import json

    async def gen():
        model_config = await get_model_config(session, req.model_id)
        client = MultiModelClient(model_config)

        messages = _build_fim_messages(req)
        buffer = ""
        try:
            async for delta in client.stream_chat(
                messages=messages,
                temperature=req.temperature,
            ):
                content = delta.get("content", "")
                buffer += content
                yield f"data: {json.dumps({'type': 'token', 'content': content}, ensure_ascii=False)}\n\n"

            # 清理后整体返回一次
            cleaned = _clean_completion(buffer, req.prefix, req.suffix)
            yield f"data: {json.dumps({'type': 'done', 'text': cleaned}, ensure_ascii=False)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
