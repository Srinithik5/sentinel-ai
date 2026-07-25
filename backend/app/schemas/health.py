from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = Field(..., examples=["healthy", "degraded"])
    service: str = Field(..., examples=["sentinel-ai-backend"])
    version: str = Field(..., examples=["1.0.0"])
    database: str = Field(..., examples=["connected", "disconnected"])