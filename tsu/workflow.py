"""Per-video production, durable paid intents, practical quality and bounded publication."""

import argparse
import hashlib
import json
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Literal

from pydantic import Field, model_validator
from sqlalchemy import select, text

from tsu.budget import BudgetBlocked, record_budget_stop
from tsu.config import Settings
from tsu.contracts import StrictModel
from tsu.db import make_engine, make_sessions
from tsu.jobs import IdempotencyConflict, create_job
from tsu.models import Alert, Concept, ProductionJob, Video, utcnow
from tsu.native_profile import is_native, native_profile
from tsu.openrouter import OpenRouter, ProviderError
from tsu.pilot import MODELS, FirstVideo, PilotBrief
from tsu.production import production_profile, render_final
from tsu.sound_design import PROFILE as SOUND_PROFILE
from tsu.sound_design import SoundPlan, contextual_profile
from tsu.youtube_metadata import localized_metadata
from tsu.youtube_upload import UploadError

VERSION = "production_v1"
ACTIVE = (
    "queued",
    "running",
    "retry_wait",
    "awaiting_processing",
    "budget_blocked",
    "awaiting_publication_authorization",
)


class ProductionInput(StrictModel):
    concept: str = Field(min_length=3, max_length=2000)
    visibility: Literal["private", "public"] = "private"


class Translation(StrictModel):
    title: str = Field(min_length=1, max_length=100)
    description: str = Field(min_length=1, max_length=2000)


class SixLanguages(StrictModel):
    en: Translation
    fr: Translation
    es: Translation
    it: Translation
    ru: Translation
    zh_CN: Translation = Field(alias="zh-CN")


class ProductionBrief(PilotBrief):
    localizations: SixLanguages
    sound_plan: SoundPlan | None = None

    @model_validator(mode="after")
    def valid_metadata(self):
        translations = self.localizations.model_dump(by_alias=True)
        localized_metadata(translations)
        if (self.title, self.description) != (
            translations["en"]["title"],
            translations["en"]["description"],
        ):
            raise ValueError("Default English metadata must match the English translation")
        if any("TechnoInno" not in t["description"] for t in translations.values()):
            raise ValueError("Each localized description must retain the brand and AI disclosure")
        return self


def enqueue(session, key, body: ProductionInput, *, legacy_profile=None):
    if not key or len(key) > 120:
        raise ValueError("Use an Idempotency-Key of 1 to 120 characters")
    durable_key = "production:" + hashlib.sha256(key.encode()).hexdigest()
    existing = session.scalar(
        select(ProductionJob).where(ProductionJob.idempotency_key == durable_key)
    )
    if existing:
        if any(existing.payload.get(k) != v for k, v in body.model_dump().items()):
            raise IdempotencyConflict("Idempotency key has different input")
        return existing, False
    return create_job(
        session,
        durable_key,
        {
            **body.model_dump(),
            "workflow_version": VERSION,
            "production_profile": legacy_profile or native_profile(),
        },
    )


def readiness(settings):
    from tsu.notifications import readiness as email_readiness

    blockers = []
    if not settings.spending_authorized:
        blockers.append("spending_not_authorized")
    if settings.daily_budget_usd <= 0 or settings.monthly_budget_usd <= 0:
        blockers.append("budget_caps_zero")
    if not settings.publishing_authorized:
        blockers.append("automatic_publication_not_authorized")
    if not settings.production_times:
        blockers.append("daily_times_not_selected")
    if not settings.youtube_long_lived_grant_confirmed:
        blockers.append("durable_google_access_not_confirmed")
    if not settings.production_live_validated:
        blockers.append("complete_live_cycle_not_validated")
    if not settings.offhost_backup_confirmed:
        blockers.append("automatic_offhost_backup_not_confirmed")
    if not settings.outbound_alerts_confirmed or not email_readiness(settings)["ready"]:
        blockers.append("outbound_alert_delivery_not_confirmed")
    return {
        "workflow_implemented": True,
        "scheduler_enabled": settings.enable_daily_scheduler,
        "configured_local_times": list(settings.production_times),
        "timezone": settings.tz,
        "blockers": blockers,
        "automatic_regeneration": False,
        "live_validation_completed": settings.production_live_validated,
        "outbound_alerts": email_readiness(settings),
        "automatic_offhost_backup_confirmed": settings.offhost_backup_confirmed,
    }


