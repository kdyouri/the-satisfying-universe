import hashlib
import hmac
import secrets
import time
from dataclasses import dataclass
from datetime import timedelta
from urllib.parse import parse_qs

from fastapi import HTTPException, Request
from sqlalchemy import delete, select

from tsu.models import OAuthFlow, OwnerSession, utcnow

OWNER_COOKIE = "__Host-tsu_owner"
LOGIN_COOKIE = "__Host-tsu_login"


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def constant_equal(first: str, second: str) -> bool:
    return secrets.compare_digest(first.encode(), second.encode())


def csrf_for(raw_session: str, admin_secret: str) -> str:
    return hmac.new(
        admin_secret.encode(), f"csrf:{raw_session}".encode(), hashlib.sha256
    ).hexdigest()


async def read_form(request: Request) -> dict[str, str]:
    if request.headers.get("content-type", "").split(";")[0] != "application/x-www-form-urlencoded":
        raise HTTPException(415, "Form encoding required")
    body = await request.body()
    if len(body) > 4096:
        raise HTTPException(413, "Form is too large")
    try:
        values = parse_qs(body.decode(), max_num_fields=6, keep_blank_values=True)
    except (UnicodeError, ValueError):
        raise HTTPException(400, "Invalid form") from None
    if any(len(value) != 1 for value in values.values()):
        raise HTTPException(400, "Duplicate form fields are not allowed")
    return {key: value[0] for key, value in values.items()}


def new_login_nonce(admin_secret: str) -> str:
    value = f"{int(time.time())}:{secrets.token_urlsafe(24)}"
    signature = hmac.new(admin_secret.encode(), value.encode(), hashlib.sha256).hexdigest()
    return f"{value}:{signature}"


def valid_login_nonce(value: str, admin_secret: str) -> bool:
    try:
        timestamp, nonce, signature = value.split(":")
        age = time.time() - int(timestamp)
    except (ValueError, TypeError):
        return False
    expected = hmac.new(
        admin_secret.encode(), f"{timestamp}:{nonce}".encode(), hashlib.sha256
    ).hexdigest()
    return 0 <= age <= 600 and constant_equal(signature, expected)


@dataclass(frozen=True)
class OwnerIdentity:
    session_hash: str | None
    csrf: str


class OwnerAccess:
    def __init__(self, settings, sessions):
        self.settings = settings
        self.sessions = sessions

    async def __call__(self, request: Request) -> OwnerIdentity:
        secret = self.settings.admin_token.get_secret_value()
        if not secret:
            raise HTTPException(503, "Administrative access is not configured")
        authorization = request.headers.get("authorization", "")
        if authorization:
            scheme, _, value = authorization.partition(" ")
            if scheme.lower() != "bearer" or not constant_equal(value, secret):
                raise HTTPException(
                    401, "Valid admin bearer token required", headers={"WWW-Authenticate": "Bearer"}
                )
            return OwnerIdentity(None, "")
        raw = request.cookies.get(OWNER_COOKIE, "")
        if not raw:
            raise HTTPException(
                401, "Owner sign-in required", headers={"WWW-Authenticate": "Bearer"}
            )
        with self.sessions() as session:
            owner = session.scalar(
                select(OwnerSession).where(
                    OwnerSession.token_hash == digest(raw),
                    OwnerSession.secret_version == digest(secret),
                    OwnerSession.expires_at > utcnow(),
                )
            )
        if owner is None:
            raise HTTPException(401, "Owner session expired; sign in again")
        csrf = csrf_for(raw, secret)
        if request.method not in ("GET", "HEAD", "OPTIONS"):
            origin = request.headers.get("origin")
            if origin and origin != self.settings.public_origin:
                raise HTTPException(403, "Request origin is not allowed")
            supplied = request.headers.get("x-csrf-token", "")
            if not supplied and request.headers.get("content-type", "").startswith(
                "application/x-www-form-urlencoded"
            ):
                supplied = (await read_form(request)).get("csrf", "")
            if not supplied or not constant_equal(supplied, csrf):
                raise HTTPException(403, "CSRF validation failed")
        return OwnerIdentity(owner.token_hash, csrf)

    def create_session(self) -> str:
        raw = secrets.token_urlsafe(48)
        with self.sessions.begin() as session:
            session.add(
                OwnerSession(
                    token_hash=digest(raw),
                    secret_version=digest(self.settings.admin_token.get_secret_value()),
                    expires_at=utcnow() + timedelta(hours=8),
                )
            )
        return raw

    def delete_session(self, session_hash: str) -> None:
        with self.sessions.begin() as session:
            session.execute(delete(OAuthFlow).where(OAuthFlow.owner_session_hash == session_hash))
            session.execute(delete(OwnerSession).where(OwnerSession.token_hash == session_hash))
