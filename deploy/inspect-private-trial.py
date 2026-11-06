"""Read-only progress and ledger evidence for the authorized one-job private trial."""

import hashlib
import json
from decimal import Decimal

from sqlalchemy import func, select

from tsu.config import Settings
from tsu.db import make_engine, make_sessions
from tsu.models import (
    Concept,
    ModelUsage,
    ProductionJob,
    Publication,
    QualityCheck,
    SocialAccount,
    Video,
    VideoGeneration,
    utcnow,
)
from tsu.trial import KEY

settings = Settings()
assert not any(
    (settings.spending_authorized, settings.publishing_authorized, settings.enable_daily_scheduler)
)
assert settings.daily_budget_usd == settings.monthly_budget_usd == 0
engine = make_engine(settings.database_url.get_secret_value())
try:
    with make_sessions(engine)() as db:
        key = "production:" + hashlib.sha256(KEY.encode()).hexdigest()
        job = db.scalar(select(ProductionJob).where(ProductionJob.idempotency_key == key))
        assert job and job.payload["visibility"] == "private"
        account = db.scalar(
            select(SocialAccount).where(
                SocialAccount.external_id == settings.youtube_channel_id,
                SocialAccount.platform == "youtube",
            )
        )
        assert account and not account.approved_for_publication
        charges = db.scalars(
            select(ModelUsage).where(ModelUsage.operation_key.startswith(key + ":"))
        ).all()
        actual = sum((x.actual_usd or Decimal(0) for x in charges), Decimal(0))
        held = sum((x.reserved_usd for x in charges if x.actual_usd is None), Decimal(0))
        generations = db.scalars(
            select(VideoGeneration).where(VideoGeneration.job_id == job.id)
        ).all()
        video = db.scalar(select(Video).where(Video.concept_id == job.concept_id))
        quality = (
            db.scalar(select(QualityCheck).where(QualityCheck.video_id == video.id))
            if video
            else None
        )
        publication = (
            db.scalar(select(Publication).where(Publication.video_id == video.id))
            if video
            else None
        )
        concept = db.get(Concept, job.concept_id) if job.concept_id else None
        report = {
            "observed_at": utcnow().isoformat(),
            "job_id": job.id,
            "status": job.status,
            "reason": job.reason,
            "calls": {k: v["state"] for k, v in job.payload.get("calls", {}).items()},
            "confirmed_trial_cost_usd": str(actual),
            "held_trial_reservations_usd": str(held),
            "trial_cap_usd": "1.00",
            "charges": [
                {
                    "purpose": x.purpose,
                    "model": x.model,
                    "status": x.status,
                    "actual_usd": str(x.actual_usd) if x.actual_usd is not None else None,
                    "reserved_usd": str(x.reserved_usd),
                }
                for x in charges
            ],
            "generations": [
                {
                    "clip": x.clip_index + 1,
                    "status": x.status,
                    "remote_id_saved": bool(x.remote_job_id),
                }
                for x in generations
            ],
            "concept": concept.name if concept else None,
            "localizations": concept.brief.get("localizations") if concept else None,
            "result": job.payload.get("result"),
            "supervised_review_recovery": job.payload.get("supervised_review_recovery"),
            "publication_result": job.payload.get("publication_result"),
            "quality": (
                {
                    "score": quality.score,
                    "technical_pass": quality.technical_pass,
                    "approved": quality.approved,
                    "details": quality.details,
                }
                if quality
                else None
            ),
            "publication": (
                {
                    "status": publication.status,
                    "url": publication.url,
                    "remote_id": publication.remote_id,
                }
                if publication
                else None
            ),
            "global_confirmed_ai_cost_usd": str(db.scalar(select(func.sum(ModelUsage.actual_usd)))),
            "global_publication_count": db.scalar(select(func.count()).select_from(Publication)),
            "global_flags_and_account_approval_remain_disabled": True,
            "global_budget_caps_usd": "0",
        }
        assert actual + held <= Decimal("1.00"), "Trial cap exceeded"
        print(json.dumps(report, ensure_ascii=False, indent=2))
finally:
    engine.dispose()
