"""Prepare one separately authorized review of the existing contextual-sound trial.

Default is read-only. Preserve the uncertain original review and its full reservation.
No video generation, source edit, recurring activation or automatic paid retry.
"""

import argparse
import hashlib
import json
import time
from decimal import Decimal

import requests
from sqlalchemy import select

from tsu.budget import exposure
from tsu.config import Settings
from tsu.db import make_engine, make_sessions
from tsu.media import inspect_final
from tsu.models import Concept, ModelUsage, ProductionJob, utcnow
from tsu.production import production_profile
from tsu.sound_design import contextual_profile
from tsu.sound_trial import KEY
from tsu.workflow import JobProducer, ProductionBrief, ProductionWorkflow, workflow_lock

STAGE = "quality_contextual_audio_v3_supervised1"
TRANSPORT_FIXED_STAGE = "quality_contextual_audio_v3_supervised_transport_fixed1"
MASTER_SHA = "4d2b9396eab125cf6b5c907e52cfeebc6a7aa3830f66c13db49824bcf74a1a4a"
REVIEW_SHA = "0ada6cbb9774e724bc9545c2b7f78524189619b7ad0284edb203a587ef1a6fad"


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--authorization-reference", default="")
    parser.add_argument("--stage", choices=(STAGE, TRANSPORT_FIXED_STAGE), default=STAGE)
    args = parser.parse_args()
    stage = args.stage
    if args.execute and not args.authorization_reference.strip():
        raise ValueError("A fresh explicit authorization for this additional review is required")
    settings = Settings()
    assert not any(
        (
            settings.enable_daily_scheduler,
            settings.spending_authorized,
            settings.publishing_authorized,
        )
    )
    assert settings.daily_budget_usd == settings.monthly_budget_usd == 0
    engine = make_engine(settings.database_url.get_secret_value())
    sessions = make_sessions(engine)
    provider = None
    try:
        with workflow_lock(engine):
            key = "production:" + hashlib.sha256(KEY.encode()).hexdigest()
            with sessions() as db:
                job = db.scalar(select(ProductionJob).where(ProductionJob.idempotency_key == key))
                assert job.payload["visibility"] == "private"
                auth = job.payload["private_trial_authorization"]
                assert auth["confirmed"] and auth["maximum_usd"] == "1.00"
                assert (
                    auth["job_id"] == job.id and auth["channel_id"] == settings.youtube_channel_id
                )
                if job.payload.get("result") or stage in job.payload.get("calls", {}):
                    print(json.dumps({"already_attempted": True, "job_id": job.id}))
                    return
                assert job.status == "owner_attention"
                assert job.payload["calls"]["quality_contextual_audio_v3"]["state"] == "submitting"
                if stage == TRANSPORT_FIXED_STAGE:
                    assert job.payload["calls"][STAGE]["state"] == "submitting"
                charges = db.scalars(
                    select(ModelUsage).where(ModelUsage.operation_key.startswith(key + ":"))
                ).all()
                committed = sum(
                    (c.actual_usd if c.actual_usd is not None else c.reserved_usd for c in charges),
                    Decimal(0),
                )
                assert committed + Decimal("0.05") <= Decimal("1.00")
                job_id = job.id
                brief = ProductionBrief.model_validate(db.get(Concept, job.concept_id).brief)
                totals = exposure(db, utcnow(), settings.tz)
            directory = settings.data_root / "jobs" / job_id
            master, review = directory / "first-video.mp4", directory / "review.mp4"
            effects = master.with_suffix(".effects.wav")
            assert digest(master) == MASTER_SHA and digest(review) == REVIEW_SHA
            technical = inspect_final(master, require_audio=True)
            assert technical["technical_pass"] and review.stat().st_size <= 6 * 1024 * 1024
            assert brief.sound_plan.kind == "liquid_flow"
            editing = {
                **production_profile(effects),
                **contextual_profile(),
                "sound_plan": brief.sound_plan.model_dump(),
                "duration_seconds": float(technical["metadata"]["format"]["duration"]),
                "soundtrack_sha256": digest(effects),
                "soundtrack_source": (
                    "original locally synthesized action effects; no external samples"
                ),
            }
            print(
                json.dumps(
                    {
                        "job_id": job_id,
                        "technical_pass": True,
                        "existing_master_sha256": MASTER_SHA,
                        "committed_including_uncertain_usd": str(committed),
                        "additional_review_reservation_usd": "0.05",
                        "maximum_total_after_reservation_usd": str(committed + Decimal("0.05")),
                        "new_video_generations": 0,
                        "original_uncertain_call_preserved": True,
                        "execute": args.execute,
                        "additional_stage": stage,
                    }
                ),
                flush=True,
            )
            if not args.execute:
                return
            remaining = Decimal(1) - committed
            scoped = settings.model_copy(
                update={
                    "spending_authorized": True,
                    "publishing_authorized": True,
                    "daily_budget_usd": totals["day_spent_usd"]
                    + totals["reserved_usd"]
                    + remaining,
                    "monthly_budget_usd": totals["month_spent_usd"]
                    + totals["reserved_usd"]
                    + remaining,
                }
            )

            class ExistingMediaReview(JobProducer):
                def render(self, clips, final, saved_brief):
                    assert final == master and digest(final) == MASTER_SHA
                    return editing

                def chat(self, stage, *parameters, **options):
                    if stage == "quality_contextual_audio_v3":
                        selected_stage = args.stage
                    elif stage == "creative":
                        selected_stage = stage
                    else:
                        raise ValueError("Unexpected paid stage")
                    return super().chat(selected_stage, *parameters, **options)

            workflow = ProductionWorkflow(scoped, engine)
            provider = workflow.provider_factory()
            original_request = provider.session.request

            def record_connection_result(method, url, **options):
                started = time.monotonic()
                try:
                    response = original_request(method, url, **options)
                except requests.RequestException as error:
                    print(
                        json.dumps(
                            {
                                "safe_connection_error_type": type(error).__name__,
                                "elapsed_seconds": round(time.monotonic() - started, 2),
                                "automatic_retry": False,
                            }
                        ),
                        flush=True,
                    )
                    raise
                if method == "POST" and url.endswith("/chat/completions"):
                    print(
                        json.dumps(
                            {
                                "review_http_status": response.status_code,
                                "elapsed_seconds": round(time.monotonic() - started, 2),
                            }
                        ),
                        flush=True,
                    )
                return response

            provider.session.request = record_connection_result
            producer = ExistingMediaReview(scoped, engine, provider, job_id)
            with sessions.begin() as db:
                job = db.get(ProductionJob, job_id)
                job.payload = {
                    **job.payload,
                    "supervised_review_recovery": {
                        "stage": stage,
                        "reference": args.authorization_reference,
                        "uncertain_original_preserved": True,
                        "maximum_total_usd": "1.00",
                    },
                }
            result = producer.run()
            assert digest(master) == MASTER_SHA
            print(json.dumps({"review_result": result}, ensure_ascii=False), flush=True)
        # The normal workflow reuses the persisted result. Its upload still requires
        # approved quality and the existing one-video private channel authorization.
        print(json.dumps(ProductionWorkflow(scoped, engine).run(job_id)), flush=True)
    finally:
        if provider:
            provider.session.close()
        engine.dispose()


if __name__ == "__main__":
    main()
