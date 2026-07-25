from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.db.session import check_database_connection
from app.schemas.health import HealthResponse

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Service health check",
    status_code=status.HTTP_200_OK,
)
async def health_check() -> HealthResponse | JSONResponse:
    database_connected = await check_database_connection()

    payload = HealthResponse(
        status="healthy" if database_connected else "degraded",
        service=settings.SERVICE_NAME,
        version=settings.VERSION,
        database="connected" if database_connected else "disconnected",
    )

    if not database_connected:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=payload.model_dump(),
        )

    return payload