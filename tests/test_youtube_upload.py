"""Run the actual upload service/API through a local Postman Google stand-in."""

import json
import os
import shutil
from datetime import timedelta
from pathlib import Path

import pytest
import requests
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text

from tsu.api import create_app
from tsu.config import Settings
from tsu.jobs import create_job
from tsu.models import (
    Concept,
    ModelUsage,
    OAuthCredential,
    Prompt,
    Publication,
    SocialAccount,
    VideoGeneration,
    utcnow,
)
from tsu.youtube_auth import YOUTUBE_EDIT_SCOPE, YOUTUBE_SCOPES
from tsu.youtube_metadata import FIRST_VIDEO_LOCALIZATIONS, LANGUAGES, PUBLICATION_OPERATION
from tsu.youtube_publication import YouTubePublication
from tsu.youtube_upload import PrivateTestUpload, UploadEndpoints, UploadHTTP

BASE = "http://127.0.0.1:4012/youtube-upload"
TOKEN = "synthetic-owner-token-with-at-least-32-characters"


@pytest.mark.parametrize(
    "path",
    [
        "/api/youtube/test-upload",
        "/api/youtube/test-upload/plan",
    ],
)
def test_upload_paths_require_owner(local_engine, path):
    client = TestClient(create_app(Settings(_env_file=None, admin_token=TOKEN), local_engine))
    assert client.get(path).status_code == 401
    if path == "/api/youtube/test-upload":
        assert client.post(path, json={"confirm_private_test": True}).status_code == 401


def test_upload_input_cannot_enable_public_or_choose_a_file(local_engine):
    client = TestClient(create_app(Settings(_env_file=None, admin_token=TOKEN), local_engine))
    client.headers["Authorization"] = "Bearer " + TOKEN
    for body in (
        {},
        {"confirm_private_test": False},
        {"confirm_private_test": True, "privacy": "public"},
        {"confirm_private_test": True, "path": "/etc/passwd"},
    ):
        assert client.post("/api/youtube/test-upload", json=body).status_code == 422


@pytest.fixture
def simulated_upload(pg_sessions, postgres_engine, tmp_path):
    if os.environ.get("TSU_UPLOAD_SIMULATION") != "1":
        pytest.skip("Start the local Postman upload simulation and set TSU_UPLOAD_SIMULATION=1")
    key = Fernet.generate_key()
    cipher = Fernet(key)
    settings = Settings(
        _env_file=None,
        admin_token=TOKEN,
        token_encryption_key=key.decode(),
        youtube_channel_id="UC8DbuevZRxVTWxltG9oDFRw",
        youtube_handle="@techno-inno",
        youtube_client_id="fake.apps.googleusercontent.com",
        youtube_client_secret="fake-secret",
    )
    with pg_sessions.begin() as db:
        account = SocialAccount(
            platform="youtube",
            external_id=settings.youtube_channel_id,
            handle="@techno-inno",
            secret_reference="synthetic",
            scopes=list(YOUTUBE_SCOPES),
            approved_for_publication=False,
        )
        db.add(account)
        db.flush()
        raw = {
            "client_id": "fake.apps.googleusercontent.com",
            "refresh_token": "fake-refresh",
            "expiry": (utcnow() - timedelta(hours=1)).isoformat(),
            "token": "expired-fake",
        }
        db.add(
            OAuthCredential(
                account_id=account.id,
                credentials_encrypted=cipher.encrypt(json.dumps(raw).encode()).decode(),
            )
        )
        concept = Concept(
            name="Synthetic upload fixture", category="test", fingerprint="mock", brief={}
        )
        db.add(concept)
        db.flush()
        prompt = Prompt(concept_id=concept.id, version=1, text="Synthetic fixture, never publish")
        db.add(prompt)
        db.flush()
        job, _ = create_job(db, "owner:first-video:v1", {"fixture": True})
        db.add(
            VideoGeneration(
                concept_id=concept.id,
                prompt_id=prompt.id,
                job_id=job.id,
                attempt=1,
                clip_index=0,
                provider="synthetic",
                model="synthetic",
                parameters={},
                status="completed",
            )
        )
    asset = tmp_path / "synthetic.mp4"
    shutil.copyfile(Path(".runtime/youtube-synthetic-test.mp4"), asset)

    def factory():
        http = UploadHTTP(
            UploadEndpoints(
                token=BASE + "/token",
                api=BASE + "/youtube/v3",
                start=BASE + "/upload/youtube/v3/videos",
            ),
            timeout=(1, 0.2),
            chunk_size=524288,
        )
        return PrivateTestUpload(settings, postgres_engine, http, asset)

    client = TestClient(create_app(settings, postgres_engine, youtube_upload_factory=factory))
    client.app.state.upload_settings = settings
    client.app.state.upload_factory = factory
    client.headers["Authorization"] = "Bearer " + TOKEN
    return client, asset, cipher


