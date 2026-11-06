import json
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from urllib.parse import parse_qs, urlsplit

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from tsu.api import create_app
from tsu.config import Settings
from tsu.models import OAuthCredential, OAuthFlow, OwnerSession, SocialAccount, utcnow
from tsu.security import OWNER_COOKIE, digest
from tsu.youtube_auth import (
    YOUTUBE_CONNECTION_SCOPES,
    YOUTUBE_SCOPES,
    ChannelGrant,
    GoogleYouTubeClient,
)

PASSWORD = "unit-test-owner-password-over-32-characters"
CHANNEL_ID = "UC8DbuevZRxVTWxltG9oDFRw"
ORIGIN = "https://studio.technoinno.live"


class FakeGoogle:
    """Local security logic only. HTTP client verification is in a separate simulation."""

    calls = 0
    wrong_channel = False
    fail = False
    missing_edit = False

    def authorization_url(self, redirect_uri, state, verifier):
        from urllib.parse import urlencode

        self.state, self.verifier = state, verifier
        return "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode({"state": state})

    def exchange(self, code, redirect_uri, verifier, expected_channel_id):
        from tsu.youtube_auth import YouTubeConnectionError

        self.calls += 1
        assert verifier == self.verifier
        if self.fail:
            raise YouTubeConnectionError("Google connection failed safely.")
        return ChannelGrant(
            channel_id="UCother" if self.wrong_channel else CHANNEL_ID,
            handle="@techno-inno",
            scopes=list(YOUTUBE_SCOPES if self.missing_edit else YOUTUBE_CONNECTION_SCOPES),
            credentials_json=json.dumps(
                {"refresh_token": "fake-refresh-secret", "token": "fake-access"}
            ),
        )


def configured(**overrides):
    return Settings(
        _env_file=None,
        **{
            "admin_token": PASSWORD,
            "public_origin": ORIGIN,
            "youtube_client_id": "fake.apps.googleusercontent.com",
            "youtube_client_secret": "fake-secret",
            "youtube_channel_id": CHANNEL_ID,
            "token_encryption_key": Fernet.generate_key().decode(),
            **overrides,
        },
    )


def field(html, name="csrf"):
    return re.search(rf'name="{name}" value="([^"]+)"', html).group(1)


def sign_in(client):
    page = client.get("/login")
    response = client.post(
        "/login",
        data={"csrf": field(page.text), "password": PASSWORD},
        headers={"Origin": ORIGIN},
        follow_redirects=False,
    )
    assert response.status_code == 303
    return field(client.get("/admin").text)


@pytest.fixture
def oauth_app(local_engine):
    config, google = configured(), FakeGoogle()
    app = create_app(config, local_engine, google_client=google)
    with TestClient(app, base_url=ORIGIN) as client:
        yield client, app, config, google


def begin(client, csrf):
    response = client.post("/auth/youtube/start", data={"csrf": csrf}, follow_redirects=False)
    assert response.status_code == 303
    return parse_qs(urlsplit(response.headers["location"]).query)["state"][0]


def test_form_pages_preserve_origin_and_callback_suppresses_referrer(oauth_app):
    client, _, _, _ = oauth_app
    assert client.get("/login").headers["referrer-policy"] == "strict-origin"
    sign_in(client)
    assert client.get("/admin").headers["referrer-policy"] == "strict-origin"
    callback = client.get("/auth/youtube/callback", params={"state": "bad", "code": "fake"})
    assert callback.status_code == 400
    assert callback.headers["referrer-policy"] == "no-referrer"


@pytest.mark.parametrize("origin", ["null", "https://evil.example"])
def test_login_and_authenticated_forms_reject_untrusted_origins(oauth_app, origin):
    client, _, _, _ = oauth_app
    nonce = field(client.get("/login").text)
    response = client.post(
        "/login",
        data={"csrf": nonce, "password": PASSWORD},
        headers={"Origin": origin},
        follow_redirects=False,
    )
    assert response.status_code == 403
    csrf = sign_in(client)
    assert (
        client.post(
            "/auth/youtube/start", data={"csrf": csrf}, headers={"Origin": origin}
        ).status_code
        == 403
    )


