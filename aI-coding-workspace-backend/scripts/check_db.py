import asyncio
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.core.db_init import check_database_connection


async def main() -> None:
    version = await check_database_connection()
    print(f"Database connected: {version}")


if __name__ == "__main__":
    asyncio.run(main())