@pytest.mark.postgres
@pytest.mark.parametrize(
    "mode",
    [
        "success",
        "partial_ack",
        "lost_completion",
        "midway_timeout",
        "processing_delay",
        "processing_failure",
        "wrong_channel",
        "revoked_grant",
        "bad_location",
        "start_timeout",
    ],
)
def test_real_http_upload_and_safe_resume(simulated_upload, pg_sessions, mode):
    control = requests.post(BASE + "/__control", json={"mode": mode}, timeout=5)
    assert control.headers.get("X-TSU-Mock") == "youtube-upload"
    client, asset, cipher = simulated_upload
    first = client.post("/api/youtube/test-upload", json={"confirm_private_test": True})
    interrupted = mode in ("lost_completion", "midway_timeout")
    permanent = mode in ("wrong_channel", "revoked_grant", "bad_location", "start_timeout")
    if interrupted or permanent:
        assert first.status_code == 409, first.text
    else:
        assert first.status_code in (200, 202), first.text
    second = client.post("/api/youtube/test-upload", json={"confirm_private_test": True})
    if permanent:
        assert second.status_code == 409, second.text
    else:
        assert second.status_code in (200, 202), second.text
        data = client.get("/api/youtube/test-upload").json()
        assert data["video_id"] == "testVideo01" and data["privacy"] == "private"
        assert data["status"] == (
            "processing_failed" if mode == "processing_failure" else "processed_private"
        )
        assert "upload_id" not in json.dumps(data)
    observed = requests.get(BASE + "/__control", timeout=5).json()["events"]
    starts = [
        x for x in observed if x["method"] == "POST" and x["path"] == "/upload/youtube/v3/videos"
    ]
    assert len(starts) == (0 if mode in ("wrong_channel", "revoked_grant") else 1)
    if starts:
        assert starts[0]["metadata"]["status"]["privacyStatus"] == "private"
        assert starts[0]["metadata"]["status"]["containsSyntheticMedia"] is True
    if interrupted:
        assert sum(e.get("range", "").startswith("bytes */") for e in observed) >= 2
    with pg_sessions() as db:
        assert db.scalar(select(func.count()).select_from(ModelUsage)) == 0
        assert not db.scalar(select(SocialAccount)).approved_for_publication
        pubs = db.scalars(select(Publication)).all()
        assert len(pubs) == (0 if mode in ("wrong_channel", "revoked_grant") else 1)
        if pubs and pubs[0].upload_session_reference:
            assert "http" not in pubs[0].upload_session_reference
            assert (
                "synthetic-session"
                in cipher.decrypt(pubs[0].upload_session_reference.encode()).decode()
            )


@pytest.mark.postgres
def test_changed_asset_and_concurrent_upload_do_not_create_duplicates(
    simulated_upload,
    pg_sessions,
    postgres_engine,
):
    requests.post(BASE + "/__control", json={"mode": "success"}, timeout=5).raise_for_status()
    client, asset, _ = simulated_upload
    with postgres_engine.connect() as lock:
        lock.execute(text("SELECT pg_advisory_lock(865190042)"))
        assert (
            client.post("/api/youtube/test-upload", json={"confirm_private_test": True}).status_code
            == 409
        )
        lock.execute(text("SELECT pg_advisory_unlock(865190042)"))
    assert (
        client.post("/api/youtube/test-upload", json={"confirm_private_test": True}).status_code
        == 200
    )
    with asset.open("ab") as output:
        output.write(b"changed-file")
    assert (
        client.post("/api/youtube/test-upload", json={"confirm_private_test": True}).status_code
        == 409
    )
    observed = requests.get(BASE + "/__control", timeout=5).json()["events"]
    assert (
        sum(e["method"] == "POST" and e["path"] == "/upload/youtube/v3/videos" for e in observed)
        == 1
    )


