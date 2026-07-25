import logging

from sqlalchemy import text

from app.db.session import engine

logger = logging.getLogger(__name__)


async def on_startup() -> None:
    logger.info("Starting SentinelAI backend...")
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        logger.info("Database connection established.")
    except Exception:
        logger.exception("Database connection failed during startup.")


async def on_shutdown() -> None:
    logger.info("Shutting down SentinelAI backend...")
    engine.dispose()