@contextmanager
def workflow_lock(engine):
    if engine.dialect.name != "postgresql":
        raise RuntimeError("Production execution requires PostgreSQL")
    with engine.connect() as connection:
        if not connection.scalar(text("SELECT pg_try_advisory_lock(865190044)")):
            raise RuntimeError("A production workflow is already active")
        try:
            yield
        finally:
            connection.execute(text("SELECT pg_advisory_unlock(865190044)"))


class JobProducer(FirstVideo):
    expected_models = MODELS
    brief_schema = ProductionBrief
    chat_tokens = 3500
    price_limits = {"creative_model": ("0.10", "0.40"), "quality_model": ("0.25", "1.50")}

    def completion_status(self, decision):
        return "running" if decision == "accepted" else super().completion_status(decision)

    def validate_final(self, digest):
        with self.sessions() as db:
            job = self.job(db)
            duplicate = db.scalar(
                select(Video).where(
                    Video.sha256 == digest,
                    Video.concept_id != job.concept_id,
                )
            )
            if duplicate:
                raise RuntimeError("This exact finished video already exists; publication blocked")

    def __init__(self, settings, engine, provider, job_id, interval=20, polls=60):
        self.settings, self.engine, self.provider = settings, engine, provider
        self.sessions = make_sessions(engine)
        self.models = {role: getattr(settings, role) for role in MODELS}
        if self.models != self.expected_models:
            raise RuntimeError("Review model capabilities and price limits before changing models")
        with self.sessions() as db:
            job = db.get(ProductionJob, job_id)
            if not job or job.payload.get("workflow_version") != VERSION:
                raise RuntimeError("Not a reusable production job")
            self.key, self.job_id = job.idempotency_key, job.id
            self.theme = job.payload["concept"]
            profile = job.payload.get("production_profile", "balanced_audio_v2")
            self.context_sound = (
                profile.get("version") if isinstance(profile, dict) else profile
            ) == SOUND_PROFILE
        self.directory = settings.data_root / "jobs" / job_id
        self.directory.mkdir(parents=True, exist_ok=True)
        self.interval, self.polls = interval, polls

    def prepare(self):
        if (
            not self.settings.spending_authorized
            or min(self.settings.daily_budget_usd, self.settings.monthly_budget_usd) <= 0
        ):
            raise BudgetBlocked("Owner spending authorization and positive budgets are required")
        if (self.directory / "operator-brief.json").exists():
            raise RuntimeError("Reusable jobs must not reuse a supervised operator brief")
        self.verify_catalogue()
        with self.sessions.begin() as db:
            job = self.job(db)
            recent = list(
                db.scalars(select(Concept.name).order_by(Concept.created_at.desc()).limit(20))
            )
            saved_instruction = job.payload.get("creative_instruction")
            sound_guidance = (
                "Every description must disclose AI-generated visuals for TechnoInno and original "
                "synthesized sound effects in that language. Set sound_plan to kind water_drops, "
                "liquid_flow, soft_grains, soft_friction or soft_roll. Use needs_review if none "
                "matches; never substitute unrelated effects or background music. Give distinct "
                "cues_seconds for visible impacts/rolling events on the final 15.8-second timeline "
                "(second shot starts at 7.8s); use no impact cues for continuous textures. "
                "Plan simple visible actions that match the sound and mention timing in the video "
                "prompts. Source clips are silent; locally synthesized action effects "
                "replace music. "
                if self.context_sound
                else "Every description must disclose AI-generated visuals for TechnoInno "
                "and original "
                "music, translated into that language. Sources are silent but the final 15.8s "
                "montage adds original calm music and a short dissolve; do not call it silent. "
            )
            self.creative_instruction = saved_instruction or (
                "Create a NEW original TechnoInno satisfying macro video. Theme: "
                + self.theme
                + ". Avoid these recent concepts: "
                + json.dumps(recent, ensure_ascii=False)
                + ". Use realistic simple physics and fixed cinematic macro lighting. "
                "No people, dialogue, lettering, logos or watermarks. Two complementary 8-second "
                "9:16 1080p source clips; the second starts from a frame of the first. "
                "Write two detailed English prompts, English title/description, hashtags, "
                "and natural complete localized titles/descriptions for en, fr, es, it, ru, zh-CN. "
                "English base title/description must exactly match en. "
                "Use an accurate short title, with its main subject early, and one or two main "
                "subject keywords in each localized title/first description line. Give 1-2 precise "
                "subject hashtags in hashtags, no #viral/#fyp or hashtags in the prose. Show the "
                "action in the opening second, no intro, and end naturally; "
                "a loop only if coherent. "
                + sound_guidance
                + "No invented achievements or claims. Return only the strict JSON object."
            )
            job.payload = {
                **job.payload,
                "creative_instruction": self.creative_instruction,
                "production_profile": {
                    **production_profile(),
                    **(contextual_profile() if self.context_sound else {}),
                },
                "quoted_generation_usd": str(self.clip_quote * 2),
            }

    def creative(self):
        brief = super().creative()
        if self.context_sound and (not brief.sound_plan or brief.sound_plan.kind == "needs_review"):
            raise RuntimeError("An appropriate sound plan is required before paid video generation")
        return brief

    def render(self, clips, final, brief):
        return render_final(
            clips, final, sound_plan=brief.sound_plan if self.context_sound else None
        )

    def concept_fingerprint(self, brief):
        digest = hashlib.sha256(" ".join(brief.concept.casefold().split()).encode()).hexdigest()
        with self.sessions() as db:
            existing = db.scalar(select(Concept).where(Concept.fingerprint == digest))
            own = self.job(db)
            if existing and existing.id != own.concept_id:
                raise RuntimeError(
                    "The proposed concept duplicates an existing concept; review required"
                )
        return digest


