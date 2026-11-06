"""Owner-requested hashtag edit of the existing private trial; no upload or AI call."""

import hashlib
import json
from decimal import Decimal

from sqlalchemy import func, select

from tsu.config import Settings
from tsu.db import make_engine, make_sessions
from tsu.models import ModelUsage, ProductionJob, Publication, VideoGeneration
from tsu.trial import KEY
from tsu.youtube_job import YouTubeJob

settings = Settings()
assert not any(
    (settings.spending_authorized, settings.publishing_authorized, settings.enable_daily_scheduler)
)
assert settings.daily_budget_usd == settings.monthly_budget_usd == 0
engine = make_engine(settings.database_url.get_secret_value())
sessions = make_sessions(engine)


def counts():
    with sessions() as db:
        return {
            "usages": db.scalar(select(func.count()).select_from(ModelUsage)),
            "generations": db.scalar(select(func.count()).select_from(VideoGeneration)),
            "publications": db.scalar(select(func.count()).select_from(Publication)),
            "actual_usd": str(db.scalar(select(func.sum(ModelUsage.actual_usd))) or Decimal(0)),
            "held_usd": str(
                db.scalar(
                    select(func.sum(ModelUsage.reserved_usd)).where(ModelUsage.actual_usd.is_(None))
                )
                or Decimal(0)
            ),
        }


try:
    with sessions() as db:
        key = "production:" + hashlib.sha256(KEY.encode()).hexdigest()
        job = db.scalar(select(ProductionJob).where(ProductionJob.idempotency_key == key))
        assert job.id == "a13b3205-90ae-49ef-8675-24bd919ff709"
        assert job.status == "completed_private" and job.payload["visibility"] == "private"
        job_id, result = job.id, job.payload["result"]
        assert result["sha256"] == (
            "9f1babe950ef63a4f1ec0294c02a3021dee794218c89420b5accf202293416f6"
        )
        assert result["quality_pass"] and result["technical_pass"]
    before = counts()
    service = YouTubeJob(settings, engine, job_id, result)
    try:
        assert service.snapshot()["video_id"] == "G9wNpynDbPY"
        updated = service.update_discovery_metadata(authorized=True)
        assert updated["video_id"] == "G9wNpynDbPY" and updated["privacy"] == "private"
    finally:
        service.close()
    after = counts()
    assert before == after
    print(
        json.dumps(
            {
                "authorization": "Owner request 2026-11-05: add hashtags to descriptions",
                "update": updated,
                "counts_before_and_after": after,
                "original_media_and_quality_record_preserved": True,
                "recurring_controls_remain_disabled": True,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
finally:
    engine.dispose()
