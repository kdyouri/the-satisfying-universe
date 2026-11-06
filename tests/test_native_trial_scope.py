"""Offline checks of the single-job grant and remaining-cap calculation, no provider calls."""

from decimal import Decimal
from types import SimpleNamespace

import pytest
from sqlalchemy import func, select

from tsu.budget import BudgetBlocked
from tsu.config import Settings
from tsu.db import make_sessions
from tsu.models import ModelUsage, ProductionJob, utcnow
from tsu.native_profile import native_profile
from tsu.native_trial import proposal
from tsu.trial import run_trial
from tsu.trial_policy import (
    NATIVE2_DURABLE_KEY,
    NATIVE2_KEY,
    NATIVE2_LIMIT,
    NATIVE2_THEME,
    NATIVE3_DURABLE_KEY,
    NATIVE3_KEY,
    NATIVE3_LIMIT,
    NATIVE3_THEME,
    NATIVE_DURABLE_KEY,
    NATIVE_KEY,
    NATIVE_LIMIT,
    NATIVE_THEME,
    private_trial_authorized,
)


def grant_job():
    return SimpleNamespace(
        id="native-job",
        idempotency_key=NATIVE_DURABLE_KEY,
        status="running",
        payload={
            "visibility": "private",
            "production_profile": native_profile(),
            "private_trial_authorization": {
                "job_id": "native-job",
                "channel_id": "channel",
                "confirmed": True,
                "maximum_usd": NATIVE_LIMIT,
            },
        },
    )


def grant_job_v2():
    job = grant_job()
    job.idempotency_key = NATIVE2_DURABLE_KEY
    job.payload["private_trial_authorization"]["maximum_usd"] = NATIVE2_LIMIT
    return job


def test_native_private_grant_is_bound_to_one_job_channel_key_and_cap():
    job = grant_job()
    assert private_trial_authorized(job, "private", "channel")
    assert not private_trial_authorized(job, "public", "channel")
    assert not private_trial_authorized(job, "private", "other-channel")
    job.idempotency_key = "another-operation"
    assert not private_trial_authorized(job, "private", "channel")


def test_native_v2_private_grant_is_bound_to_its_own_key_and_cap():
    job = grant_job_v2()
    assert private_trial_authorized(job, "private", "channel")
    job.payload["private_trial_authorization"]["maximum_usd"] = NATIVE_LIMIT
    assert not private_trial_authorized(job, "private", "channel")
    job.payload["private_trial_authorization"]["maximum_usd"] = NATIVE2_LIMIT
    job.idempotency_key = NATIVE_DURABLE_KEY
    assert not private_trial_authorized(job, "private", "channel")
    job.idempotency_key = NATIVE2_DURABLE_KEY
    assert not private_trial_authorized(job, "public", "channel")
    job.payload["private_trial_authorization"]["withdrawn_by_owner"] = True
    assert not private_trial_authorized(job, "private", "channel")


@pytest.mark.parametrize(
    "field,value",
    [
        ("job_id", "other-job"),
        ("channel_id", "other-channel"),
        ("maximum_usd", "1.00"),
        ("maximum_usd", "1.71"),
        ("confirmed", False),
        ("withdrawn_by_owner", True),
    ],
)
def test_wrong_or_withdrawn_native_grant_is_not_upload_authority(field, value):
    job = grant_job()
    job.payload["private_trial_authorization"][field] = value
    assert not private_trial_authorized(job, "private", "channel")


@pytest.mark.parametrize("field", ["owner_discarded", "never_publish"])
def test_discarded_native_grant_is_not_upload_authority(field):
    job = grant_job()
    job.payload[field] = True
    assert not private_trial_authorized(job, "private", "channel")


def test_native_trial_proposal_has_no_montage_or_schedule():
    plan = proposal()
    assert plan["maximum_additional_usd"] == "1.70"
    assert plan["profile"]["clip_count"] == 1 and plan["profile"]["duration"] == 15
    assert plan["profile"]["generate_audio"] and not plan["profile"]["postproduction"]
    assert plan["visibility"] == "private" and not plan["scheduler_activation"]


def test_native_trial_v2_proposal_has_free_theme_and_two_dollar_cap():
    plan = proposal("v2")
    assert plan["operation"] == NATIVE2_KEY
    assert plan["maximum_additional_usd"] == "2.00"
    assert plan["theme"] == NATIVE2_THEME and "chosen freely" in plan["theme"]
    assert plan["profile"]["clip_count"] == 1 and plan["profile"]["duration"] == 15
    assert plan["profile"]["generate_audio"] and not plan["profile"]["postproduction"]
    assert plan["visibility"] == "private" and not plan["scheduler_activation"]


