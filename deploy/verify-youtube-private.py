"""Read-only checks of persisted upload state and unchanged production gates."""

import hashlib
import json
import os
from decimal import Decimal
from pathlib import Path

import requests
from sqlalchemy import func, select

from tsu.config import Settings
from tsu.db import make_engine, make_sessions
from tsu.models import (
    ModelUsage,
    ProductionJob,
    Publication,
    SocialAccount,
    SystemSetting,
    Video,
    VideoGeneration,
)
from tsu.youtube_upload import OPERATION, PrivateTestUpload

settings = Settings()
engine = make_engine(settings.database_url.get_secret_value())
service = PrivateTestUpload(settings, engine)
snapshot = service.snapshot()
service.close()
assert snapshot["status"] == "processed_private", snapshot["status"]
assert snapshot["verified"]["privacy"] == "private"
assert snapshot["verified"]["channel_id"] == settings.youtube_channel_id
assert not any(
    (settings.spending_authorized, settings.publishing_authorized, settings.enable_daily_scheduler)
)
assert settings.daily_budget_usd == settings.monthly_budget_usd == 0
with make_sessions(engine)() as db:

    def count(model):
        return db.scalar(select(func.count()).select_from(model))

    generations, publications, usage = count(VideoGeneration), count(Publication), count(ModelUsage)
    assert (generations, publications, usage) == (2, 1, 5)
    confirmed = db.scalar(select(func.sum(ModelUsage.actual_usd)))
    assert confirmed == Decimal("0.800526")
    original = db.scalar(
        select(ProductionJob).where(ProductionJob.idempotency_key == "owner:first-video:v1")
    )
    assert original.status == "rejected"
    pub = db.get(Publication, snapshot["publication_id"])
    assert pub.published_at is None
    account = db.get(SocialAccount, pub.social_account_id)
    assert not account.approved_for_publication
    assert pub.upload_session_reference.startswith("gAAAA")
    assert db.get(Video, pub.video_id).status == "owner_private_upload_test"
    sent_plan = db.get(SystemSetting, OPERATION).value["plan"]
    assert sent_plan["metadata"]["status"]["containsSyntheticMedia"] is True
    assert sent_plan["notify_subscribers"] is False
headers = {"Authorization": "Bearer " + os.environ["ADMIN_TOKEN"]}
admin = requests.get("http://127.0.0.1:8000/admin", headers=headers, timeout=15)
assert admin.status_code == 200 and snapshot["url"] in admin.text
print(
    json.dumps(
        {
            "upload": snapshot,
            "generation_count": generations,
            "publication_count": publications,
            "model_usage_count": usage,
            "confirmed_ai_cost_usd": str(confirmed),
            "new_ai_calls": 0,
            "original_job_status": original.status,
            "scheduler_enabled": False,
            "public_publishing_enabled": False,
            "automatic_spending_enabled": False,
            "budget_caps_usd": "0",
            "account_approved_for_automatic_publication": False,
            "session_reference_encrypted": True,
            "synthetic_media_disclosure_sent": True,
            "synthetic_media_disclosure_readback": snapshot["verified"]["synthetic_media"],
            "dashboard_links_to_uploaded_video": True,
            "upload_module_sha256": hashlib.sha256(
                Path("tsu/youtube_upload.py").read_bytes()
            ).hexdigest(),
        },
        ensure_ascii=False,
        indent=2,
    )
)