@pytest.mark.postgres
@pytest.mark.parametrize(
    "mode",
    [
        "publish_success",
        "lost_metadata_response",
        "lost_public_response",
        "metadata_error",
        "metadata_mismatch",
        "public_error",
        "publish_wrong_channel",
        "missing_edit_scope",
        "publication_lock",
        "publish_restricted",
        "publish_not_processed",
    ],
)
def test_six_language_publication_uses_existing_video_and_recovers(
    simulated_upload, pg_sessions, postgres_engine, mode
):
    from tsu.models import SystemSetting

    requests.post(BASE + "/__control", json={"mode": "success"}, timeout=5).raise_for_status()
    original, _, _ = simulated_upload
    assert (
        original.post("/api/youtube/test-upload", json={"confirm_private_test": True}).status_code
        == 200
    )
    requests.post(
        BASE + "/__control", json={"mode": mode, "existing": True}, timeout=5
    ).raise_for_status()
    if mode != "missing_edit_scope":
        with pg_sessions.begin() as db:
            account = db.scalar(select(SocialAccount))
            account.scopes = [*account.scopes, YOUTUBE_EDIT_SCOPE]
    settings = original.app.state.upload_settings

    def factory():
        http = UploadHTTP(
            UploadEndpoints(
                BASE + "/token", BASE + "/youtube/v3", BASE + "/upload/youtube/v3/videos"
            ),
            timeout=(1, 0.2),
        )
        return YouTubePublication(settings, postgres_engine, http)

    client = TestClient(
        create_app(
            settings,
            postgres_engine,
            youtube_publication_factory=factory,
            youtube_upload_factory=original.app.state.upload_factory,
        )
    )
    client.headers["Authorization"] = "Bearer " + TOKEN
    plan = client.get("/api/youtube/publication/plan").json()
    assert set(plan["languages"]) == set(LANGUAGES)
    assert plan["video_id"] == "testVideo01" and plan["default_language"] == "en"
    assert plan["edit_consent_granted"] == (mode != "missing_edit_scope")
    assert plan["new_upload"] is plan["scheduler_enabled"] is False
    current = client.get("/api/youtube/publication")
    if mode == "publish_wrong_channel":
        assert current.status_code == 409
    else:
        assert current.json()["privacy"] == "private"
    payload = {"confirm_publication": True}
    if mode == "publication_lock":
        with postgres_engine.connect() as lock:
            lock.execute(text("SELECT pg_advisory_lock(865190042)"))
            assert client.post("/api/youtube/publication", json=payload).status_code == 409
            lock.execute(text("SELECT pg_advisory_unlock(865190042)"))
    first = client.post("/api/youtube/publication", json=payload)
    permanent = mode in {
        "metadata_error",
        "metadata_mismatch",
        "public_error",
        "publish_wrong_channel",
        "missing_edit_scope",
        "publish_restricted",
        "publish_not_processed",
    }
    assert first.status_code == (200 if mode in {"publish_success", "publication_lock"} else 409), (
        first.text
    )
    second = client.post("/api/youtube/publication", json=payload)
    assert second.status_code == (409 if permanent else 200), second.text
    observed = requests.get(BASE + "/__control", timeout=5).json()["events"]
    assert not any(x["method"] == "POST" for x in observed)
    puts = [x for x in observed if x["method"] == "PUT"]
    if mode in {
        "missing_edit_scope",
        "publish_wrong_channel",
        "publish_restricted",
        "publish_not_processed",
    }:
        assert not puts
    if not permanent:
        data = second.json()
        assert data["status"] == "published_public" and data["translations_verified"]
        assert data["privacy"] == "public" and set(LANGUAGES).issubset(data["languages"])
        assert all(data["localizations"][k] == v for k, v in FIRST_VIDEO_LOCALIZATIONS.items())
        assert data["localizations"]["de"]["title"] == "Bestehender Titel"
        assert [x["part"] for x in puts] == ["snippet,localizations", "status"]
        assert puts[0]["body"]["snippet"]["categoryId"] == "28"
        assert puts[0]["body"]["snippet"]["tags"] == ["keep-tag"]
        assert "status" not in puts[0]["body"]
        assert puts[1]["body"]["status"]["embeddable"] is False
        assert puts[1]["body"]["status"]["publicStatsViewable"] is False
        old_endpoint = client.get("/api/youtube/test-upload")
        assert old_endpoint.status_code == 200 and old_endpoint.json()["privacy"] == "public"
        with pg_sessions() as db:
            pub = db.scalar(select(Publication))
            assert pub.status == "processed_public" and pub.published_at is not None
            assert db.get(SystemSetting, PUBLICATION_OPERATION).value["stage"] == "published_public"
    else:
        if mode not in {"public_error"}:
            assert not any(x["part"] == "status" for x in puts)
        with pg_sessions() as db:
            assert db.scalar(select(Publication)).published_at is None
    with pg_sessions() as db:
        assert db.scalar(select(func.count()).select_from(Publication)) == 1
        assert db.scalar(select(func.count()).select_from(ModelUsage)) == 0
        assert not db.scalar(select(SocialAccount)).approved_for_publication


def test_publication_routes_require_owner_and_explicit_fixed_plan(local_engine):
    client = TestClient(create_app(Settings(_env_file=None, admin_token=TOKEN), local_engine))
    for path in ("/api/youtube/publication", "/api/youtube/publication/plan"):
        assert client.get(path).status_code == 401
    assert (
        client.post("/api/youtube/publication", json={"confirm_publication": True}).status_code
        == 401
    )
    client.headers["Authorization"] = "Bearer " + TOKEN
    for body in (
        {},
        {"confirm_publication": False},
        {"confirm_publication": True, "video_id": "otherVideo1"},
    ):
        assert client.post("/api/youtube/publication", json=body).status_code == 422
