"""One owner-requested private upload, with durable resumable transfer and no scheduler."""

import hashlib
import json
import re
import subprocess
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, urlsplit

import requests
from sqlalchemy import select, text, update

from tsu.db import make_sessions
from tsu.media import inspect_final
from tsu.models import (
    OAuthCredential,
    ProductionJob,
    Publication,
    SocialAccount,
    SystemSetting,
    Video,
    VideoGeneration,
    utcnow,
)
from tsu.youtube_auth import YOUTUBE_SCOPES, YouTubeConnectionError, YouTubeConnections
from tsu.youtube_metadata import PUBLICATION_OPERATION

OPERATION = "youtube:private-test:balanced-audio-v2:first-video"
METADATA = {
    "snippet": {
        "title": "Cette spirale dorée est hypnotisante ✨",
        "description": (
            "Un mouvement lent, une texture dorée, quelques secondes pour souffler.\n\n"
            "Création visuelle générée avec une IA pour TechnoInno. Musique originale.\n\n"
            "#Shorts #Satisfying #OddlySatisfying #TechnoInno"
        ),
        "tags": ["satisfying", "relaxation", "TechnoInno", "shorts"],
        "categoryId": "24",
        "defaultLanguage": "fr",
    },
    "status": {
        "privacyStatus": "private",
        "selfDeclaredMadeForKids": False,
        "containsSyntheticMedia": True,
    },
}


class UploadError(RuntimeError):
    """Safe message only. Never expose Google bodies, tokens or session URLs."""


@dataclass(frozen=True)
class UploadEndpoints:
    token: str = "https://oauth2.googleapis.com/token"
    api: str = "https://www.googleapis.com/youtube/v3"
    start: str = "https://www.googleapis.com/upload/youtube/v3/videos"


class UploadHTTP:
    def __init__(self, endpoints=None, timeout=(10, 60), chunk_size=1024 * 1024):
        self.endpoints = endpoints or UploadEndpoints()
        defaults = UploadEndpoints()
        for name in ("token", "api", "start"):
            value = getattr(self.endpoints, name)
            parsed = urlsplit(value)
            if value != getattr(defaults, name) and not (
                parsed.scheme == "http" and parsed.hostname == "127.0.0.1"
            ):
                raise ValueError("Only official Google or loopback simulation URLs are allowed")
        if chunk_size < 262144 or chunk_size % 262144:
            raise ValueError("Use multiples of 256 KiB for upload chunks")
        self.chunk_size, self.timeout = chunk_size, timeout
        self.session, self.token = requests.Session(), None

    def request(self, method, url, *, authenticated=True, **kwargs):
        headers = kwargs.pop("headers", {})
        if authenticated:
            headers["Authorization"] = f"Bearer {self.token}"
        try:
            return self.session.request(
                method, url, headers=headers, timeout=self.timeout, allow_redirects=False, **kwargs
            )
        except requests.RequestException:
            raise UploadError("Google connection interrupted; reconcile the saved upload") from None

    @staticmethod
    def data(response):
        if response.status_code not in (200, 201):
            reason = ""
            try:
                value = response.json()["error"]["errors"][0]["reason"]
                if isinstance(value, str) and re.fullmatch(r"[A-Za-z_]{1,80}", value):
                    reason = f" ({value})"
            except (ValueError, KeyError, IndexError, TypeError):
                pass
            raise UploadError(f"Google HTTP {response.status_code}{reason}")
        try:
            value = response.json()
            if not isinstance(value, dict) or "error" in value:
                raise ValueError
            return value
        except ValueError:
            raise UploadError(
                "Google returned an invalid response; reconcile saved state"
            ) from None

    def session_url(self, value):
        expected, actual = urlsplit(self.endpoints.start), urlsplit(value)
        if not (
            actual.scheme == expected.scheme
            and actual.netloc == expected.netloc
            and actual.path == expected.path
            and not actual.fragment
            and not actual.username
            and not actual.password
            and parse_qs(actual.query).get("upload_id")
            and len(value) <= 8192
        ):
            raise UploadError("Untrusted upload session URL; no video or credential was sent")
        return value


@contextmanager
def upload_lock(engine):
    if engine.dialect.name != "postgresql":
        raise UploadError("Live upload state requires PostgreSQL")
    with engine.connect() as connection:
        if not connection.scalar(text("SELECT pg_try_advisory_lock(865190042)")):
            raise UploadError("This private upload is already active")
        try:
            yield
        finally:
            connection.execute(text("SELECT pg_advisory_unlock(865190042)"))


