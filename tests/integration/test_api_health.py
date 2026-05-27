from fastapi.testclient import TestClient

from repopilot import __version__
from repopilot.api import create_app
from repopilot.config import Settings


def test_health_endpoint_returns_stable_metadata():
    app = create_app(Settings(app_name="RepoPilot Test", environment="test"))
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "name": "RepoPilot Test",
        "version": __version__,
        "status": "ok",
        "environment": "test",
    }
