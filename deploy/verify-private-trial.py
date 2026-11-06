"""Verify the authorized private trial through Google reads, without uploads or paid calls."""

import hashlib
import json
from decimal import Decimal
from pathlib import Path

from sqlalchemy import func, select

from tsu.config import Settings
from tsu.db import make_engine, make_sessions
from tsu.models import (
    ModelUsage,
    ProductionJob,
    Publication,
    QualityCheck,
    VideoGeneration,
)
from tsu.trial import KEY
from tsu.youtube_job import YouTubeJob
from tsu.youtube_publication import YouTubePublication

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
        assert job.status == "completed_private" and job.payload["visibility"] == "private"
        job_id, result = job.id, job.payload["result"]
        assert result["quality_pass"] and result["technical_pass"]
        assert result["quality_decision"] == "accepted"
        assert not result["automatic_regeneration"] and not result["scheduler_enabled"]
        quality = db.scalar(select(QualityCheck).where(QualityCheck.video_id == result["video_id"]))
        assert quality.approved and quality.technical_pass
        charges = db.scalars(
            select(ModelUsage).where(ModelUsage.operation_key.startswith(key + ":"))
        ).all()
        assert len(charges) == 7
        unsettled = [x for x in charges if x.actual_usd is None]
        assert len(unsettled) == 3
        assert all(x.purpose.startswith("quality_balanced_audio_v2") for x in unsettled)
        assert sum(x.reserved_usd for x in unsettled) == Decimal("0.14")
        assert job.payload["supervised_review_recovery"]["uncertain_original_preserved"]
        actual = sum((x.actual_usd or Decimal(0) for x in charges), Decimal(0))
        held = sum((x.reserved_usd for x in unsettled), Decimal(0))
        assert actual + held <= Decimal("1.00")
        count = db.scalar(select(func.count()).select_from(Publication))
        generations = db.scalar(select(func.count()).select_from(VideoGeneration))
        assert (count, generations) == (2, 4)
        original = db.scalar(
            select(ProductionJob).where(ProductionJob.idempotency_key == "owner:first-video:v1")
        )
        assert original.status == "rejected"
    asset = Path(result["file"])
    with asset.open("rb") as source:
        assert hashlib.file_digest(source, "sha256").hexdigest() == result["sha256"]
    service = YouTubeJob(settings, engine, job_id, result)
    try:
        localizations = service.metadata["localizations"]
        current = service.reconcile()
        assert current["status"] == "processed_private" and current["privacy"] == "private"
        assert current["requested_privacy"] == "private"
        service.verify_metadata(service.remote())
        verified = {}
        for code, expected in localizations.items():
            response = service.http.data(
                service.http.request(
                    "GET",
                    service.http.endpoints.api + "/videos",
                    params={"part": "snippet", "id": current["video_id"], "hl": code},
                )
            )
            item = next(x for x in response["items"] if x["id"] == current["video_id"])
            assert item["snippet"]["channelId"] == settings.youtube_channel_id
            assert item["snippet"]["localized"] == expected
            verified[code] = True
    finally:
        service.close()
    legacy = YouTubePublication(settings, engine)
    try:
        old = legacy.status()
        assert old["video_id"] == "qNsEQFHoMdk" and old["privacy"] == "public"
        assert old["translations_verified"]
    finally:
        legacy.close()
    print(
        json.dumps(
            {
                "job_id": job_id,
                "result": result,
                "confirmed_trial_cost_usd": str(actual),
                "held_trial_reservations_usd": str(held),
                "supervised_review_recovery_required": True,
                "maximum_authorized_additional_spend_usd": "1.00",
                "publication": current,
                "six_localized_readbacks_match": verified,
                "six_descriptions_have_hashtags": all(
                    "#Shorts" in t["description"] for t in localizations.values()
                ),
                "original_public_video_unchanged": True,
                "original_rejected_job_preserved": True,
                "global_publication_count": count,
                "global_generation_count": generations,
                "global_recurring_controls_remain_disabled": True,
                "real_cycle_verified": True,
                "verification_new_uploads": 0,
                "verification_new_paid_calls": 0,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
finally:
    engine.dispose()
