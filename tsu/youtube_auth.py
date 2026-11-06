import secrets
from dataclasses import dataclass
from datetime import timedelta

from cryptography.fernet import Fernet, InvalidToken
from google_auth_oauthlib.flow import Flow
from sqlalchemy import select, update

from tsu.models import OAuthCredential, OAuthFlow, SocialAccount, utcnow
from tsu.security import digest

YOUTUBE_SCOPES = (
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
)
YOUTUBE_EDIT_SCOPE = "https://www.googleapis.com/auth/youtube.force-ssl"
YOUTUBE_CONNECTION_SCOPES = (*YOUTUBE_SCOPES, YOUTUBE_EDIT_SCOPE)


class YouTubeConnectionError(ValueError):
    """Safe user-facing message only; upstream errors may contain secrets."""


@dataclass(frozen=True)
class ChannelGrant:
    channel_id: str
    handle: str
    credentials_json: str
    scopes: list[str]


@dataclass(frozen=True)
class GoogleEndpoints:
    # The application always uses these defaults. Explicit internal injection permits
    # local HTTP simulations without changing production configuration or TLS settings.
    token: str = "https://oauth2.googleapis.com/token"
    channels: str = "https://www.googleapis.com/youtube/v3/channels"


class GoogleYouTubeClient:
    def __init__(self, settings, http_timeout=(5, 15), endpoints: GoogleEndpoints | None = None):
        self.settings = settings
        self.http_timeout = http_timeout
        self.endpoints = endpoints or GoogleEndpoints()

    def _flow(self, redirect_uri: str, verifier: str) -> Flow:
        return Flow.from_client_config(
            {
                "web": {
                    "client_id": self.settings.youtube_client_id.get_secret_value(),
                    "client_secret": self.settings.youtube_client_secret.get_secret_value(),
                    "auth_uri": "https://accounts.google.com/o/oauth2/v2/auth",
                    "token_uri": self.endpoints.token,
                    "redirect_uris": [redirect_uri],
                }
            },
            scopes=list(YOUTUBE_CONNECTION_SCOPES),
            redirect_uri=redirect_uri,
            code_verifier=verifier,
            autogenerate_code_verifier=False,
        )

    def authorization_url(self, redirect_uri: str, state: str, verifier: str) -> str:
        flow = self._flow(redirect_uri, verifier)
        url, _ = flow.authorization_url(
            state=state,
            access_type="offline",
            prompt="consent select_account",
            login_hint=self.settings.youtube_login_hint,
            include_granted_scopes="true",
        )
        return url

    def exchange(
        self, code: str, redirect_uri: str, verifier: str, expected_channel_id: str
    ) -> ChannelGrant:
        flow = self._flow(redirect_uri, verifier)
        try:
            flow.fetch_token(code=code, timeout=self.http_timeout, include_client_id=True)
            raw_scopes = flow.oauth2session.token.get("scope", list(YOUTUBE_CONNECTION_SCOPES))
            granted = raw_scopes.split() if isinstance(raw_scopes, str) else raw_scopes
            if not set(YOUTUBE_CONNECTION_SCOPES).issubset(granted):
                raise YouTubeConnectionError(
                    "Google did not grant the required YouTube permissions."
                )
            credentials = flow.credentials
            if not credentials.refresh_token:
                raise YouTubeConnectionError(
                    "Offline access was not granted. Reconnect with consent."
                )
            with flow.authorized_session() as authorized:
                response = authorized.get(
                    self.endpoints.channels,
                    params={"part": "snippet", "mine": "true"},
                    timeout=self.http_timeout,
                )
                response.raise_for_status()
                channels = response.json().get("items", [])
            match = next((item for item in channels if item.get("id") == expected_channel_id), None)
            if match is None:
                raise YouTubeConnectionError(
                    "The selected Google/YouTube account is not the configured TechnoInno channel."
                )
            return ChannelGrant(
                channel_id=expected_channel_id,
                handle=match.get("snippet", {}).get("customUrl") or self.settings.youtube_handle,
                credentials_json=credentials.to_json(),
                scopes=list(granted),
            )
        except YouTubeConnectionError:
            raise
        except Exception:
            # Do not expose exception text: it can contain authorization codes or tokens.
            raise YouTubeConnectionError(
                "Google could not complete the connection. "
                "Check API access and try connecting again."
            ) from None


