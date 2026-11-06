from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from decimal import Decimal
from threading import Barrier

import pytest
from sqlalchemy import func, select

from tsu.budget import (
    BudgetBlocked,
    OperationConflict,
    exposure,
    period_starts,
    record_budget_stop,
    reserve,
    settle,
)
from tsu.config import Settings
from tsu.models import Alert, BudgetGuard, ModelUsage

NOW = datetime(2026, 11, 4, 12, tzinfo=UTC)


def settings(daily="5", monthly="50", authorized=True):
    return Settings(
        _env_file=None,
        daily_budget_usd=daily,
        monthly_budget_usd=monthly,
        spending_authorized=authorized,
    )


def hold(sessions, key, amount="1", config=None, now=NOW):
    with sessions.begin() as session:
        return reserve(
            session, config or settings(), key, "test/model", "video", Decimal(amount), now
        ).id


@pytest.mark.postgres
def test_no_authorization_and_zero_budget_fail_closed(pg_sessions):
    with pytest.raises(BudgetBlocked, match="authorization"):
        hold(pg_sessions, "one", config=settings(authorized=False))
    with pytest.raises(BudgetBlocked, match="budget"):
        hold(pg_sessions, "two", config=settings(daily="0", monthly="0"))
    with pg_sessions() as session:
        assert session.scalar(select(func.count()).select_from(ModelUsage)) == 0


@pytest.mark.postgres
def test_budget_stop_alert_is_persistent_and_deduplicated(pg_sessions):
    def record(_):
        with pg_sessions.begin() as session:
            record_budget_stop(session, "stopped-job")

    with ThreadPoolExecutor(max_workers=6) as executor:
        list(executor.map(record, range(6)))
    with pg_sessions() as session:
        assert session.scalar(select(func.count()).select_from(Alert)) == 1


@pytest.mark.postgres
def test_concurrent_reservations_cannot_exceed_cap(pg_sessions):
    barrier = Barrier(10)

    def attempt(index):
        barrier.wait()
        try:
            hold(pg_sessions, f"concurrent:{index}")
            return True
        except BudgetBlocked:
            return False

    with ThreadPoolExecutor(max_workers=10) as executor:
        assert sum(executor.map(attempt, range(10))) == 5
    with pg_sessions() as session:
        assert exposure(session, NOW, "Africa/Casablanca")["reserved_usd"] == Decimal("5")


@pytest.mark.postgres
def test_concurrent_duplicate_reservation_and_conflict(pg_sessions):
    with ThreadPoolExecutor(max_workers=6) as executor:
        ids = list(executor.map(lambda _: hold(pg_sessions, "same"), range(6)))
    assert len(set(ids)) == 1
    with pytest.raises(OperationConflict):
        hold(pg_sessions, "same", "2")


@pytest.mark.postgres
def test_old_unresolved_holds_survive_day_and_month_rollover(pg_sessions):
    hold(pg_sessions, "old", "4", now=datetime(2026, 10, 31, 12, tzinfo=UTC))
    with pytest.raises(BudgetBlocked):
        hold(pg_sessions, "today", "2")
    with pg_sessions.begin() as session:
        settle(session, "old", Decimal("1"), "remote-old", NOW)
    hold(pg_sessions, "today", "4")
    with pytest.raises(BudgetBlocked):
        hold(pg_sessions, "monthly", "1", config=settings(daily="50", monthly="5"))


@pytest.mark.postgres
def test_settlement_is_immutable_and_overrun_freezes(pg_sessions):
    hold(pg_sessions, "overrun")
    with pg_sessions.begin() as session:
        settle(session, "overrun", Decimal("2"), "remote1", NOW)
    with pg_sessions.begin() as session:
        settle(session, "overrun", Decimal("2"), "remote1", NOW)
    with pytest.raises(OperationConflict), pg_sessions.begin() as session:
        settle(session, "overrun", Decimal("1"), "remote1", NOW)
    with pytest.raises(BudgetBlocked, match="frozen"):
        hold(pg_sessions, "blocked")
    with pg_sessions() as session:
        assert session.get(BudgetGuard, 1).frozen
        assert session.scalar(select(func.count()).select_from(Alert)) == 1


@pytest.mark.parametrize(
    ("now", "expected_day", "expected_month"),
    [
        # IANA 2026: Casablanca returned to UTC in September; do not hardcode +01.
        (
            datetime(2026, 11, 4, 0, 30, tzinfo=UTC),
            datetime(2026, 11, 4, tzinfo=UTC),
            datetime(2026, 11, 1, tzinfo=UTC),
        ),
        (
            datetime(2026, 6, 4, 0, 30, tzinfo=UTC),
            datetime(2026, 6, 3, 23, tzinfo=UTC),
            datetime(2026, 5, 31, 23, tzinfo=UTC),
        ),
    ],
)
def test_local_budget_boundary_uses_casablanca(now, expected_day, expected_month):
    day, month = period_starts(now, "Africa/Casablanca")
    assert day == expected_day
    assert month == expected_month


@pytest.mark.postgres
@pytest.mark.parametrize("value", ["NaN", "Infinity", "-1", "0.0000001", "0"])
def test_invalid_financial_inputs(pg_sessions, value):
    with pytest.raises(ValueError):
        hold(pg_sessions, "invalid", value)
