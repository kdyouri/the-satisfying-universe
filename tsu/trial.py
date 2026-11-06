"""One private end-to-end trial, only after explicit human budget authorization."""

import argparse
import json
from decimal import Decimal

from sqlalchemy import select

from tsu.budget import BudgetBlocked, exposure
from tsu.config import Settings
from tsu.db import make_engine, make_sessions
from tsu.models import ModelUsage, utcnow
from tsu.trial_policy import (
    NATIVE2_KEY,
    NATIVE2_LIMIT,
    NATIVE3_KEY,
    NATIVE3_LIMIT,
    NATIVE_KEY,
    NATIVE_LIMIT,
    NATIVE_THEME,
)
from tsu.workflow import ProductionInput, ProductionWorkflow, enqueue

KEY = "owner:reusable-private-trial:v1"
THEME = (
    "A single clear water droplet rolling slowly along the groove of a blue ceramic leaf, "
    "stationary macro camera, simple realistic motion and calming studio light"
)


def proposal():
    return {
        "theme": THEME,
        "visibility": "private",
        "maximum_new_spend_usd": "1.00",
        "maximum_reserved_stages_usd": "0.86",
        "planned_video_generation_usd": "0.80",
        "languages": ["en", "fr", "es", "it", "ru", "zh-CN"],
        "automatic_regeneration": False,
        "scheduler_enabled": False,
        "requires_explicit_human_budget_authorization": True,
    }


def run_trial(
    settings,
    engine,
    *,
    authorized=False,
    reference="",
    workflow_factory=None,
    trial_key=KEY,
    theme=THEME,
):
    if not authorized or not reference.strip():
        raise BudgetBlocked("Explicit human authorization for the scoped private trial is required")
    if (
        settings.enable_daily_scheduler
        or settings.spending_authorized
        or settings.publishing_authorized
    ):
        raise BudgetBlocked("Keep global recurring controls off during the scoped private trial")
    sessions = make_sessions(engine)
    with sessions.begin() as db:
        if trial_key not in {
            KEY,
            "owner:contextual-sound-private-trial:v1",
            NATIVE_KEY,
            NATIVE2_KEY,
            NATIVE3_KEY,
        }:
            raise BudgetBlocked("Unknown supervised trial operation")
        native = trial_key in {NATIVE_KEY, NATIVE2_KEY, NATIVE3_KEY}
        if trial_key == NATIVE_KEY and theme != NATIVE_THEME:
            raise BudgetBlocked("The fixed native trial theme changed")
        limit = "1.00"
        if native:
            limit = {
                NATIVE_KEY: NATIVE_LIMIT,
                NATIVE2_KEY: NATIVE2_LIMIT,
                NATIVE3_KEY: NATIVE3_LIMIT,
            }[trial_key]
        job, _ = enqueue(
            db,
            trial_key,
            ProductionInput(concept=theme, visibility="private"),
            legacy_profile=None
            if native
            else (
                "contextual_audio_v3" if "contextual-sound" in trial_key else "balanced_audio_v2"
            ),
        )
        if (
            job.status == "cancelled"
            or job.payload.get("owner_discarded")
            or job.payload.get("never_publish")
        ):
            raise BudgetBlocked("The owner discarded this trial; authorization cannot be restored")
        previous = job.payload.get("private_trial_authorization")
        if previous and previous.get("maximum_usd") != limit:
            raise BudgetBlocked("The trial authorization changed")
        job.payload = {
            **job.payload,
            "private_trial_authorization": {
                "job_id": job.id,
                "channel_id": settings.youtube_channel_id,
                "confirmed": True,
                "maximum_usd": limit,
                "reference": reference,
            },
        }
        charges = db.scalars(
            select(ModelUsage).where(
                ModelUsage.operation_key.startswith(job.idempotency_key + ":"),
            )
        ).all()
        committed = sum(
            (c.actual_usd if c.actual_usd is not None else c.reserved_usd) for c in charges
        )
        remaining = Decimal(limit) - committed
        if remaining < 0:
            raise BudgetBlocked("Trial cap reached; no additional paid request")
        totals = exposure(db, utcnow(), settings.tz)
        job_id = job.id
    # Only this explicit one-job context receives budget/publish authority. The saved
    # server environment and account-wide automatic-publication approval stay unchanged.
    scoped = settings.model_copy(
        update={
            "spending_authorized": True,
            "publishing_authorized": True,
            "daily_budget_usd": totals["day_spent_usd"] + totals["reserved_usd"] + remaining,
            "monthly_budget_usd": totals["month_spent_usd"] + totals["reserved_usd"] + remaining,
        }
    )
    runner = workflow_factory(scoped) if workflow_factory else ProductionWorkflow(scoped, engine)
    return runner.run(job_id)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-confirmed-private-trial", action="store_true")
    parser.add_argument("--authorization-reference", default="")
    args = parser.parse_args()
    if not args.run_confirmed_private_trial:
        print(json.dumps(proposal(), ensure_ascii=False, indent=2))
        return
    settings = Settings()
    engine = make_engine(settings.database_url.get_secret_value())
    try:
        print(
            json.dumps(
                run_trial(
                    settings, engine, authorized=True, reference=args.authorization_reference
                ),
                ensure_ascii=False,
            )
        )
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