class YouTubeConnections:
    def __init__(self, settings, sessions, client=None):
        self.settings = settings
        self.sessions = sessions
        self.client = client or GoogleYouTubeClient(settings)

    def cipher(self) -> Fernet:
        try:
            return Fernet(self.settings.token_encryption_key.get_secret_value().encode())
        except (ValueError, TypeError):
            raise YouTubeConnectionError("Secure credential storage is not configured.") from None

    def start(self, owner_session_hash: str | None) -> str:
        if not owner_session_hash:
            raise YouTubeConnectionError("Sign in through the owner login page to connect YouTube.")
        if not self.settings.gates()["youtube_oauth_configured"]:
            raise YouTubeConnectionError("YouTube OAuth configuration is incomplete.")
        state = secrets.token_urlsafe(40)
        verifier = secrets.token_urlsafe(64)
        redirect_uri = f"{self.settings.public_origin}/auth/youtube/callback"
        cipher = self.cipher()
        with self.sessions.begin() as session:
            session.add(
                OAuthFlow(
                    state_hash=digest(state),
                    owner_session_hash=owner_session_hash,
                    verifier_encrypted=cipher.encrypt(verifier.encode()).decode(),
                    expected_channel_id=self.settings.youtube_channel_id,
                    redirect_uri=redirect_uri,
                    expires_at=utcnow() + timedelta(minutes=10),
                )
            )
        return self.client.authorization_url(redirect_uri, state, verifier)

    def complete(
        self, owner_session_hash: str | None, state: str, code: str | None, denied: bool = False
    ) -> None:
        if not owner_session_hash or not state:
            raise YouTubeConnectionError("The YouTube connection session is missing or invalid.")
        # Atomic compare/update consumes the state before any token request, including denials.
        with self.sessions.begin() as session:
            row = session.execute(
                update(OAuthFlow)
                .where(
                    OAuthFlow.state_hash == digest(state),
                    OAuthFlow.owner_session_hash == owner_session_hash,
                    OAuthFlow.expires_at > utcnow(),
                    OAuthFlow.consumed_at.is_(None),
                )
                .values(consumed_at=utcnow())
                .returning(
                    OAuthFlow.verifier_encrypted,
                    OAuthFlow.expected_channel_id,
                    OAuthFlow.redirect_uri,
                )
            ).first()
        if row is None:
            raise YouTubeConnectionError("The YouTube connection link expired or was already used.")
        if denied:
            raise YouTubeConnectionError(
                "Google authorization was cancelled. No connection was saved."
            )
        if not code or len(code) > 4096:
            raise YouTubeConnectionError("Google did not return a valid authorization code.")
        if row.expected_channel_id != self.settings.youtube_channel_id:
            raise YouTubeConnectionError("The configured channel changed; start a new connection.")
        cipher = self.cipher()
        try:
            verifier = cipher.decrypt(row.verifier_encrypted.encode()).decode()
        except InvalidToken:
            raise YouTubeConnectionError(
                "Secure storage configuration changed. Start a new YouTube connection."
            ) from None
        grant = self.client.exchange(code, row.redirect_uri, verifier, row.expected_channel_id)
        if grant.channel_id != row.expected_channel_id or not set(
            YOUTUBE_CONNECTION_SCOPES
        ).issubset(grant.scopes):
            raise YouTubeConnectionError("The returned channel or permission grant is invalid.")
        encrypted = cipher.encrypt(grant.credentials_json.encode()).decode()
        with self.sessions.begin() as session:
            account = session.scalar(
                select(SocialAccount)
                .where(
                    SocialAccount.platform == "youtube",
                    SocialAccount.external_id == grant.channel_id,
                )
                .with_for_update()
            )
            if account is None:
                account = SocialAccount(
                    platform="youtube",
                    external_id=grant.channel_id,
                    handle=grant.handle,
                    scopes=grant.scopes,
                    secret_reference=f"oauth:youtube:{grant.channel_id}",
                    approved_for_publication=False,
                )
                session.add(account)
                session.flush()
            account.handle = grant.handle
            account.scopes = grant.scopes
            account.approved_for_publication = False
            stored = session.get(OAuthCredential, account.id)
            if stored is None:
                session.add(OAuthCredential(account_id=account.id, credentials_encrypted=encrypted))
            else:
                stored.credentials_encrypted = encrypted
                stored.updated_at = utcnow()

    def status(self) -> dict:
        with self.sessions() as session:
            account = session.scalar(
                select(SocialAccount).where(
                    SocialAccount.platform == "youtube",
                    SocialAccount.external_id == self.settings.youtube_channel_id,
                )
            )
            credential = session.get(OAuthCredential, account.id) if account else None
            return {
                "connected": bool(credential),
                "expected_handle": self.settings.youtube_handle,
                "channel_id": self.settings.youtube_channel_id,
                "handle": account.handle if account else None,
                "publishing_enabled": False,
                "private_test_upload_available": bool(credential),
                "metadata_edit_authorized": bool(
                    credential and YOUTUBE_EDIT_SCOPE in account.scopes
                ),
                "reason": "Manual publication needs edit consent; recurring publishing is off.",
            }