def test_native_trial_v3_proposal_is_veo_native_audio_one_dollar_cap():
    plan = proposal("v3")
    assert plan["operation"] == NATIVE3_KEY
    assert plan["maximum_additional_usd"] == "1.00"
    assert plan["theme"] == NATIVE3_THEME and "chosen freely" in plan["theme"]
    assert plan["profile"]["version"] == "native_audio_v5"
    assert plan["profile"]["model"] == "google/veo-3.1-lite"
    assert plan["profile"]["clip_count"] == 1 and plan["profile"]["duration"] == 8
    assert plan["profile"]["generate_audio"] and not plan["profile"]["postproduction"]
    assert plan["profile"]["maximum_generation_usd"] == "0.70"
    assert plan["visibility"] == "private" and not plan["scheduler_activation"]


def test_native_v2_scope_accepts_a_free_theme_and_preserves_old_holds(local_engine):
    settings = Settings(_env_file=None, youtube_channel_id="channel")
    sessions = make_sessions(local_engine)
    with sessions.begin() as db:
        db.add_all(
            [
                ModelUsage(
                    operation_key="old:paid",
                    model="synthetic",
                    purpose="test",
                    reserved_usd=Decimal("2.4"),
                    actual_usd=Decimal("2.4"),
                    status="settled",
                    remote_request_id="old",
                    settled_at=utcnow(),
                ),
                ModelUsage(
                    operation_key="old:uncertain",
                    model="synthetic",
                    purpose="test",
                    reserved_usd=Decimal("0.3"),
                ),
            ]
        )
    scopes = []

    def factory(scoped):
        scopes.append(scoped)
        return SimpleNamespace(
            run=lambda job_id: {"job_id": job_id, "status": "offline_scope_only"}
        )

    free_theme = "A fresh original satisfying macro subject of the model's own choice."

    def run():
        return run_trial(
            settings,
            local_engine,
            authorized=True,
            reference="synthetic-owner-consent-v2",
            trial_key=NATIVE2_KEY,
            theme=free_theme,
            workflow_factory=factory,
        )

    first = run()
    assert scopes[-1].spending_authorized and scopes[-1].publishing_authorized
    assert scopes[-1].daily_budget_usd == scopes[-1].monthly_budget_usd == Decimal("4.70")
    assert not scopes[-1].enable_daily_scheduler
    assert not settings.spending_authorized and not settings.publishing_authorized
    assert settings.daily_budget_usd == settings.monthly_budget_usd == 0
    with sessions.begin() as db:
        job = db.get(ProductionJob, first["job_id"])
        assert job.idempotency_key == NATIVE2_DURABLE_KEY
        assert job.payload["private_trial_authorization"]["maximum_usd"] == NATIVE2_LIMIT
        assert job.payload["production_profile"]["version"] == "native_audio_v5"
        db.add(
            ModelUsage(
                operation_key=job.idempotency_key + ":uncertain",
                model="synthetic",
                purpose="test",
                reserved_usd=Decimal("0.05"),
            )
        )
    assert run()["job_id"] == first["job_id"]
    assert scopes[-1].daily_budget_usd == scopes[-1].monthly_budget_usd == Decimal("4.70")
    with sessions.begin() as db:
        assert db.scalar(select(func.count()).select_from(ProductionJob)) == 1
        assert (
            db.scalar(
                select(ModelUsage).where(ModelUsage.operation_key == "old:uncertain")
            ).actual_usd
            is None
        )


def test_native_v3_scope_accepts_free_theme_and_veo_profile(local_engine):
    settings = Settings(_env_file=None, youtube_channel_id="channel")
    sessions = make_sessions(local_engine)
    with sessions.begin() as db:
        db.add_all(
            [
                ModelUsage(
                    operation_key="old:paid",
                    model="synthetic",
                    purpose="test",
                    reserved_usd=Decimal("2.4"),
                    actual_usd=Decimal("2.4"),
                    status="settled",
                    remote_request_id="old",
                    settled_at=utcnow(),
                ),
                ModelUsage(
                    operation_key="old:uncertain",
                    model="synthetic",
                    purpose="test",
                    reserved_usd=Decimal("0.3"),
                ),
            ]
        )
    scopes = []

    def factory(scoped):
        scopes.append(scoped)
        return SimpleNamespace(
            run=lambda job_id: {"job_id": job_id, "status": "offline_scope_only"}
        )

    def run():
        return run_trial(
            settings,
            local_engine,
            authorized=True,
            reference="synthetic-owner-consent-v3",
            trial_key=NATIVE3_KEY,
            theme=NATIVE3_THEME,
            workflow_factory=factory,
        )

    first = run()
    assert scopes[-1].spending_authorized and scopes[-1].publishing_authorized
    assert scopes[-1].daily_budget_usd == scopes[-1].monthly_budget_usd == Decimal("3.70")
    assert not scopes[-1].enable_daily_scheduler
    assert not settings.spending_authorized and not settings.publishing_authorized
    assert settings.daily_budget_usd == settings.monthly_budget_usd == 0
    with sessions.begin() as db:
        job = db.get(ProductionJob, first["job_id"])
        assert job.idempotency_key == NATIVE3_DURABLE_KEY
        assert job.payload["private_trial_authorization"]["maximum_usd"] == NATIVE3_LIMIT
        assert job.payload["production_profile"]["version"] == "native_audio_v5"
        assert job.payload["production_profile"]["model"] == "google/veo-3.1-lite"


