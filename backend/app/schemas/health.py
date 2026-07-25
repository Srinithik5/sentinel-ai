from datetime import datetime

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = Field(..., examples=["ok"])
    timestamp: datetime
    database: str = Field(..., examples=["connected", "unavailable"])