def test_login_csrf_password_and_cookie_protection(oauth_app):
    client, app, _, _ = oauth_app
    assert client.post("/login", data={"password": PASSWORD, "csrf": "bad"}).status_code == 403
    nonce = field(client.get("/login").text)
    assert client.post("/login", data={"csrf": nonce, "password": "wrong"}).status_code == 401
    sign_in(client)
    cookie = client.cookies.get(OWNER_COOKIE)
    with app.state.sessions() as session:
        rows = session.scalars(select(OwnerSession)).all()
        assert len(rows) == 1 and rows[0].token_hash == digest(cookie)
        assert rows[0].token_hash != cookie
    assert (
        client.post(
            "/api/jobs", json={"concept": "Liquid"}, headers={"Idempotency-Key": "cookie"}
        ).status_code
        == 403
    )
    assert (
        client.post("/api/youtube/publication", json={"confirm_publication": True}).status_code
        == 403
    )
    csrf = field(client.get("/admin").text)
    assert (
        client.post(
            "/api/jobs",
            json={"concept": "Liquid"},
            headers={
                "Idempotency-Key": "cookie",
                "X-CSRF-Token": csrf,
                "Origin": ORIGIN,
            },
        ).status_code
        == 201
    )
    assert (
        client.post(
            "/auth/youtube/start", data={"csrf": csrf}, headers={"Origin": "https://evil.example"}
        ).status_code
        == 403
    )


