from fastapi import APIRouter

from app.api.v1.endpoints import agents, chat, health, models, projects, vibe

api_router = APIRouter()
api_router.include_router(agents.router)
api_router.include_router(models.router)
api_router.include_router(projects.router)
api_router.include_router(chat.router)
api_router.include_router(health.router)
api_router.include_router(vibe.router)
