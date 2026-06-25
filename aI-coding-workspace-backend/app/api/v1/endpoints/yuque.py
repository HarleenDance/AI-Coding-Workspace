"""语雀文档 API 代理。

接口文档: https://www.yuque.com/open-api
认证: 用户在 https://www.yuque.com/settings/tokens 创建 Personal Token，
      填到前端设置面板，通过 Header X-Auth-Token 传给本接口。

本模块只在请求时透传 Token，不持久化。
"""
import httpx
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

router = APIRouter(prefix="/yuque", tags=["Yuque"])

YUQUE_BASE = "https://openapi.yuque.com/api/v2"

# 默认请求头（User-Agent 是语雀 API 必需的）
BASE_HEADERS = {
    "User-Agent": "AI-Coding-Workspace/1.0",
    "Accept": "application/json",
}


class YuqueTokenIn(BaseModel):
    """请求体里的语雀 Token。"""
    token: str


@router.post("/user")
async def get_user(payload: YuqueTokenIn):
    """获取语雀用户信息（验证 Token 是否有效）。"""
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            f"{YUQUE_BASE}/user",
            headers={**BASE_HEADERS, "X-Auth-Token": payload.token},
        )
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=_extract_error(resp))
    return resp.json().get("data", {})


@router.post("/repos")
async def list_repos(payload: YuqueTokenIn):
    """列出用户的知识库。"""
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            f"{YUQUE_BASE}/repos",
            headers={**BASE_HEADERS, "X-Auth-Token": payload.token},
        )
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=_extract_error(resp))
    return resp.json().get("data", [])


@router.post("/repos/{namespace}/docs")
async def list_docs(namespace: str, payload: YuqueTokenIn, offset: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100)):
    """列出知识库下的文档目录。"""
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            f"{YUQUE_BASE}/repos/{namespace}/docs",
            headers={**BASE_HEADERS, "X-Auth-Token": payload.token},
            params={"offset": offset, "limit": limit},
        )
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=_extract_error(resp))
    return resp.json().get("data", [])


@router.post("/repos/{namespace}/docs/{slug}")
async def get_doc(namespace: str, slug: str, payload: YuqueTokenIn):
    """获取文档详情（Markdown 源码）。"""
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            f"{YUQUE_BASE}/repos/{namespace}/docs/{slug}",
            headers={**BASE_HEADERS, "X-Auth-Token": payload.token},
            params={"raw": "1"},  # 返回 Markdown 源码
        )
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=_extract_error(resp))
    return resp.json().get("data", {})


@router.post("/repos/{namespace}/toc")
async def get_toc(namespace: str, payload: YuqueTokenIn):
    """获取知识库目录树。"""
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            f"{YUQUE_BASE}/repos/{namespace}/toc",
            headers={**BASE_HEADERS, "X-Auth-Token": payload.token},
        )
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=_extract_error(resp))
    return resp.json().get("data", [])


def _extract_error(resp: httpx.Response) -> str:
    """从语雀错误响应里提取可读信息。"""
    try:
        data = resp.json()
        msg = data.get("message") or data.get("errors") or str(data)
        return str(msg)[:200]
    except Exception:
        return resp.text[:200]
