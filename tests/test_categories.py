"""Content category rotation and per-category performance reporting."""

from datetime import UTC, datetime
from decimal import Decimal

from tsu.categories import CATEGORIES, category_for, category_of, theme_for
from tsu.config import Settings
from tsu.db import make_sessions
from tsu.jobs import schedule_production
from tsu.models import (
    Concept,
    ModelUsage,
    ProductionJob,
    Prompt,
    Publication,
    SocialAccount,
    Video,
    VideoGeneration,
)
from tsu.performance import collect, report
from tsu.workflow import ProductionInput, enqueue


def test_category_rotation_is_deterministic_and_covers_all_categories():
    first = category_for("2026-11-06", 1)
    assert first == "oddly_satisfying"
    assert category_for("2026-11-06", 1) == first
    assert category_for("2026-11-06", 2) != first
    seen = [category_for("2026-11-06", slot) for slot in (1, 2)]
    seen += [category_for("2026-11-07", slot) for slot in (1, 2)]
    seen += [category_for("2026-11-08", slot) for slot in (1, 2)]
    assert set(seen) == {key for key, _ in CATEGORIES}
    assert category_for("2026-11-11", 1) == first


def test_theme_text_roundtrip_and_identity():
    theme = theme_for("hypnotic_visuals")
    assert theme.startswith("Content category hypnotic_visuals: ")
    assert category_of(theme) == "hypnotic_visuals"
    assert "shared TechnoInno visual identity" in theme
    assert category_of("A fresh original calming satisfying macro scene") is None
    assert len(theme) <= 2000


def test_schedule_production_uses_the_rotating_category_theme(pg_sessions):

    with pg_sessions.begin() as db:
        ids = schedule_production(
            db, datetime(2026, 11, 7, 12, tzinfo=UTC), "Africa/Casablanca", ("12:00", "20:00")
        )
        assert len(ids) == 1
        job = db.get(ProductionJob, ids[0])
        assert job.payload["concept"].startswith("Content category ")
        key = category_of(job.payload["concept"])
        assert key == category_for("2026-11-07", 1)
        assert job.payload["visibility"] == "public"
        # Idempotent re-enqueue with the same deterministic theme keeps the job.
        again = schedule_production(
            db, datetime(2026, 11, 7, 12, 30, tzinfo=UTC), "Africa/Casablanca", ("12:00", "20:00")
        )
        assert again == ids


def test_performance_collect_and_report_by_category(local_engine):
    settings = Settings(_env_file=None, youtube_channel_id="channel")
    sessions = make_sessions(local_engine)
    with sessions.begin() as db:
        job, _ = enqueue(
            db,
            "cat-one",
            ProductionInput(concept=theme_for("oddly_satisfying"), visibility="public"),
        )
        concept = Concept(
            name="Concept one",
            category="macro",
            fingerprint="fp-one",
            brief={},
        )
        db.add(concept)
        db.flush()
        job.concept_id = concept.id
        prompt = Prompt(concept_id=concept.id, version=1, text="Synthetic prompt")
        db.add(prompt)
        db.flush()
        generation = VideoGeneration(
            concept_id=concept.id,
            prompt_id=prompt.id,
            job_id=job.id,
            attempt=1,
            clip_index=0,
            provider="openrouter",
            model="synthetic",
            parameters={},
            status="completed",
        )
        db.add(generation)
        db.flush()
        video = Video(
            concept_id=concept.id,
            generation_id=generation.id,
            original_key="original",
            final_key="final",
            sha256="hash",
            technical_metadata={},
            status="published",
        )
        db.add(video)
        db.flush()
        account = SocialAccount(
            platform="youtube",
            external_id="channel",
            handle="@techno-inno",
            scopes=[],
            secret_reference="synthetic",
        )
        db.add(account)
        db.flush()
        publication = Publication(
            video_id=video.id,
            social_account_id=account.id,
            status="processed_public",
            remote_id="vid-1",
        )
        db.add(publication)
        db.flush()
        db.add(
            ModelUsage(
                operation_key="op",
                model="synthetic",
                purpose="video",
                reserved_usd=Decimal("0.1"),
                actual_usd=Decimal("0.1"),
                status="settled",
            )
        )

    def fake_fetch(settings, engine, video_ids):
        assert video_ids == ["vid-1"]
        return {"vid-1": {"view_count": "1200", "like_count": "80", "comment_count": "9"}}

    first = collect(settings, local_engine, fetch=fake_fetch)
    assert first["videos"] == 1 and first["collected"] == 3
    # A second collection the same day replaces the same-source rows, not duplicates.
    second = collect(settings, local_engine, fetch=fake_fetch)
    assert second["collected"] == 3

    outcome = report(settings, local_engine)
    by_key = {row["category"]: row for row in outcome["categories"]}
    assert by_key["oddly_satisfying"]["videos"] == 1
    assert by_key["oddly_satisfying"]["total_views"] == 1200
    assert by_key["oddly_satisfying"]["avg_likes"] == 80.0
    assert outcome["categories"][0]["category"] == "oddly_satisfying"
