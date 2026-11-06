"""One supervised review of existing trial media within the owner's original 1 USD cap.

The uncertain original call and its reservation remain untouched. This separate operation
never generates media, uploads, changes global controls, or installs an automatic retry.
Without --execute, only inspect the media and compute the remaining scoped budget.
"""

import base64
import hashlib
import json
import os
import re
import sys
from decimal import Decimal

from sqlalchemy import select

from tsu.budget import exposure
from tsu.config import Settings
from tsu.contracts import PracticalReview
from tsu.db import make_engine, make_sessions
from tsu.media import inspect_final
from tsu.models import Concept, ModelUsage, ProductionJob, QualityCheck, Video, utcnow
from tsu.openrouter import OpenRouter
from tsu.pilot import first_video_lock
from tsu.production import SOUNDTRACK, production_profile, review_instruction
from tsu.trial import KEY
from tsu.workflow import JobProducer, ProductionBrief, workflow_lock

STAGE = os.environ.get(
    "TSU_SUPERVISED_REVIEW_STAGE", "quality_balanced_audio_v2_supervised_recovery1"
)
assert STAGE in {
    "quality_balanced_audio_v2_supervised_recovery1",
    "quality_balanced_audio_v2_supervised_diagnostic1",
    "quality_balanced_audio_v2_supervised_corrected1",
}
ALLOWANCE = "0.04" if STAGE.endswith("diagnostic1") else "0.05"
settings = Settings()
assert not any(
    (settings.enable_daily_scheduler, settings.spending_authorized, settings.publishing_authorized)
)
assert settings.daily_budget_usd == settings.monthly_budget_usd == 0
engine = make_engine(settings.database_url.get_secret_value())
sessions = make_sessions(engine)
provider = None
try:
    with workflow_lock(engine), first_video_lock(engine):
        key = "production:" + hashlib.sha256(KEY.encode()).hexdigest()
        with sessions() as db:
            job = db.scalar(select(ProductionJob).where(ProductionJob.idempotency_key == key))
            assert job.payload["visibility"] == "private"
            auth = job.payload["private_trial_authorization"]
            assert auth["confirmed"] and auth["maximum_usd"] == "1.00"
            assert auth["job_id"] == job.id and auth["channel_id"] == settings.youtube_channel_id
            if job.payload.get("result"):
                print(json.dumps({"already_recorded": True, "job_id": job.id}))
                sys.exit(0)
            assert job.status == "owner_attention"
            original = job.payload["calls"]["quality_balanced_audio_v2"]
            assert original["state"] == "submitting"
            assert job.reason == "Provider connection failed; do not repeat a paid submission"
            charges = db.scalars(
                select(ModelUsage).where(ModelUsage.operation_key.startswith(key + ":"))
            ).all()
            committed = sum(
                x.actual_usd if x.actual_usd is not None else x.reserved_usd for x in charges
            )
            remaining = Decimal("1") - committed
            assert remaining >= Decimal(ALLOWANCE)
            totals = exposure(db, utcnow(), settings.tz)
            job_id = job.id
            brief = ProductionBrief.model_validate(db.get(Concept, job.concept_id).brief)
        scoped = settings.model_copy(
            update={
                "spending_authorized": True,
                "daily_budget_usd": totals["day_spent_usd"] + totals["reserved_usd"] + remaining,
                "monthly_budget_usd": totals["month_spent_usd"]
                + totals["reserved_usd"]
                + remaining,
            }
        )
        folder = settings.data_root / "jobs" / job_id
        final, review = folder / "first-video.mp4", folder / "review.mp4"
        technical = inspect_final(final, require_audio=True)
        assert technical["technical_pass"] and review.stat().st_size <= 6 * 1024 * 1024
        seconds = float(technical["metadata"]["format"]["duration"])
        content = [
            {"type": "text", "text": review_instruction(brief.concept, seconds)},
            {
                "type": "video_url",
                "video_url": {
                    "url": "data:video/mp4;base64," + base64.b64encode(review.read_bytes()).decode()
                },
            },
        ]
        assert (
            hashlib.sha256(json.dumps(content, sort_keys=True).encode()).hexdigest()
            == original["input_hash"]
        )
        audit = {
            "job_id": job_id,
            "technical_pass": True,
            "duration_seconds": seconds,
            "audio_levels": technical["audio_levels"],
            "master_bytes": final.stat().st_size,
            "review_bytes": review.stat().st_size,
            "committed_including_uncertain_usd": str(committed),
            "additional_review_reservation_usd": ALLOWANCE,
            "maximum_total_after_reservation_usd": str(committed + Decimal(ALLOWANCE)),
            "original_uncertain_call_preserved": True,
            "new_video_generations": 0,
        }
        print(json.dumps(audit), flush=True)
        if "--execute" not in sys.argv[1:]:
            sys.exit(0)

        class CompatibleReview(OpenRouter):
            def json(self, method, path, body=None):
                if (
                    method == "POST"
                    and path == "/chat/completions"
                    and STAGE.endswith("corrected1")
                ):
                    body = json.loads(json.dumps(body))

                    # Native Gemini schema compilation can reject complex constraints.
                    # Keep their full enforcement in PracticalReview below, while sending
                    # only structure/types/enums/required fields to the provider.
                    def simplify(value):
                        if isinstance(value, dict):
                            for key in (
                                "minimum",
                                "maximum",
                                "minLength",
                                "maxLength",
                                "minItems",
                                "maxItems",
                                "title",
                            ):
                                value.pop(key, None)
                            for child in value.values():
                                simplify(child)
                        elif isinstance(value, list):
                            for child in value:
                                simplify(child)

                    simplify(body["response_format"]["json_schema"]["schema"])
                    # Avoid the newly cheapest Flex variants for this controlled recovery;
                    # the historical successful review used Google AI Studio standard.
                    body["provider"].update(
                        only=["google-ai-studio"],
                        ignore=["google-ai-studio/flex", "google-ai-studio/priority"],
                    )
                return super().json(method, path, body)

        provider = CompatibleReview(
            settings.openrouter_api_key.get_secret_value(), timeout=(10, 300)
        )

        def capture_error(response, **kwargs):
            if response.status_code >= 400:
                safe = re.sub(
                    r"data:[^\s\"]+;base64,[A-Za-z0-9+/=]+",
                    "[media omitted]",
                    response.text[:65536],
                )
                safe = re.sub(
                    r"sk-or-v1-[A-Za-z0-9_-]+|Bearer [A-Za-z0-9._-]+", "[credential omitted]", safe
                )
                name = "/data/validation/private-review-http-error-20261105.json"
                descriptor = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
                with os.fdopen(descriptor, "w") as target:
                    json.dump(
                        {
                            "stage": STAGE,
                            "status_code": response.status_code,
                            "generation_id": response.headers.get("X-Generation-Id"),
                            "body": safe,
                        },
                        target,
                    )

        provider.session.hooks["response"].append(capture_error)
        producer = JobProducer(scoped, engine, provider, job_id)
        producer.verify_catalogue()
        raw = producer.chat(
            STAGE,
            content,
            PracticalReview.model_json_schema(),
            ALLOWANCE,
            scoped.quality_model,
            producer.price_limits["quality_model"],
        )
        quality = PracticalReview.model_validate_json(raw)
        decision = quality.decision(technical_pass=True, duration_seconds=seconds)
        with final.open("rb") as source:
            digest = hashlib.file_digest(source, "sha256").hexdigest()
        editing = {
            **production_profile(),
            "duration_seconds": seconds,
            "soundtrack_sha256": hashlib.sha256(SOUNDTRACK.read_bytes()).hexdigest(),
            "soundtrack_source": "original local synthesis; no external samples",
        }
        with sessions.begin() as db:
            job = producer.job(db, locked=True)
            generation = producer.generation(db, 0)
            assert not db.scalar(select(Video).where(Video.generation_id == generation.id))
            video = Video(
                concept_id=job.concept_id,
                generation_id=generation.id,
                original_key=str(folder / "clip-1.mp4"),
                final_key=str(final),
                sha256=digest,
                technical_metadata={
                    **technical,
                    "source_clips": [str(folder / f"clip-{n}.mp4") for n in (1, 2)],
                    "editing": editing,
                },
                status="running" if decision == "accepted" else "awaiting_owner_review",
            )
            db.add(video)
            db.flush()
            db.add(
                QualityCheck(
                    video_id=video.id,
                    model=scoped.quality_model,
                    score=quality.total,
                    technical_pass=True,
                    approved=decision == "accepted",
                    details=quality.model_dump(),
                    rejection_reason=None if decision == "accepted" else decision,
                )
            )
            charges = db.scalars(
                select(ModelUsage).where(ModelUsage.operation_key.startswith(key + ":"))
            ).all()
            result = {
                "job_id": job_id,
                "video_id": video.id,
                "file": str(final),
                "title": brief.title,
                "sha256": digest,
                "technical_pass": True,
                "quality_score": quality.total,
                "quality_pass": decision == "accepted",
                "quality_decision": decision,
                "production_profile": editing,
                "issues": [x.model_dump() for x in quality.issues],
                "severe_defects": quality.severe_defects,
                "actual_cost_usd": str(sum(x.actual_usd or Decimal(0) for x in charges)),
                "unsettled_reservations": sum(x.actual_usd is None for x in charges),
                "published": False,
                "scheduler_enabled": False,
                "automatic_regeneration": False,
            }
            job.payload = {
                **job.payload,
                "result": result,
                "supervised_review_recovery": {
                    "stage": STAGE,
                    "scope": "same private trial, original owner 1 USD cap",
                    "uncertain_original_preserved": True,
                },
            }
            job.status = (
                "running"
                if decision == "accepted"
                else (
                    "awaiting_local_edit" if decision == "local_edit" else "awaiting_owner_review"
                )
            )
            job.reason = None if decision == "accepted" else decision
            job.updated_at = utcnow()
        (folder / "result.json").write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps(result, ensure_ascii=False), flush=True)
finally:
    if provider:
        provider.session.close()
    engine.dispose()