class ProductionWorkflow:
    def __init__(
        self, settings, engine, provider_factory=None, publisher_factory=None, interval=20, polls=60
    ):
        self.settings, self.engine = settings, engine
        self.sessions = make_sessions(engine)
        self.provider_factory = provider_factory or (
            lambda: OpenRouter(settings.openrouter_api_key.get_secret_value(), timeout=(10, 300))
        )
        self.publisher_factory = publisher_factory
        self.interval, self.polls = interval, polls

    def report(self, job_id, status, reason=None, alert=False):
        with self.sessions.begin() as db:
            job = db.get(ProductionJob, job_id)
            job.status, job.reason, job.updated_at = status, reason, utcnow()
            job.lease_token = job.lease_until = None
            if alert:
                key = f"production:{job_id}:{status}"
                if not db.scalar(select(Alert).where(Alert.dedupe_key == key)):
                    db.add(
                        Alert(
                            dedupe_key=key,
                            kind=status,
                            message=f"Production {job_id}: {reason or status}",
                        )
                    )
            return {"job_id": job_id, "status": status, "reason": reason}

    def run(self, job_id):
        with workflow_lock(self.engine):
            with self.sessions.begin() as db:
                job = db.get(ProductionJob, job_id)
                if not job or job.payload.get("workflow_version") != VERSION:
                    raise ValueError("Unknown reusable production job")
                if job.payload.get("owner_discarded") or job.payload.get("never_publish"):
                    return {"job_id": job.id, "status": "cancelled", "reason": job.reason}
                if job.status in {
                    "cancelled",
                    "published",
                    "completed_private",
                    "awaiting_owner_review",
                    "awaiting_local_edit",
                    "rejected",
                }:
                    return {"job_id": job.id, "status": job.status, "reason": job.reason}
                job.status, job.updated_at = "running", utcnow()
                job.attempts += 1
            provider = None
            try:
                provider = self.provider_factory()
                from tsu.native_production import NativeJobProducer

                producer_type = (
                    NativeJobProducer
                    if is_native(job.payload.get("production_profile"))
                    else JobProducer
                )
                producer = producer_type(
                    self.settings,
                    self.engine,
                    provider,
                    job_id,
                    interval=self.interval,
                    polls=self.polls,
                )
                result = producer.run()
                if not result["quality_pass"]:
                    status = (
                        "awaiting_local_edit"
                        if result["quality_decision"] == "local_edit"
                        else (
                            "rejected"
                            if result["quality_decision"] == "technical_failed"
                            else "awaiting_owner_review"
                        )
                    )
                    return self.report(job_id, status, result["quality_decision"], alert=True)
                if not self.settings.publishing_authorized:
                    return self.report(
                        job_id,
                        "awaiting_publication_authorization",
                        "Production approved; automatic upload is not authorized",
                    )
                if self.publisher_factory:
                    publisher = self.publisher_factory(job_id, result)
                else:
                    from tsu.youtube_job import YouTubeJob

                    publisher = YouTubeJob(self.settings, self.engine, job_id, result)
                try:
                    published = publisher.publish()
                finally:
                    publisher.close()
                if published["status"] in {"processing_private", "uploaded_unverified"}:
                    with self.sessions.begin() as db:
                        job = db.get(ProductionJob, job_id)
                        job.payload = {
                            **job.payload,
                            "retry_after": (utcnow() + timedelta(seconds=60)).isoformat(),
                        }
                    return self.report(
                        job_id, "awaiting_processing", "YouTube is processing the video"
                    )
                target = "published" if published["privacy"] == "public" else "completed_private"
                with self.sessions.begin() as db:
                    job = db.get(ProductionJob, job_id)
                    job.payload = {**job.payload, "publication_result": published}
                return self.report(job_id, target)
            except BudgetBlocked:
                with self.sessions.begin() as db:
                    record_budget_stop(db, job_id)
                    job = db.get(ProductionJob, job_id)
                    job.payload = {
                        **job.payload,
                        "retry_after": (utcnow() + timedelta(hours=1)).isoformat(),
                    }
                return self.report(
                    job_id, "budget_blocked", "Budget or spending authorization unavailable"
                )
            except Exception as error:
                # Unknown paid intents remain stored. No exception body or secret is exposed.
                safe = (
                    str(error)
                    if isinstance(error, (ProviderError, UploadError))
                    else type(error).__name__
                )
                if self.retryable(job_id, error):
                    with self.sessions.begin() as db:
                        job = db.get(ProductionJob, job_id)
                        attempts = job.payload.get("recovery_attempts", 0) + 1
                        job.payload = {
                            **job.payload,
                            "recovery_attempts": attempts,
                            "retry_after": (utcnow() + timedelta(seconds=60)).isoformat(),
                        }
                    if attempts <= 3:
                        return self.report(job_id, "retry_wait", safe)
                return self.report(job_id, "owner_attention", safe, alert=True)
            finally:
                if provider and hasattr(provider, "session"):
                    provider.session.close()

    def retryable(self, job_id, error):
        from tsu.models import Publication, SystemSetting, VideoGeneration

        message = str(error)
        transient = any(
            x in message
            for x in (
                "connection",
                "interrupted",
                "Polling deadline",
                "HTTP 500",
                "HTTP 502",
                "HTTP 503",
                "HTTP 504",
                "HTTP 429",
                "not yet visible",
            )
        )
        if not isinstance(error, (ProviderError, UploadError)) or not transient:
            return False
        with self.sessions() as db:
            job = db.get(ProductionJob, job_id)
            if any(v.get("state") != "done" for v in job.payload.get("calls", {}).values()):
                return False
            if db.scalar(
                select(VideoGeneration).where(
                    VideoGeneration.job_id == job_id,
                    VideoGeneration.status == "submitting",
                    VideoGeneration.remote_job_id.is_(None),
                )
            ):
                return False
            state = db.get(SystemSetting, "youtube:job:" + job_id)
            if state:
                pub = db.get(Publication, state.value["publication_id"])
                if pub.status == "starting" and not pub.upload_session_reference:
                    return False
        return True