class PrivateTestUpload:
    operation_key = OPERATION
    public_operation_key = PUBLICATION_OPERATION
    metadata = METADATA
    source_job_key = "owner:first-video:v1"
    asset_label = "first_video_balanced_audio_v2"

    def __init__(self, settings, engine, http=None, asset=None):
        self.settings, self.engine = settings, engine
        self.sessions = make_sessions(engine)
        self.http = http or UploadHTTP()
        self.asset = asset or settings.data_root / "pilot/first-video/preview-balanced-audio-v2.mp4"
        self._cipher = None

    @property
    def cipher(self):
        if self._cipher is None:
            try:
                self._cipher = YouTubeConnections(self.settings, self.sessions).cipher()
            except YouTubeConnectionError:
                raise UploadError("Secure Google credential storage is not configured") from None
        return self._cipher

    def close(self):
        self.http.session.close()

    def plan(self):
        if not self.asset.is_file() or not 0 < self.asset.stat().st_size <= 100 * 1024 * 1024:
            raise UploadError("The sonorized preview is missing or exceeds the test size limit")
        try:
            self.technical = self.inspect_asset()
        except (subprocess.SubprocessError, ValueError, KeyError):
            raise UploadError("The video file cannot be decoded; no upload started") from None
        if not self.technical["technical_pass"]:
            raise UploadError("The preview does not pass technical/audio checks")
        with self.asset.open("rb") as media:
            digest = hashlib.file_digest(media, "sha256").hexdigest()
        return {
            "asset": self.asset_label,
            "sha256": digest,
            "bytes": self.asset.stat().st_size,
            "channel_id": self.settings.youtube_channel_id,
            "duration_seconds": float(self.technical["metadata"]["format"]["duration"]),
            "metadata": self.metadata,
            "notify_subscribers": False,
            "scheduler_enabled": False,
            "public_publishing": False,
        }

    def inspect_asset(self):
        return inspect_final(self.asset, require_audio=True)

    def authorize(self):
        with self.sessions() as db:
            account = db.scalar(
                select(SocialAccount).where(
                    SocialAccount.platform == "youtube",
                    SocialAccount.external_id == self.settings.youtube_channel_id,
                )
            )
            credential = db.get(OAuthCredential, account.id) if account else None
            if not credential or not set(YOUTUBE_SCOPES).issubset(account.scopes):
                raise UploadError("Connect the expected YouTube channel with upload permission")
            original, account_id = credential.credentials_encrypted, account.id
        try:
            raw = json.loads(self.cipher.decrypt(original.encode()))
            if raw["client_id"] != self.settings.youtube_client_id.get_secret_value():
                raise ValueError
            expires = datetime.fromisoformat(
                raw.get("expiry", "1970-01-01T00:00:00Z").replace("Z", "+00:00")
            )
            if expires.tzinfo is None:
                expires = expires.replace(tzinfo=UTC)
        except Exception:
            raise UploadError("Saved Google grant is invalid; reconnect YouTube") from None
        if not raw.get("token") or expires < utcnow() + timedelta(seconds=90):
            result = self.http.data(
                self.http.request(
                    "POST",
                    self.http.endpoints.token,
                    authenticated=False,
                    data={
                        "grant_type": "refresh_token",
                        "refresh_token": raw["refresh_token"],
                        "client_id": raw["client_id"],
                        "client_secret": self.settings.youtube_client_secret.get_secret_value(),
                    },
                )
            )
            if not isinstance(result.get("access_token"), str) or not result["access_token"]:
                raise UploadError("Google did not return an access token; reconnect YouTube")
            raw.update(
                token=result["access_token"],
                expiry=(
                    utcnow() + timedelta(seconds=int(result.get("expires_in", 3600)))
                ).isoformat(),
            )
            if result.get("refresh_token"):
                raw["refresh_token"] = result["refresh_token"]
            with self.sessions.begin() as db:
                changed = db.execute(
                    update(OAuthCredential)
                    .where(
                        OAuthCredential.account_id == account_id,
                        OAuthCredential.credentials_encrypted == original,
                    )
                    .values(
                        credentials_encrypted=self.cipher.encrypt(
                            json.dumps(raw).encode()
                        ).decode(),
                        updated_at=utcnow(),
                    )
                ).rowcount
                if changed != 1:
                    raise UploadError(
                        "Google connection changed during refresh; retry verification"
                    )
        self.http.token = raw["token"]
        result = self.http.data(
            self.http.request(
                "GET",
                self.http.endpoints.api + "/channels",
                params={"part": "snippet", "mine": "true"},
            )
        )
        if not any(
            c.get("id") == self.settings.youtube_channel_id for c in result.get("items", [])
        ):
            raise UploadError("Google access is not for the expected TechnoInno channel")
        self.account_id = account_id

    def snapshot(self):
        with self.sessions() as db:
            state = db.get(SystemSetting, self.operation_key)
            if not state:
                return {"status": "not_uploaded", "privacy": "private", "url": None}
            pub = db.get(Publication, state.value["publication_id"])
            public = db.get(SystemSetting, self.public_operation_key)
            public_requested = bool(
                public
                and public.value.get("public_requested")
                and public.value.get("publication_id") == pub.id
                and public.value.get("video_id") == pub.remote_id
            )
            return {
                "publication_id": pub.id,
                "video_id": pub.remote_id,
                "status": pub.status,
                "privacy": state.value.get("verified", {}).get("privacy"),
                "requested_privacy": "public" if public_requested else "private",
                "url": pub.url,
                "last_error": pub.last_error,
                "verified": state.value.get("verified"),
                "sha256": state.value["plan"]["sha256"],
            }

    def record_completion(self, resource):
        remote_id = resource.get("id", "")
        if not isinstance(remote_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{11}", remote_id):
            raise UploadError("Upload completed without a valid video ID; retain the session")
        with self.sessions.begin() as db:
            state = db.get(SystemSetting, self.operation_key)
            pub = db.get(Publication, state.value["publication_id"])
            if pub.remote_id and pub.remote_id != remote_id:
                raise UploadError("Upload session returned a different video ID; stop")
            pub.remote_id, pub.url = remote_id, f"https://www.youtube.com/watch?v={remote_id}"
            pub.status, pub.last_error = "uploaded_unverified", None

    def reconcile(self):
        current = self.snapshot()
        if not current.get("video_id"):
            return current
        self.authorize()
        result = self.http.data(
            self.http.request(
                "GET",
                self.http.endpoints.api + "/videos",
                params={
                    "part": "snippet,status,contentDetails,processingDetails",
                    "id": current["video_id"],
                },
            )
        )
        item = next(
            (x for x in result.get("items", []) if x.get("id") == current["video_id"]), None
        )
        if not item:
            raise UploadError(
                "Known uploaded video is not yet visible to its owner; do not reupload"
            )
        if item.get("snippet", {}).get("channelId") != self.settings.youtube_channel_id:
            raise UploadError("The uploaded video's channel does not match TechnoInno")
        status = item.get("status", {})
        privacy = status.get("privacyStatus")
        if privacy != "private" and not (
            privacy == "public" and current["requested_privacy"] == "public"
        ):
            raise UploadError("Unexpected video visibility; owner attention required")
        processing = item.get("processingDetails", {}).get("processingStatus")
        verified = {
            "channel_id": item["snippet"]["channelId"],
            "privacy": status["privacyStatus"],
            "title": item["snippet"].get("title"),
            "upload_status": status.get("uploadStatus"),
            "processing_status": processing,
            "duration": item.get("contentDetails", {}).get("duration"),
            "definition": item.get("contentDetails", {}).get("definition"),
            "synthetic_media": status.get("containsSyntheticMedia"),
        }
        failed = processing == "failed" or status.get("uploadStatus") in (
            "failed",
            "rejected",
            "deleted",
        )
        state_name = (
            "processing_failed"
            if failed
            else (
                f"processed_{privacy}"
                if processing == "succeeded"
                or (
                    status.get("uploadStatus") == "processed" and processing in (None, "terminated")
                )
                else f"processing_{privacy}"
            )
        )
        with self.sessions.begin() as db:
            state = db.get(SystemSetting, self.operation_key)
            state.value = {**state.value, "verified": verified}
            pub = db.get(Publication, state.value["publication_id"])
            pub.status, pub.last_error = state_name, None
        return self.snapshot()

    def progress(self, response, size):
        if response.status_code in (200, 201):
            self.record_completion(self.http.data(response))
            return None
        if response.status_code != 308:
            self.http.data(response)
        header = response.headers.get("Range")
        if not header:
            return 0
        match = re.fullmatch(r"(?:bytes=)?0-(\d+)", header)
        if not match or not 0 <= int(match[1]) < size:
            raise UploadError("Invalid Google progress range; retain the saved session")
        return int(match[1]) + 1

    def video_record(self, db, source, plan):
        return Video(
            concept_id=source.concept_id,
            generation_id=source.id,
            original_key=str(self.asset),
            final_key=str(self.asset),
            sha256=plan["sha256"],
            technical_metadata={
                **self.technical,
                "owner_authorization": (
                    "Explicit one private upload test; not public quality approval"
                ),
            },
            status="owner_private_upload_test",
        )

    def upload(self):
        with upload_lock(self.engine):
            plan = self.plan()
            self.authorize()
            with self.sessions.begin() as db:
                state = db.get(SystemSetting, self.operation_key, with_for_update=True)
                if state:
                    if state.value["plan"] != plan:
                        raise UploadError(
                            "The prepared video or metadata changed; no duplicate upload"
                        )
                    pub = db.get(Publication, state.value["publication_id"], with_for_update=True)
                else:
                    source = db.scalar(
                        select(VideoGeneration)
                        .join(ProductionJob)
                        .where(
                            ProductionJob.idempotency_key == self.source_job_key,
                            VideoGeneration.clip_index == 0,
                        )
                    )
                    if source is None:
                        raise UploadError("Original generation record is missing")
                    video = self.video_record(db, source, plan)
                    db.add(video)
                    db.flush()
                    pub = Publication(
                        video_id=video.id, social_account_id=self.account_id, status="prepared"
                    )
                    db.add(pub)
                    db.flush()
                    state = SystemSetting(
                        key=self.operation_key, value={"plan": plan, "publication_id": pub.id}
                    )
                    db.add(state)
                known_id, encrypted_url, prior = (
                    pub.remote_id,
                    pub.upload_session_reference,
                    pub.status,
                )
                if not known_id and not encrypted_url:
                    if prior != "prepared":
                        raise UploadError(
                            "An earlier initiation is ambiguous; do not start another"
                        )
                    pub.status = "starting"
            if known_id:
                return self.reconcile()
            if encrypted_url:
                session_url = self.http.session_url(
                    self.cipher.decrypt(encrypted_url.encode()).decode()
                )
            else:
                response = self.http.request(
                    "POST",
                    self.http.endpoints.start,
                    params={
                        "uploadType": "resumable",
                        "part": "snippet,status,localizations"
                        if "localizations" in self.metadata
                        else "snippet,status",
                        "notifySubscribers": "false",
                    },
                    json=self.metadata,
                    headers={
                        "X-Upload-Content-Length": str(plan["bytes"]),
                        "X-Upload-Content-Type": "video/mp4",
                    },
                )
                if response.status_code not in (200, 201):
                    self.http.data(response)
                session_url = self.http.session_url(response.headers.get("Location", ""))
                with self.sessions.begin() as db:
                    state = db.get(SystemSetting, self.operation_key, with_for_update=True)
                    pub = db.get(Publication, state.value["publication_id"], with_for_update=True)
                    pub.upload_session_reference = self.cipher.encrypt(
                        session_url.encode()
                    ).decode()
                    pub.status = "uploading"
            offset = self.progress(
                self.http.request(
                    "PUT",
                    session_url,
                    data=b"",
                    headers={"Content-Length": "0", "Content-Range": f"bytes */{plan['bytes']}"},
                ),
                plan["bytes"],
            )
            # Every write is bounded, and its acknowledged range is authoritative.
            for _ in range(512):
                if offset is None:
                    return self.reconcile()
                if offset >= plan["bytes"]:
                    raise UploadError(
                        "All bytes acknowledged without a video ID; reconcile session"
                    )
                with self.asset.open("rb") as media:
                    media.seek(offset)
                    chunk = media.read(self.http.chunk_size)
                response = self.http.request(
                    "PUT",
                    session_url,
                    data=chunk,
                    headers={
                        "Content-Type": "video/mp4",
                        "Content-Length": str(len(chunk)),
                        "Content-Range": (
                            f"bytes {offset}-{offset + len(chunk) - 1}/{plan['bytes']}"
                        ),
                    },
                )
                next_offset = self.progress(response, plan["bytes"])
                if next_offset is not None and next_offset <= offset:
                    raise UploadError(
                        "Upload did not advance; query saved progress before retrying"
                    )
                offset = next_offset
            raise UploadError("Upload step limit reached; retain and resume the saved session")
