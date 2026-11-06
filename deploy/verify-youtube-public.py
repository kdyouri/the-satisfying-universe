"""Read-only live verification of localized YouTube metadata and production controls."""

import json
import os
from decimal import Decimal

import requests
from sqlalchemy import func, select

from tsu.config import Settings
from tsu.db import make_engine, make_sessions
from tsu.models import ModelUsage, ProductionJob, Publication, SocialAccount, VideoGeneration
from tsu.youtube_metadata import FIRST_VIDEO_LOCALIZATIONS, LANGUAGES
from tsu.youtube_publication import YouTubePublication

settings = Settings()
engine = make_engine(settings.database_url.get_secret_value())
service = YouTubePublication(settings, engine)
try:
    current = service.status()
    assert current["status"] == "published_public"
    assert current["privacy"] == "public" and current["translations_verified"]
    assert current["video_id"] == "qNsEQFHoMdk"
    assert current["default_language"] == "en"
    assert current["region_restriction"] is None
    language_checks = {}
    for code in LANGUAGES:
        response = service.http.data(
            service.http.request(
                "GET",
                service.http.endpoints.api + "/videos",
                params={"part": "snippet", "id": current["video_id"], "hl": code},
            )
        )
        item = next(x for x in response["items"] if x["id"] == current["video_id"])
        assert item["snippet"]["channelId"] == settings.youtube_channel_id
        localized = item["snippet"]["localized"]
        expected = FIRST_VIDEO_LOCALIZATIONS[code]
        assert localized["title"] == expected["title"], code
        assert localized["description"] == expected["description"], code
        language_checks[code] = {"title": localized["title"], "title_and_description_match": True}
finally:
    service.close()
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
    pub = db.get(Publication, current["publication_id"])
    assert pub.status == "processed_public" and pub.published_at is not None
    published_at = pub.published_at.isoformat()
    assert not db.get(SocialAccount, pub.social_account_id).approved_for_publication
headers = {"Authorization": "Bearer " + os.environ["ADMIN_TOKEN"]}
admin = requests.get("http://127.0.0.1:8000/admin", headers=headers, timeout=15)
assert admin.status_code == 200 and "Vidéo publique" in admin.text and current["url"] in admin.text
print(
    json.dumps(
        {
            "date": "2026-11-05",
            "upload": current,
            "localized_readback": language_checks,
            "published_at": published_at,
            "generation_count": generations,
            "publication_count": publications,
            "model_usage_count": usage,
            "confirmed_ai_cost_usd": str(confirmed),
            "new_uploads": 0,
            "new_ai_calls": 0,
            "original_job_status": original.status,
            "scheduler_enabled": False,
            "automatic_publishing_enabled": False,
            "automatic_spending_enabled": False,
            "budget_caps_usd": "0",
            "dashboard_reports_public_video": True,
        },
        ensure_ascii=False,
        indent=2,
    )
)