def dispatch(settings, engine, workflow=None, now=None):
    if (
        not settings.spending_authorized
        or min(settings.daily_budget_usd, settings.monthly_budget_usd) <= 0
    ):
        return 0
    if settings.enable_daily_scheduler and readiness(settings)["blockers"]:
        return 0
    now = now or utcnow()
    sessions = make_sessions(engine)
    with sessions() as db:
        jobs = db.scalars(
            select(ProductionJob)
            .where(
                ProductionJob.status.in_(ACTIVE),
                ProductionJob.payload["workflow_version"].as_string() == VERSION,
                (ProductionJob.status != "awaiting_publication_authorization")
                if not settings.publishing_authorized
                else True,
            )
            .order_by(ProductionJob.created_at, ProductionJob.id)
            .limit(20)
        ).all()
        selected = next(
            (
                j.id
                for j in jobs
                if not j.payload.get("retry_after")
                or datetime.fromisoformat(j.payload["retry_after"]) <= now
            ),
            None,
        )
    if not selected:
        return 0
    try:
        (workflow or ProductionWorkflow(settings, engine)).run(selected)
    except RuntimeError:
        return 0  # Another process owns the global workflow lock.
    return 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--job", required=True)
    args = parser.parse_args()
    settings = Settings()
    engine = make_engine(settings.database_url.get_secret_value())
    try:
        print(json.dumps(ProductionWorkflow(settings, engine).run(args.job), ensure_ascii=False))
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
