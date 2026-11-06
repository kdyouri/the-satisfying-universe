from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select

from tsu.jobs import claim_next, create_job, finish_preflight, recover_expired, schedule_day
from tsu.models import Alert, ProductionJob
from tsu.worker import scan_once

NOW = datetime(2026, 11, 4, 12, tzinfo=UTC)


@pytest.mark.postgres
def test_recover_fences_old_worker_and_preserves_job(pg_sessions):
    with pg_sessions.begin() as session:
        job, _ = create_job(session, "recover", {"concept": "Water"})
        job_id = job.id
    with pg_sessions.begin() as session:
        first = claim_next(session, NOW)
        old_token = first.lease_token
    later = NOW + timedelta(minutes=3)
    with pg_sessions.begin() as session:
        assert recover_expired(session, later) == 1
        new = claim_next(session, later)
        token = new.lease_token
    with pg_sessions.begin() as session:
        assert not finish_preflight(session, job_id, old_token, later)
        assert finish_preflight(session, job_id, token, later)
    with pg_sessions() as session:
        assert session.get(ProductionJob, job_id).status == "awaiting_configuration"


@pytest.mark.postgres
def test_three_expired_preflights_fail_visibly(pg_sessions):
    with pg_sessions.begin() as session:
        job, _ = create_job(session, "three", {"concept": "Glass"})
        job_id = job.id
    for index in range(3):
        now = NOW + timedelta(minutes=index * 4)
        with pg_sessions.begin() as session:
            claim_next(session, now)
        with pg_sessions.begin() as session:
            recover_expired(session, now + timedelta(minutes=3))
    with pg_sessions() as session:
        assert session.get(ProductionJob, job_id).status == "failed"
        assert session.scalar(select(func.count()).select_from(Alert)) == 1


@pytest.mark.postgres
def test_concurrent_job_idempotency_and_claim(pg_sessions):
    def create(_):
        with pg_sessions.begin() as session:
            job, _ = create_job(session, "duplicate", {"concept": "Marble"})
            return job.id

    with ThreadPoolExecutor(max_workers=6) as executor:
        assert len(set(executor.map(create, range(6)))) == 1

    def claim(_):
        with pg_sessions.begin() as session:
            return claim_next(session, NOW) is not None

    with ThreadPoolExecutor(max_workers=6) as executor:
        assert sum(executor.map(claim, range(6))) == 1


@pytest.mark.postgres
def test_daily_slots_idempotent_and_worker_stops_honestly(pg_sessions):
    with pg_sessions.begin() as session:
        first = schedule_day(session, NOW, "Africa/Casablanca")
    with pg_sessions.begin() as session:
        assert schedule_day(session, NOW, "Africa/Casablanca") == first
    assert scan_once(pg_sessions) == 2
    assert scan_once(pg_sessions) == 0
    with pg_sessions() as session:
        assert set(session.scalars(select(ProductionJob.status))) == {"awaiting_configuration"}
