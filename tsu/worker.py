import logging

from celery import Celery

from tsu.config import Settings
from tsu.db import make_engine, make_sessions
from tsu.jobs import (
    claim_next,
    finish_preflight,
    recover_expired,
    schedule_day,
    schedule_production,
    utcnow,
)

settings = Settings()
celery_app = Celery("tsu", broker=settings.redis_url.get_secret_value())
celery_app.conf.update(
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    task_ignore_result=True,
    task_soft_time_limit=45,
    task_time_limit=60,
    timezone=settings.tz,
    broker_connection_retry_on_startup=True,
    beat_schedule={
        "scan-durable-jobs": {"task": "tsu.scan", "schedule": 60.0, "options": {"expires": 55}}
    },
)
logger = logging.getLogger(__name__)


def scan_once(sessions, enable_daily: bool = False, timezone: str = "Africa/Casablanca") -> int:
    with sessions.begin() as session:
        recover_expired(session, utcnow())
        if enable_daily:
            schedule_day(session, utcnow(), timezone)
    count = 0
    for _ in range(20):
        with sessions.begin() as session:
            job = claim_next(session, utcnow())
            if job is None:
                break
            job_id, token = job.id, job.lease_token
        # Any interruption after claim is recovered from the durable lease on the next scan.
        with sessions.begin() as session:
            finish_preflight(session, job_id, token, utcnow())
        count += 1
    return count


@celery_app.task(name="tsu.scan", soft_time_limit=2700, time_limit=2760)
def scan():
    engine = make_engine(settings.database_url.get_secret_value())
    try:
        from tsu.workflow import dispatch, readiness

        if settings.enable_daily_scheduler and not readiness(settings)["blockers"]:
            with make_sessions(engine).begin() as session:
                from sqlalchemy import select

                from tsu.models import SocialAccount

                account = session.scalar(
                    select(SocialAccount).where(
                        SocialAccount.platform == "youtube",
                        SocialAccount.external_id == settings.youtube_channel_id,
                    )
                )
                if account and account.approved_for_publication:
                    schedule_production(session, utcnow(), settings.tz, settings.production_times)
        count = dispatch(settings, engine)
        logger.info("Production jobs handled=%s", count)
        return count
    finally:
        engine.dispose()


@celery_app.task(name="tsu.email_alerts", soft_time_limit=180, time_limit=200)
def email_alerts():
    from tsu.notifications import deliver

    engine = make_engine(settings.database_url.get_secret_value())
    try:
        result = deliver(settings, engine)
        logger.info(
            "Owner email alert delivery accepted=%s uncertain=%s",
            result["accepted"],
            result["uncertain"],
        )
        return result
    finally:
        engine.dispose()


celery_app.conf.beat_schedule["email-owner-alerts"] = {
    "task": "tsu.email_alerts",
    "schedule": 60.0,
    "options": {"expires": 55},
}