def test_native_v1_fixed_theme_stays_enforced_and_v2_requires_authorization(local_engine):
    settings = Settings(_env_file=None, youtube_channel_id="channel")
    with pytest.raises(BudgetBlocked, match="theme changed"):
        run_trial(
            settings,
            local_engine,
            authorized=True,
            reference="synthetic",
            trial_key=NATIVE_KEY,
            theme="changed theme",
        )
    with pytest.raises(BudgetBlocked):
        run_trial(
            settings,
            local_engine,
            trial_key=NATIVE2_KEY,
            theme=NATIVE2_THEME,
        )
    with make_sessions(local_engine)() as db:
        assert db.scalar(select(func.count()).select_from(ProductionJob)) == 0


def test_native_scope_remaining_budget_preserves_global_flags_and_old_holds(local_engine):
    settings = Settings(_env_file=None, youtube_channel_id="channel")
    sessions = make_sessions(local_engine)
    with sessions.begin() as db:
        db.add_all(
            [
                ModelUsage(
                    operation_key="old:paid",
                    model="synthetic",
                    purpose="test",
                    reserved_usd=Decimal("2.4"),
                    actual_usd=Decimal("2.4"),
                    status="settled",
                    remote_request_id="old",
                    settled_at=utcnow(),
                ),
                ModelUsage(
                    operation_key="old:uncertain",
                    model="synthetic",
                    purpose="test",
                    reserved_usd=Decimal("0.3"),
                ),
            ]
        )
    scopes = []

    def factory(scoped):
        scopes.append(scoped)
        return SimpleNamespace(
            run=lambda job_id: {"job_id": job_id, "status": "offline_scope_only"}
        )

    def run():
        return run_trial(
            settings,
            local_engine,
            authorized=True,
            reference="synthetic-owner-consent",
            trial_key=NATIVE_KEY,
            theme=NATIVE_THEME,
            workflow_factory=factory,
        )

    first = run()
    assert scopes[-1].spending_authorized and scopes[-1].publishing_authorized
    assert scopes[-1].daily_budget_usd == scopes[-1].monthly_budget_usd == Decimal("4.40")
    assert not scopes[-1].enable_daily_scheduler
    assert not settings.spending_authorized and not settings.publishing_authorized
    assert settings.daily_budget_usd == settings.monthly_budget_usd == 0
    with sessions.begin() as db:
        job = db.get(ProductionJob, first["job_id"])
        assert job.payload["private_trial_authorization"]["maximum_usd"] == NATIVE_LIMIT
        assert job.payload["production_profile"]["version"] == "native_audio_v5"
        db.add(
            ModelUsage(
                operation_key=job.idempotency_key + ":uncertain",
                model="synthetic",
                purpose="test",
                reserved_usd=Decimal("0.05"),
            )
        )
    assert run()["job_id"] == first["job_id"]
    assert scopes[-1].daily_budget_usd == scopes[-1].monthly_budget_usd == Decimal("4.40")
    with sessions.begin() as db:
        assert db.scalar(select(func.count()).select_from(ProductionJob)) == 1
        assert (
            db.scalar(
                select(ModelUsage).where(ModelUsage.operation_key == "old:uncertain")
            ).actual_usd
            is None
        )
        job = db.get(ProductionJob, first["job_id"])
        job.status = "cancelled"
        job.payload = {**job.payload, "owner_discarded": True}
    with pytest.raises(BudgetBlocked, match="discarded"):
        run()
    assert len(scopes) == 2


@pytest.mark.parametrize(
    "override",
    [
        {},
        {"authorized": True},
        {"authorized": True, "reference": "synthetic", "theme": "changed theme"},
        {"authorized": True, "reference": "synthetic", "trial_key": "unknown"},
    ],
)
def test_native_scope_cannot_start_without_the_fixed_explicit_authorization(local_engine, override):
    kwargs = {"trial_key": NATIVE_KEY, "theme": NATIVE_THEME, **override}
    with pytest.raises(BudgetBlocked):
        run_trial(Settings(_env_file=None), local_engine, **kwargs)
    with make_sessions(local_engine)() as db:
        assert db.scalar(select(func.count()).select_from(ProductionJob)) == 0
