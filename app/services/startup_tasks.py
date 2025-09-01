"""
Startup tasks for Gallery Twin.

Provides a single entrypoint to initialize the database and optionally
load YAML content. To be called from FastAPI app startup later.
"""

import asyncio
from typing import Optional

from app.db import init_database, get_session
from app.services.content_loader import load_content_from_dir


async def run_startup_tasks(
    load_content: bool = True, content_dir: str = "content/exhibits"
) -> None:
    """
    Initialize database and (optionally) load content from YAML.
    Designed to be awaited from application startup.
    """
    await init_database()
    if load_content:
        session = await get_session()
        try:
            await load_content_from_dir(session=session, content_dir=content_dir)
        except Exception as exc:
            # Non-fatal: app should still start even if content fails to load
            print(f"[startup_tasks] Content load failed: {exc}")
        finally:
            await session.close()


if __name__ == "__main__":
    asyncio.run(run_startup_tasks())