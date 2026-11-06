from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from tsu.db import Base


def utcnow():
    return datetime.now(UTC)


class Record:
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, index=True
    )


class Concept(Record, Base):
    __tablename__ = "concepts"
    name: Mapped[str] = mapped_column(String(300))
    category: Mapped[str] = mapped_column(String(100))
    fingerprint: Mapped[str] = mapped_column(String(64), unique=True)
    brief: Mapped[dict] = mapped_column(JSON)


class Prompt(Record, Base):
    __tablename__ = "prompts"
    concept_id: Mapped[str] = mapped_column(ForeignKey("concepts.id"))
    version: Mapped[int] = mapped_column(Integer, default=1)
    text: Mapped[str] = mapped_column(Text)
    __table_args__ = (UniqueConstraint("concept_id", "version"),)


class ProductionJob(Record, Base):
    __tablename__ = "production_jobs"
    idempotency_key: Mapped[str] = mapped_column(String(160), unique=True)
    payload_hash: Mapped[str] = mapped_column(String(64))
    payload: Mapped[dict] = mapped_column(JSON)
    concept_id: Mapped[str | None] = mapped_column(ForeignKey("concepts.id"))
    status: Mapped[str] = mapped_column(String(40), default="queued", index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    lease_token: Mapped[str | None] = mapped_column(String(36))
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reason: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    __table_args__ = (CheckConstraint("attempts >= 0"),)


class VideoGeneration(Record, Base):
    __tablename__ = "video_generations"
    concept_id: Mapped[str] = mapped_column(ForeignKey("concepts.id"))
    prompt_id: Mapped[str] = mapped_column(ForeignKey("prompts.id"))
    job_id: Mapped[str] = mapped_column(ForeignKey("production_jobs.id"))
    attempt: Mapped[int] = mapped_column(Integer)
    clip_index: Mapped[int] = mapped_column(Integer, default=0)
    provider: Mapped[str] = mapped_column(String(100))
    model: Mapped[str] = mapped_column(String(200))
    remote_job_id: Mapped[str | None] = mapped_column(String(250), unique=True)
    parameters: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(40), default="planned")
    elapsed_seconds: Mapped[Decimal | None] = mapped_column(Numeric(12, 3))
    cost_usd: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    __table_args__ = (
        UniqueConstraint("concept_id", "attempt", "clip_index"),
        CheckConstraint("attempt >= 1 AND attempt <= 2"),
        CheckConstraint("clip_index >= 0"),
    )


class Video(Record, Base):
    __tablename__ = "videos"
    concept_id: Mapped[str] = mapped_column(ForeignKey("concepts.id"))
    generation_id: Mapped[str] = mapped_column(ForeignKey("video_generations.id"))
    original_key: Mapped[str] = mapped_column(Text)
    final_key: Mapped[str | None] = mapped_column(Text)
    sha256: Mapped[str] = mapped_column(String(64))
    technical_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(40), default="generated")


class QualityCheck(Record, Base):
    __tablename__ = "quality_checks"
    video_id: Mapped[str] = mapped_column(ForeignKey("videos.id"))
    model: Mapped[str | None] = mapped_column(String(200))
    score: Mapped[int] = mapped_column(Integer)
    technical_pass: Mapped[bool] = mapped_column(Boolean)
    approved: Mapped[bool] = mapped_column(Boolean)
    details: Mapped[dict] = mapped_column(JSON)
    rejection_reason: Mapped[str | None] = mapped_column(Text)
    __table_args__ = (
        CheckConstraint("score >= 0 AND score <= 100"),
        CheckConstraint("NOT approved OR (technical_pass AND score >= 80)"),
    )


class SocialAccount(Record, Base):
    __tablename__ = "social_accounts"
    platform: Mapped[str] = mapped_column(String(30))
    external_id: Mapped[str] = mapped_column(String(200))
    handle: Mapped[str] = mapped_column(String(200))
    secret_reference: Mapped[str] = mapped_column(Text)
    scopes: Mapped[list] = mapped_column(JSON, default=list)
    approved_for_publication: Mapped[bool] = mapped_column(Boolean, default=False)
    __table_args__ = (UniqueConstraint("platform", "external_id"),)


class Publication(Record, Base):
    __tablename__ = "publications"
    video_id: Mapped[str] = mapped_column(ForeignKey("videos.id"))
    social_account_id: Mapped[str] = mapped_column(ForeignKey("social_accounts.id"))
    status: Mapped[str] = mapped_column(String(40), default="planned")
    remote_id: Mapped[str | None] = mapped_column(String(250))
    upload_session_reference: Mapped[str | None] = mapped_column(Text)
    url: Mapped[str | None] = mapped_column(Text)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)
    __table_args__ = (UniqueConstraint("video_id", "social_account_id"),)


class Analytics(Record, Base):
    __tablename__ = "analytics"
    publication_id: Mapped[str] = mapped_column(ForeignKey("publications.id"))
    metric: Mapped[str] = mapped_column(String(100))
    value: Mapped[Decimal | None] = mapped_column(Numeric(24, 6))
    source: Mapped[str] = mapped_column(String(250))
    unavailable_reason: Mapped[str | None] = mapped_column(Text)


class ModelUsage(Record, Base):
    __tablename__ = "model_usage"
    operation_key: Mapped[str] = mapped_column(String(200), unique=True)
    model: Mapped[str] = mapped_column(String(200))
    purpose: Mapped[str] = mapped_column(String(100))
    reserved_usd: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    actual_usd: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    status: Mapped[str] = mapped_column(String(30), default="reserved")
    remote_request_id: Mapped[str | None] = mapped_column(String(250))
    settled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        CheckConstraint("reserved_usd > 0"),
        CheckConstraint("actual_usd IS NULL OR actual_usd >= 0"),
    )


class SystemSetting(Base):
    __tablename__ = "system_settings"
    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[dict] = mapped_column(JSON)


class BudgetGuard(Base):
    __tablename__ = "budget_guards"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    frozen: Mapped[bool] = mapped_column(Boolean, default=False)
    reason: Mapped[str | None] = mapped_column(Text)


class Alert(Record, Base):
    __tablename__ = "alerts"
    dedupe_key: Mapped[str] = mapped_column(String(250), unique=True)
    kind: Mapped[str] = mapped_column(String(80))
    message: Mapped[str] = mapped_column(Text)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)


class OwnerSession(Base):
    __tablename__ = "owner_sessions"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    secret_version: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class OAuthFlow(Base):
    __tablename__ = "oauth_flows"
    state_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    owner_session_hash: Mapped[str] = mapped_column(ForeignKey("owner_sessions.token_hash"))
    verifier_encrypted: Mapped[str] = mapped_column(Text)
    expected_channel_id: Mapped[str] = mapped_column(String(100))
    redirect_uri: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class OAuthCredential(Base):
    __tablename__ = "oauth_credentials"
    account_id: Mapped[str] = mapped_column(ForeignKey("social_accounts.id"), primary_key=True)
    credentials_encrypted: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
