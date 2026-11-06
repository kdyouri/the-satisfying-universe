import hashlib
import json
from datetime import UTC, datetime, timedelta
from uuid import uuid4
from zoneinfo import ZoneInfo

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from tsu.models import Alert, ProductionJob


class IdempotencyConflict(ValueError):
    pass


def create_job(session: Session, key: str, payload: dict) -> tuple[ProductionJob, bool]:
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    existing = session.scalar(select(ProductionJob).where(ProductionJob.idempotency_key == key))
    if existing:
        if existing.payload_hash != digest:
            raise IdempotencyConflict("Idempotency key has different input")
        return existing, False
    job = ProductionJob(idempotency_key=key, payload=payload, payload_hash=digest)
    try:
        with session.begin_nested():
            session.add(job)
            session.flush()
        return job, True
    except IntegrityError:
        existing = session.scalar(select(ProductionJob).where(ProductionJob.idempotency_key == key))
        if existing is None:
            raise
        if existing.payload_hash != digest:
            raise IdempotencyConflict("Idempotency key has different input") from None
        return existing, False


def claim_next(session: Session, now: datetime) -> ProductionJob | None:
    if session.bind.dialect.name != "postgresql":
        raise RuntimeError("Workers require PostgreSQL SKIP LOCKED semantics")
    job = session.scalar(
        select(ProductionJob)
        .where(ProductionJob.status == "queued")
        .order_by(ProductionJob.created_at, ProductionJob.id)
        .with_for_update(skip_locked=True)
        .limit(1)
    )
    if job is None:
        return None
    job.status = "preflight"
    job.attempts += 1
    job.lease_token = str(uuid4())
    job.lease_until = now + timedelta(minutes=2)
    job.updated_at = now
    session.flush()
    return job


def finish_preflight(session: Session, job_id: str, token: str, now: datetime) -> bool:
    # Fencing token prevents an expired worker from finishing a newer worker's lease.
    result = session.execute(
        update(ProductionJob)
        .where(
            ProductionJob.id == job_id,
            ProductionJob.status == "preflight",
            ProductionJob.lease_token == token,
            ProductionJob.lease_until > now,
        )
        .values(
            status="awaiting_configuration",
            lease_token=None,
            lease_until=None,
            reason="Foundation ready; live agents, benchmark and account setup are pending.",
            updated_at=now,
        )
    )
    return result.rowcount == 1


def recover_expired(session: Session, now: datetime) -> int:
    # Safe only for M1 preflight, which has no external side effects.
    jobs = session.scalars(
        select(ProductionJob)
        .where(
            ProductionJob.status == "preflight",
            ProductionJob.lease_until <= now,
        )
        .with_for_update(skip_locked=True)
    ).all()
    for job in jobs:
        job.status = "queued" if job.attempts < 3 else "failed"
        job.reason = (
            "Preflight lease expired; retry queued"
            if job.attempts < 3
            else ("Preflight failed after three leases; owner attention required")
        )
        job.lease_token = None
        job.lease_until = None
        job.updated_at = now
        if job.status == "failed":
            session.add(
                Alert(
                    dedupe_key=f"job-failed:{job.id}",
                    kind="job_failed",
                    message=f"Job {job.id} exhausted preflight retries.",
                )
            )
    session.flush()
    return len(jobs)


def schedule_day(session: Session, now: datetime, timezone: str) -> list[str]:
    local_date = now.astimezone(ZoneInfo(timezone)).date().isoformat()
    ids = []
    for slot in (1, 2):
        job, _ = create_job(
            session,
            f"daily:{local_date}:{slot}",
            {"concept": "Creative Director to propose", "date": local_date, "slot": slot},
        )
        ids.append(job.id)
    return ids


def schedule_production(session, now, timezone, times):
    """Only due local slots, with a stable key and private-by-default API separate."""
    from tsu.workflow import ProductionInput, enqueue

    local = now.astimezone(ZoneInfo(timezone))
    ids = []
    for index, value in enumerate(times):
        hour, minute = map(int, value.split(":"))
        due = local.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if due > local:
            continue
        job, _ = enqueue(
            session,
            f"daily:{local.date().isoformat()}:{index + 1}",
            ProductionInput(
                concept="A fresh original calming satisfying macro scene", visibility="public"
            ),
        )
        ids.append(job.id)
    return ids


def utcnow():
    return datetime.now(UTC)
