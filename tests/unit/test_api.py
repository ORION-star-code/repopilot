"""Tests for FastAPI API endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient

from repopilot.api import create_app
from repopilot.config import Settings


class TestHealthEndpoint:
    """Test /health endpoint."""

    def test_health_returns_200(self) -> None:
        app = create_app(Settings())
        client = TestClient(app)

        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "name" in data
        assert "version" in data
        assert "environment" in data

    def test_health_returns_correct_environment(self) -> None:
        settings = Settings(environment="test")
        app = create_app(settings)
        client = TestClient(app)

        response = client.get("/health")

        assert response.status_code == 200
        assert response.json()["environment"] == "test"


class TestIntakeEndpoint:
    """Test /api/v1/intake endpoint."""

    def test_intake_github_url(self) -> None:
        app = create_app(Settings())
        client = TestClient(app)

        response = client.post("/api/v1/intake", json={
            "input": "https://github.com/octo/repo/issues/42",
        })

        assert response.status_code == 200
        data = response.json()
        assert data["source"] == "github_issue"
        assert data["repository"] == "octo/repo"
        assert data["issue_number"] == 42

    def test_intake_bug_description(self) -> None:
        app = create_app(Settings())
        client = TestClient(app)

        response = client.post("/api/v1/intake", json={
            "input": "Login fails after token refresh",
        })

        assert response.status_code == 200
        data = response.json()
        assert data["source"] == "bug_description"
        assert "Login fails" in data["title"]

    def test_intake_empty_input_returns_422(self) -> None:
        app = create_app(Settings())
        client = TestClient(app)

        response = client.post("/api/v1/intake", json={
            "input": "",
        })

        assert response.status_code == 422  # Pydantic validation error

    def test_intake_whitespace_only_returns_400(self) -> None:
        app = create_app(Settings())
        client = TestClient(app)

        response = client.post("/api/v1/intake", json={
            "input": "   ",
        })

        assert response.status_code == 400


class TestInspectEndpoint:
    """Test /api/v1/inspect endpoint."""

    def test_inspect_current_directory(self) -> None:
        app = create_app(Settings())
        client = TestClient(app)

        response = client.post("/api/v1/inspect", json={
            "path": ".",
        })

        assert response.status_code == 200
        data = response.json()
        assert "root" in data
        assert "files" in data
        assert "language_counts" in data

    def test_inspect_nonexistent_path_returns_400(self) -> None:
        app = create_app(Settings())
        client = TestClient(app)

        response = client.post("/api/v1/inspect", json={
            "path": "/nonexistent/path/that/does/not/exist",
        })

        # Absolute paths are rejected by contain_path (400), not 404
        assert response.status_code == 400


class TestPlanEndpoint:
    """Test /api/v1/plan endpoint."""

    def test_plan_creates_repair_plan(self) -> None:
        app = create_app(Settings())
        client = TestClient(app)

        response = client.post("/api/v1/plan", json={
            "input": "Tests fail when config is missing",
            "repo": ".",
        })

        assert response.status_code == 200
        data = response.json()
        assert "summary" in data
        assert "target_files" in data
        assert "steps" in data
        assert "verification" in data

    def test_plan_empty_input_returns_400(self) -> None:
        app = create_app(Settings())
        client = TestClient(app)

        response = client.post("/api/v1/plan", json={
            "input": "",
        })

        assert response.status_code == 422


class TestDryRunEndpoint:
    """Test /api/v1/dry-run endpoint."""

    def test_dry_run_returns_artifacts(self) -> None:
        app = create_app(Settings())
        client = TestClient(app)

        response = client.post("/api/v1/dry-run", json={
            "input": "Token refresh fails",
            "repo": ".",
        })

        assert response.status_code == 200
        data = response.json()
        assert data["workflow_status"] == "dry_run_completed"
        assert "plan" in data
        assert "artifacts" in data
        assert data["approval_required"] is True

    def test_dry_run_empty_input_returns_422(self) -> None:
        app = create_app(Settings())
        client = TestClient(app)

        response = client.post("/api/v1/dry-run", json={
            "input": "",
        })

        assert response.status_code == 422
