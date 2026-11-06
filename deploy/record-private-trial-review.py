"""Record follow-up consent and the remaining reconciliation alert; no provider call."""

import hashlib
import json

from sqlalchemy import select

from tsu.config import Settings
from tsu.db import make_engine, make_sessions
from tsu.models import Alert, ProductionJob
from tsu.trial import KEY

settings = Settings()
assert not any(
    (settings.spending_authorized, settings.publishing_authorized, settings.enable_daily_scheduler)
)
engine = make_engine(settings.database_url.get_secret_value())
try:
    with make_sessions(engine).begin() as db:
        key = "production:" + hashlib.sha256(KEY.encode()).hexdigest()
        job = db.scalar(
            select(ProductionJob).where(ProductionJob.idempotency_key == key).with_for_update()
        )
        assert job.status == "completed_private"
        calls = job.payload["calls"]
        assert calls["quality_balanced_audio_v2_supervised_corrected1"]["state"] == "done"
        assert calls["quality_balanced_audio_v2_supervised_diagnostic1"]["state"] == "submitting"
        job.payload = {
            **job.payload,
            "explicit_additional_review_authorization": {
                "source": "Direct owner reply in this chat after approval-review rejection",
                "answer": "Oui, deux appels maximum, total limité à 1 USD",
                "maximum_additional_calls": 2,
                "calls_used": [
                    "quality_balanced_audio_v2_supervised_diagnostic1",
                    "quality_balanced_audio_v2_supervised_corrected1",
                ],
                "trial_total_cap_usd": "1.00",
                "no_regeneration": True,
                "scheduler_remains_off": True,
            },
        }
        alert = db.scalar(
            select(Alert).where(Alert.dedupe_key == f"production:{job.id}:owner_attention")
        )
        if alert:
            alert.kind = "cost_reconciliation"
            alert.message = (
                "Essai privé terminé après revue supervisée (91/100). "
                "0,14 USD restent réservés pour trois contrôles sans coût individuel réconcilié. "
                "Ne pas répéter ces requêtes ni effacer leurs réservations."
            )
        print(
            json.dumps(
                {
                    "followup_consent_recorded": True,
                    "remaining_alert": "cost_reconciliation",
                    "new_paid_calls": 0,
                    "new_uploads": 0,
                }
            )
        )
finally:
    engine.dispose()
