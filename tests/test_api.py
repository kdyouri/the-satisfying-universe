import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tsu.api import create_app
from tsu.config import Settings

TOKEN = "test-admin-token-with-at-least-32-characters"


@pytest.fixture
def client(local_engine):
    settings = Settings(_env_file=None, admin_token=TOKEN)
    with TestClient(create_app(settings, local_engine)) as client:
        client.headers["Authorization"] = f"Bearer {TOKEN}"
        yield client


def test_liveness_is_public(local_engine):
    client = TestClient(create_app(Settings(_env_file=None), local_engine))
    assert client.get("/health/live").json() == {"status": "alive"}
    assert client.get("/api/overview").status_code == 503


@pytest.mark.parametrize(
    "path",
    [
        "/admin",
        "/api/jobs",
        "/api/overview",
        "/api/alerts",
        "/api/capabilities",
        "/api/openapi.json",
        "/health/ready",
    ],
)
def test_all_admin_paths_protected(local_engine, path):
    client = TestClient(create_app(Settings(_env_file=None, admin_token=TOKEN), local_engine))
    assert client.get(path).status_code == 401
    assert client.get(path, headers={"Authorization": "Bearer bad"}).status_code == 401


@pytest.mark.parametrize("cookie", [None, "invalid-session"])
def test_browser_admin_without_active_session_opens_login(local_engine, cookie):
    client = TestClient(create_app(Settings(_env_file=None, admin_token=TOKEN), local_engine))
    if cookie:
        client.cookies.set("__Host-tsu_owner", cookie)
    response = client.get("/admin", headers={"Accept": "text/html"}, follow_redirects=False)
    assert response.status_code == 303 and response.headers["location"] == "/login"
    assert response.headers["cache-control"] == "no-store"
    login = client.get("/admin", headers={"Accept": "text/html"})
    assert login.status_code == 200 and login.url.path == "/login"
    assert "Owner sign in" in login.text and TOKEN not in login.text
    assert client.get("/api/overview", headers={"Accept": "text/html"}).status_code == 401
    assert (
        client.get(
            "/admin", headers={"Accept": "text/html", "Authorization": "Bearer bad"}
        ).status_code
        == 401
    )


def test_job_create_replay_conflict_and_restart(client, local_engine):
    headers = {"Idempotency-Key": "concept:one"}
    first = client.post("/api/jobs", json={"concept": "Symmetric liquid droplets"}, headers=headers)
    assert first.status_code == 201
    replay = client.post(
        "/api/jobs", json={"concept": "Symmetric liquid droplets"}, headers=headers
    )
    assert replay.status_code == 200
    assert replay.json()["id"] == first.json()["id"]
    assert (
        client.post("/api/jobs", json={"concept": "Other idea"}, headers=headers).status_code == 409
    )
    # New application instance uses the committed job; no broker was required.
    restarted = TestClient(create_app(Settings(_env_file=None, admin_token=TOKEN), local_engine))
    response = restarted.get(
        f"/api/jobs/{first.json()['id']}", headers={"Authorization": f"Bearer {TOKEN}"}
    )
    assert response.json()["status"] == "queued"
    assert client.get("/api/overview").json()["jobs"] == {"queued": 1}


def test_input_validation(client):
    assert client.post("/api/jobs", json={"concept": "abc"}).status_code == 422
    assert (
        client.post(
            "/api/jobs",
            json={"concept": "abc", "publish": True},
            headers={"Idempotency-Key": "bad"},
        ).status_code
        == 422
    )
    assert client.get("/api/jobs?limit=101").status_code == 422
    assert client.get("/api/jobs/nonexistent").status_code == 404


def test_readiness_caps_and_admin(client):
    assert client.get("/health/ready").status_code == 200
    result = client.get("/api/overview").json()
    assert result["capabilities"]["generation_available"] is False
    assert result["capabilities"]["publishing_available"] is False
    assert result["daily_cap_usd"] == "0"
    profile = result["capabilities"]["production_profile"]
    assert profile["version"] == "native_audio_v5"
    assert profile["audio_mode"] == "native_ai_generated_audio"
    assert profile["duration_seconds"] == 8 and profile["clip_count"] == 1
    assert profile["postproduction"] is False and profile["master_preserved"]
    assert profile["minor_defects_tolerated"] and not profile["automatic_regeneration"]
    admin = client.get("/admin")
    assert admin.status_code == 200
    assert "Not connected" in admin.text
    assert "Production programmée désactivée" in admin.text
    assert "son IA natif" in admin.text
    assert TOKEN not in admin.text
    assert "no-store" in admin.headers["cache-control"]


def test_api_snapshot(client):
    stored = json.loads((Path(__file__).resolve().parents[1] / "docs/openapi.json").read_text())
    assert client.get("/api/openapi.json").json() == stored
    assert client.get("/docs").status_code == 404
    assert client.get("/openapi.json").status_code == 404
