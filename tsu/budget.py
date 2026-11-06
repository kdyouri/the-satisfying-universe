from datetime import UTC, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from tsu.config import Settings
from tsu.models import Alert, BudgetGuard, ModelUsage


class BudgetBlocked(ValueError):
    pass


class OperationConflict(ValueError):
    pass


def _money(value: Decimal) -> Decimal:
    if not value.is_finite() or value < 0 or value != value.quantize(Decimal("0.000001")):
        raise ValueError("USD must be finite, nonnegative, with at most six decimal places")
    return value


def period_starts(now: datetime, timezone: str) -> tuple[datetime, datetime]:
    if now.tzinfo is None:
        raise ValueError("An aware timestamp is required")
    local = now.astimezone(ZoneInfo(timezone))
    day = local.replace(hour=0, minute=0, second=0, microsecond=0)
    return day.astimezone(UTC), day.replace(day=1).astimezone(UTC)


def exposure(session: Session, now: datetime, timezone: str) -> dict[str, Decimal]:
    day, month = period_starts(now, timezone)
    # Old unresolved requests remain held even after calendar rollover.
    reserved = session.scalar(
        select(func.coalesce(func.sum(ModelUsage.reserved_usd), 0)).where(
            ModelUsage.status == "reserved"
        )
    )

    def spent(start):
        return session.scalar(
            select(func.coalesce(func.sum(ModelUsage.actual_usd), 0)).where(
                ModelUsage.status == "settled", ModelUsage.settled_at >= start
            )
        )

    return {"reserved_usd": reserved, "day_spent_usd": spent(day), "month_spent_usd": spent(month)}


def _guard(session: Session) -> BudgetGuard:
    if session.bind.dialect.name != "postgresql":
        raise RuntimeError("Financial mutations require PostgreSQL row locks")
    guard = session.scalar(select(BudgetGuard).where(BudgetGuard.id == 1).with_for_update())
    if guard is None:
        raise RuntimeError("Budget guard missing; run database migrations")
    return guard


def reserve(
    session: Session,
    settings: Settings,
    operation_key: str,
    model: str,
    purpose: str,
    upper_bound_usd: Decimal,
    now: datetime,
) -> ModelUsage:
    """Caller owns transaction. Not an authorization API or live-provider submitter."""
    amount = _money(upper_bound_usd)
    if amount == 0:
        raise ValueError("Reserve a positive conservative upper bound")
    guard = _guard(session)
    existing = session.scalar(select(ModelUsage).where(ModelUsage.operation_key == operation_key))
    if existing:
        if (existing.model, existing.purpose, existing.reserved_usd) != (model, purpose, amount):
            raise OperationConflict("Operation key was already used with different inputs")
        return existing
    if not settings.spending_authorized:
        raise BudgetBlocked("Owner spending authorization is required")
    if guard.frozen:
        raise BudgetBlocked("Spending is frozen pending cost reconciliation")
    current = exposure(session, now, settings.tz)
    if (
        current["day_spent_usd"] + current["reserved_usd"] + amount > settings.daily_budget_usd
        or current["month_spent_usd"] + current["reserved_usd"] + amount
        > settings.monthly_budget_usd
    ):
        raise BudgetBlocked("Daily or monthly budget would be exceeded")
    usage = ModelUsage(
        operation_key=operation_key,
        model=model,
        purpose=purpose,
        reserved_usd=amount,
        created_at=now,
    )
    session.add(usage)
    session.flush()
    return usage


def settle(
    session: Session, operation_key: str, actual_usd: Decimal, remote_request_id: str, now: datetime
) -> ModelUsage:
    """Only verified terminal provider cost may settle; unknown cost retains reservation."""
    amount = _money(actual_usd)
    if not remote_request_id:
        raise ValueError("Provider request evidence is required")
    guard = _guard(session)
    usage = session.scalar(select(ModelUsage).where(ModelUsage.operation_key == operation_key))
    if usage is None:
        raise ValueError("No reservation exists")
    if usage.status == "settled":
        if usage.actual_usd != amount or usage.remote_request_id != remote_request_id:
            raise OperationConflict("Settlement is immutable")
        return usage
    usage.actual_usd = amount
    usage.status = "settled"
    usage.remote_request_id = remote_request_id
    usage.settled_at = now
    if amount > usage.reserved_usd:
        guard.frozen = True
        guard.reason = "Provider charge exceeded reserved upper bound"
        session.add(
            Alert(
                dedupe_key=f"overrun:{operation_key}",
                kind="cost_overrun",
                message="Cost exceeded its reservation; new spending is frozen.",
            )
        )
    session.flush()
    return usage


def record_budget_stop(session: Session, job_id: str) -> None:
    """Commit separately after rolling back a blocked reservation transaction."""
    _guard(session)
    key = f"budget:{job_id}"
    if not session.scalar(select(Alert).where(Alert.dedupe_key == key)):
        session.add(
            Alert(
                dedupe_key=key,
                kind="budget_exhausted",
                message=f"Job {job_id} stopped before paid submission: budget unavailable.",
            )
        )
