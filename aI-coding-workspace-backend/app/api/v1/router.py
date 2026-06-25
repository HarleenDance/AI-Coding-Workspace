from fastapi import APIRouter

from app.api.v1.endpoints import (
    agents,
    browser_proxy,
    chat,
    completion,
    git,
    health,
    models,
    projects,
    vibe,
    yuque,
)

api_router = APIRouter()
api_router.include_router(agents.router)
api_router.include_router(models.router)
api_router.include_router(projects.router)
api_router.include_router(chat.router)
api_router.include_router(completion.router)
api_router.include_router(git.router)
api_router.include_router(health.router)
api_router.include_router(vibe.router)
api_router.include_router(yuque.router)
api_router.include_router(browser_proxy.router)
