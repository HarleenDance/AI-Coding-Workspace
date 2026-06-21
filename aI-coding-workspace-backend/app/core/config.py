from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置。

    生产环境通过 AI_IDE_ 前缀注入，例如 AI_IDE_DEEPSEEK_API_KEY。
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="AI_IDE_",
        extra="ignore",
    )

    app_name: str = "AI Coding Workspace Backend"
    api_v1_prefix: str = "/api"

    database_url: str = (
        "postgresql+asyncpg://postgres:123456@localhost:5432/ai_workspace_db"
    )

    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_api_key: str = Field(default="")
    deepseek_chat_model: str = "deepseek-chat"
    deepseek_reasoner_model: str = "deepseek-reasoner"

    dashscope_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    dashscope_api_key: str = Field(default="")
    embedding_model: str = "text-embedding-v3"
    embedding_dimension: int = 1024
    embedding_batch_size: int = 16

    runtime_dir: Path = Path("runtime")
    checkpoint_sqlite_path: Path = Path("runtime/langgraph_checkpoints.sqlite3")


@lru_cache
def get_settings() -> Settings:
    return Settings()