def test_connection_is_encrypted_bound_to_channel_and_does_not_enable_publishing(oauth_app):
    client, app, config, google = oauth_app
    csrf = sign_in(client)
    state = begin(client, csrf)
    with app.state.sessions() as session:
        flow = session.scalar(select(OAuthFlow))
        assert flow.state_hash == digest(state)
        assert google.verifier not in flow.verifier_encrypted
    response = client.get(
        "/auth/youtube/callback",
        params={"state": state, "code": "fake-code"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert google.calls == 1
    with app.state.sessions() as session:
        account = session.scalar(select(SocialAccount))
        stored = session.get(OAuthCredential, account.id)
        assert not account.approved_for_publication
        assert "fake-refresh-secret" not in stored.credentials_encrypted
        plain = (
            Fernet(config.token_encryption_key.get_secret_value())
            .decrypt(stored.credentials_encrypted.encode())
            .decode()
        )
        assert json.loads(plain)["refresh_token"] == "fake-refresh-secret"
    status = client.get("/api/youtube/status").json()
    assert status["connected"] and not status["publishing_enabled"]
    assert "fake-refresh-secret" not in json.dumps(status)
    replay = client.get("/auth/youtube/callback", params={"state": state, "code": "fake-code"})
    assert replay.status_code == 400 and google.calls == 1


@pytest.mark.parametrize("failure", ["wrong_channel", "provider_failure", "denial", "expired"])
def test_failures_do_not_store_credentials(oauth_app, failure):
    client, app, _, google = oauth_app
    state = begin(client, sign_in(client))
    google.wrong_channel = failure == "wrong_channel"
    google.fail = failure == "provider_failure"
    if failure == "expired":
        with app.state.sessions.begin() as session:
            row = session.get(OAuthFlow, digest(state))
            row.expires_at = utcnow() - timedelta(seconds=1)
    params = {"state": state, "code": "fake-code"}
    if failure == "denial":
        params = {"state": state, "error": "access_denied"}
    response = client.get("/auth/youtube/callback", params=params)
    assert response.status_code == 400
    with app.state.sessions() as session:
        assert session.scalar(select(func.count()).select_from(OAuthCredential)) == 0
    if failure in ("expired", "denial"):
        assert google.calls == 0


def test_state_is_bound_to_same_browser_and_logout_removes_access(oauth_app):
    client, app, _, google = oauth_app
    state = begin(client, sign_in(client))
    with TestClient(app, base_url=ORIGIN) as other:
        sign_in(other)
        assert (
            other.get("/auth/youtube/callback", params={"state": state, "code": "fake"}).status_code
            == 400
        )
    assert google.calls == 0
    csrf = field(client.get("/admin").text)
    assert client.post("/logout", data={"csrf": csrf}, follow_redirects=False).status_code == 303
    assert client.get("/api/youtube/status").status_code == 401


def test_google_authorization_url_uses_exact_redirect_pkce_offline_and_required_scopes():
    config = configured()
    url = GoogleYouTubeClient(config).authorization_url(
        f"{ORIGIN}/auth/youtube/callback", "test-state", "v" * 64
    )
    parsed = urlsplit(url)
    query = parse_qs(parsed.query)
    assert parsed.netloc == "accounts.google.com"
    assert query["redirect_uri"] == [f"{ORIGIN}/auth/youtube/callback"]
    assert query["access_type"] == ["offline"]
    assert query["code_challenge_method"] == ["S256"]
    assert query["state"] == ["test-state"]
    assert set(query["scope"][0].split()) == set(YOUTUBE_CONNECTION_SCOPES)
    assert query["include_granted_scopes"] == ["true"]


def test_expired_owner_session_requires_new_signin(oauth_app):
    client, app, _, _ = oauth_app
    sign_in(client)
    with app.state.sessions.begin() as session:
        row = session.scalar(select(OwnerSession))
        row.expires_at = utcnow() - timedelta(seconds=1)
    assert client.get("/admin").status_code == 401
    browser = client.get("/admin", headers={"Accept": "text/html"}, follow_redirects=False)
    assert browser.status_code == 303 and browser.headers["location"] == "/login"
    assert client.get("/api/overview", headers={"Accept": "text/html"}).status_code == 401


def test_rotating_admin_password_invalidates_existing_browser_session(oauth_app):
    from pydantic import SecretStr

    client, _, config, _ = oauth_app
    sign_in(client)
    config.admin_token = SecretStr("new-owner-password-with-at-least-32-characters")
    assert client.get("/admin").status_code == 401


@pytest.mark.parametrize("failure", ["network", "partial_edit_consent"])
def test_failed_reconnect_preserves_previously_saved_credentials(oauth_app, failure):
    client, app, _, google = oauth_app
    csrf = sign_in(client)
    state = begin(client, csrf)
    assert (
        client.get(
            "/auth/youtube/callback",
            params={"state": state, "code": "fake1"},
            follow_redirects=False,
        ).status_code
        == 303
    )
    with app.state.sessions() as session:
        previous = session.scalar(select(OAuthCredential.credentials_encrypted))
    google.fail = failure == "network"
    google.missing_edit = failure == "partial_edit_consent"
    state = begin(client, csrf)
    assert (
        client.get("/auth/youtube/callback", params={"state": state, "code": "fake2"}).status_code
        == 400
    )
    with app.state.sessions() as session:
        assert session.scalar(select(OAuthCredential.credentials_encrypted)) == previous


@pytest.mark.postgres
def test_concurrent_callbacks_exchange_a_code_only_once(pg_sessions):
    from tsu.youtube_auth import YouTubeConnectionError, YouTubeConnections

    config, google = configured(), FakeGoogle()
    with pg_sessions.begin() as session:
        session.add(
            OwnerSession(
                token_hash=digest("concurrent-owner"), expires_at=utcnow() + timedelta(hours=1)
            )
        )
    connections = YouTubeConnections(config, pg_sessions, google)
    url = connections.start(digest("concurrent-owner"))
    state = parse_qs(urlsplit(url).query)["state"][0]

    def complete(_):
        try:
            connections.complete(digest("concurrent-owner"), state, "fake-code")
            return True
        except YouTubeConnectionError:
            return False

    with ThreadPoolExecutor(max_workers=2) as executor:
        assert sum(executor.map(complete, range(2))) == 1
    assert google.calls == 1
