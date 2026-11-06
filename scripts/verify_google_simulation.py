"""Run only against the local Postman HTTP stand-in. Fake Google credentials only."""

import json
import os
import secrets
import sys
import tempfile
from datetime import timedelta
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import requests  # noqa: E402
from cryptography.fernet import Fernet  # noqa: E402
from sqlalchemy import func, select  # noqa: E402

from tsu.config import Settings  # noqa: E402
from tsu.db import Base, make_engine, make_sessions  # noqa: E402
from tsu.models import OAuthCredential, OwnerSession, utcnow  # noqa: E402
from tsu.security import digest  # noqa: E402
from tsu.youtube_auth import (  # noqa: E402
    GoogleEndpoints,
    GoogleYouTubeClient,
    YouTubeConnectionError,
    YouTubeConnections,
)

base = os.environ.get("TSU_SIMULATION_BASE", "http://127.0.0.1:4010/google-youtube")
assert urlsplit(base).scheme == "http" and urlsplit(base).hostname == "127.0.0.1"
# Applies only to this synthetic test process; production keeps OAuth HTTPS enforcement.
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
control = f"{base}/__control"
results = []

for mode in (
    "success",
    "wrong_channel",
    "no_refresh",
    "missing_scope",
    "missing_edit_scope",
    "token_failure",
    "server_error",
    "channel_failure",
    "empty_channel",
    "timeout",
):
    response = requests.post(control, json={"mode": mode}, timeout=5)
    assert response.headers.get("X-TSU-Mock") == "google-youtube", "Mock interception is required"
    response.raise_for_status()
    with tempfile.TemporaryDirectory(prefix="tsu-oauth-simulation-") as directory:
        engine = make_engine(f"sqlite:///{directory}/simulation.db")
        Base.metadata.create_all(engine)
        sessions = make_sessions(engine)
        owner_hash = digest("synthetic-simulation-owner")
        with sessions.begin() as session:
            session.add(
                OwnerSession(token_hash=owner_hash, expires_at=utcnow() + timedelta(hours=1))
            )
        settings = Settings(
            _env_file=None,
            public_origin="https://studio.technoinno.live",
            youtube_client_id="fake.apps.googleusercontent.com",
            youtube_client_secret="fake-secret",
            youtube_channel_id="UC8DbuevZRxVTWxltG9oDFRw",
            token_encryption_key=Fernet.generate_key().decode(),
        )
        client = GoogleYouTubeClient(
            settings,
            http_timeout=(1, 0.2) if mode == "timeout" else (5, 10),
            endpoints=GoogleEndpoints(
                token=f"{base}/token", channels=f"{base}/youtube/v3/channels"
            ),
        )
        connections = YouTubeConnections(settings, sessions, client)
        auth_url = connections.start(owner_hash)
        state = parse_qs(urlsplit(auth_url).query)["state"][0]
        error = None
        try:
            connections.complete(owner_hash, state, f"synthetic-code-{mode}-{secrets.token_hex(8)}")
        except YouTubeConnectionError as failure:
            error = str(failure)
        with sessions() as session:
            count = session.scalar(select(func.count()).select_from(OAuthCredential))
        assert (count == 1 and error is None) if mode == "success" else (count == 0 and error)
        observed = requests.get(control, timeout=5).json()["events"]
        assert observed and observed[0]["operation"] == "token"
        assert {
            "client_id",
            "client_secret",
            "code",
            "code_verifier",
            "grant_type",
            "redirect_uri",
        } <= set(observed[0]["fields"])
        expected_channels = mode in ("success", "wrong_channel", "channel_failure", "empty_channel")
        assert any(event["operation"] == "channels" for event in observed) == expected_channels
        results.append(
            {
                "scenario": mode,
                "passed": True,
                "credentials_saved": count,
                "operations": [event["operation"] for event in observed],
            }
        )
        engine.dispose()
    print(f"{mode}: passed")

destination = (
    Path(__file__).resolve().parents[1]
    / "docs/evidence/google-oauth-edit-simulation-2026-11-05.json"
)
destination.write_text(
    json.dumps(
        {
            "date": "2026-11-05",
            "environment": "local Postman HTTP stand-in on loopback",
            "real_google_consent": False,
            "scenarios": results,
        },
        indent=2,
    )
    + "\n"
)
print(f"{len(results)} HTTP simulation scenarios passed; no real Google grant or upload.")
