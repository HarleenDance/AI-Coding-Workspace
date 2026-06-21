from fastapi import APIRouter

from app.core.db_init import check_database_connection

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("/db")
async def check_db_health() -> dict[str, str]:
    version = await check_database_connection()
    return {
        "status": "ok",
        "database": "postgresql",
        "version": version,
    }

