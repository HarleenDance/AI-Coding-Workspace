"""浏览器代理：剥离 X-Frame-Options，让 iframe 能嵌入任意网站。

原理：
  用户 → 后端代理(httpx 请求目标站) → 删除拒绝头 → 返回给前端 iframe

相对路径处理：在 HTML <head> 注入 <base> 标签，让浏览器以目标 URL 为基准。
"""
from urllib.parse import urljoin

import httpx
from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse, Response

router = APIRouter(prefix="/browser", tags=["Browser"])

# 需要剥离的响应头
STRIP_HEADERS = {
    "x-frame-options",
    "content-security-policy",
    "content-security-policy-report-only",
    "x-content-security-policy",
    "frame-options",
    # httpx 自动解压了 gzip/br，必须移除编码头，否则浏览器二次解压会乱码
    "content-encoding",
    "transfer-encoding",
    # 这两个由 Response 自己管理，不能透传
    "content-length",
    "connection",
}

# 需要跟随重定向时保持的请求头
FORWARD_HEADERS = ["user-agent", "accept", "accept-language", "cookie"]


@router.get("/proxy")
async def proxy_page(
    url: str = Query(..., description="目标网页 URL"),
):
    """代理目标网页，剥离 X-Frame-Options，使其可被 iframe 嵌入。"""
    if not url.startswith(("http://", "https://")):
        return Response(content="Invalid URL", status_code=400)

    try:
        async with httpx.AsyncClient(
            timeout=20,
            follow_redirects=True,
            verify=False,  # 忽略 SSL 证书问题
        ) as client:
            resp = await client.get(
                url,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/125.0.0.0 Safari/537.36"
                    ),
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                },
            )
    except httpx.RequestError as e:
        return Response(content=f"代理请求失败: {e}", status_code=502)

    # 构建新的响应头：剥离阻止嵌入的头
    new_headers = {}
    for key, value in resp.headers.items():
        if key.lower() not in STRIP_HEADERS:
            new_headers[key] = value

    body = resp.content
    content_type = resp.headers.get("content-type", "")

    # 如果是 HTML，注入 <base> 标签修复相对路径
    if "text/html" in content_type:
        html = body.decode("utf-8", errors="replace")
        base_tag = f'<base href="{url}">'
        # 注入到 <head> 后面，没有 head 就放最前面
        if "<head>" in html.lower():
            import re
            html = re.sub(r"<head[^>]*>", lambda m: m.group(0) + base_tag, html, count=1, flags=re.IGNORECASE)
        elif "<html" in html.lower():
            html = html.replace("<html", f"<html>\n{base_tag}", 1)
        else:
            html = base_tag + html
        body = html.encode("utf-8")

    return Response(
        content=body,
        status_code=resp.status_code,
        headers=new_headers,
        media_type=content_type or None,
    )


@router.get("/proxy-resource")
async def proxy_resource(
    url: str = Query(..., description="资源 URL"),
):
    """代理子资源（CSS/JS/图片/字体），解决跨域和相对路径问题。"""
    if not url.startswith(("http://", "https://")):
        return Response(content="Invalid URL", status_code=400)

    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True, verify=False) as client:
            resp = await client.get(url)
    except httpx.RequestError:
        return Response(content="Resource fetch failed", status_code=502)

    return Response(
        content=resp.content,
        status_code=resp.status_code,
        headers={"content-type": resp.headers.get("content-type", "application/octet-stream")},
    )
