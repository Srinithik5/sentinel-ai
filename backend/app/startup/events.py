from app.core.logging import get_logger
from app.db.session import check_database_connection, engine

logger = get_logger(__name__)


async def on_startup() -> None:
    logger.info("application_starting")
    if await check_database_connection():
        logger.info("database_connection_established")
    else:
        logger.error("database_connection_failed")


async def on_shutdown() -> None:
    logger.info("application_stopping")
    await engine.dispose()