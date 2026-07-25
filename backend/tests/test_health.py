from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_check_reports_service_metadata() -> None:
    response = client.get("/api/v1/health")

    assert response.status_code in (200, 503)
    body = response.json()
    assert body["service"] == "sentinel-ai-backend"
    assert body["version"] == "1.0.0"
    assert body["status"] in {"healthy", "degraded"}
    assert body["database"] in {"connected", "disconnected"}