"""Real multi-job caller, PostgreSQL, FFmpeg and both local HTTP providers."""

import json
import os
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
import requests
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from tsu.api import create_app
from tsu.config import Settings
from tsu.jobs import schedule_production
from tsu.models import (
    Alert,
    BudgetGuard,
    Concept,
    ModelUsage,
    OAuthCredential,
    ProductionJob,
    Publication,
    QualityCheck,
    SocialAccount,
    Video,
    VideoGeneration,
    utcnow,
)
from tsu.openrouter import OpenRouter
from tsu.pilot import MODELS
from tsu.workflow import ProductionInput, ProductionWorkflow, dispatch, enqueue, workflow_lock
from tsu.youtube_auth import YOUTUBE_CONNECTION_SCOPES
from tsu.youtube_job import YouTubeJob
from tsu.youtube_upload import UploadEndpoints, UploadHTTP

BASE = "http://127.0.0.1:4013"
OR = BASE + "/openrouter"
YT = BASE + "/youtube-upload"
TOKEN = "synthetic-owner-password-at-least-32-characters"


@pytest.fixture
def pipeline(pg_sessions, postgres_engine, tmp_path):
    if os.environ.get("TSU_PRODUCTION_SIMULATION") != "1":
        pytest.skip("Start the local two-provider production simulation on port 4013")
    for base in (OR, YT):
        response = requests.post(
            base + "/__control",
            json={
                "mode": "success",
                "multiple": True,
                "base_url": YT,
            },
            timeout=5,
        )
        response.raise_for_status()
        assert response.headers["X-TSU-Mock"] in {"openrouter", "youtube-upload"}
    key = Fernet.generate_key()
    settings = Settings(
        _env_file=None,
        **MODELS,
        admin_token=TOKEN,
        data_root=tmp_path,
        spending_authorized=True,
        publishing_authorized=True,
        daily_budget_usd="10",
        monthly_budget_usd="10",
        openrouter_api_key="synthetic-openrouter-key",
        token_encryption_key=key.decode(),
        youtube_channel_id="UC8DbuevZRxVTWxltG9oDFRw",
        youtube_client_id="fake.apps.googleusercontent.com",
        youtube_client_secret="fake-secret",
    )
    with pg_sessions.begin() as db:
        account = SocialAccount(
            platform="youtube",
            external_id=settings.youtube_channel_id,
            handle="@techno-inno",
            scopes=list(YOUTUBE_CONNECTION_SCOPES),
            secret_reference="synthetic",
            approved_for_publication=True,
        )
        db.add(account)
        db.flush()
        raw = {
            "client_id": "fake.apps.googleusercontent.com",
            "refresh_token": "fake-refresh",
            "token": "expired-fake",
            "expiry": (utcnow() - timedelta(hours=1)).isoformat(),
        }
        db.add(
            OAuthCredential(
                account_id=account.id,
                credentials_encrypted=Fernet(key).encrypt(json.dumps(raw).encode()).decode(),
            )
        )

    def make(polls=3):
        def publisher(job_id, result):
            http = UploadHTTP(
                UploadEndpoints(
                    YT + "/token", YT + "/youtube/v3", YT + "/upload/youtube/v3/videos"
                ),
                timeout=(1, 0.2),
            )
            return YouTubeJob(settings, postgres_engine, job_id, result, http=http)

        return ProductionWorkflow(
            settings,
            postgres_engine,
            provider_factory=lambda: OpenRouter("synthetic-openrouter-key", OR, timeout=(1, 0.2)),
            publisher_factory=publisher,
            interval=0,
            polls=polls,
        )

    def create(key="one", visibility="public", *, native=False):
        with pg_sessions.begin() as db:
            job, _ = enqueue(
                db,
                key,
                ProductionInput(concept=f"Original calming theme {key}", visibility=visibility),
                legacy_profile=None if native else "contextual_audio_v3",
            )
            return job.id

    return settings, make, create


def events(base):
    return requests.get(base + "/__control", timeout=5).json()["events"]


@pytest.mark.postgres
def test_new_sound_trial_is_one_private_capped_cycle_with_global_controls_off(
    pipeline, pg_sessions, postgres_engine
):
    from tsu.sound_trial import KEY, THEME
    from tsu.trial import run_trial

    settings, make, _ = pipeline
    settings.spending_authorized = settings.publishing_authorized = False
    settings.daily_budget_usd = settings.monthly_budget_usd = Decimal("0")
    with pg_sessions.begin() as db:
        db.scalar(select(SocialAccount)).approved_for_publication = False

    def factory(scoped):
        runner = make()
        runner.settings = scoped
        prior = runner.publisher_factory

        def publisher(job_id, result):
            service = prior(job_id, result)
            service.settings = scoped
            return service

        runner.publisher_factory = publisher
        return runner

    result = run_trial(
        settings,
        postgres_engine,
        authorized=True,
        reference="synthetic-owner-consent",
        workflow_factory=factory,
        trial_key=KEY,
        theme=THEME,
    )
    assert result["status"] == "completed_private"
    before = (len(events(OR)), len(events(YT)))
    assert (
        run_trial(
            settings,
            postgres_engine,
            authorized=True,
            reference="synthetic-owner-consent",
            workflow_factory=factory,
            trial_key=KEY,
            theme=THEME,
        )["status"]
        == "completed_private"
    )
    assert (len(events(OR)), len(events(YT))) == before
    assert not settings.spending_authorized and not settings.publishing_authorized
    assert settings.daily_budget_usd == settings.monthly_budget_usd == 0
    with pg_sessions() as db:
        job = db.scalar(select(ProductionJob))
        assert job.payload["result"]["production_profile"]["version"] == "contextual_audio_v3"
        assert db.scalar(select(func.sum(ModelUsage.actual_usd))) < 1
        assert db.scalar(select(Publication)).published_at is None


@pytest.mark.postgres
@pytest.mark.parametrize("mode", ["sound_missing", "sound_unsupported"])
def test_unsupported_sound_stops_before_paid_video_generation(pipeline, mode):
    _, make, create = pipeline
    requests.post(OR + "/__control", json={"mode": mode}, timeout=5).raise_for_status()
    assert make().run(create())["status"] == "owner_attention"
    assert not any(e["path"] == "/videos" for e in events(OR))
    assert not events(YT)


@pytest.mark.postgres
def test_existing_job_retains_captured_audio_policy_on_enqueue_replay(pipeline, pg_sessions):
    _, _, create = pipeline
    job_id = create()
    with pg_sessions.begin() as db:
        job = db.get(ProductionJob, job_id)
        job.payload = {**job.payload, "production_profile": "balanced_audio_v2", "result": {}}
    with pg_sessions.begin() as db:
        same, created = enqueue(
            db, "one", ProductionInput(concept="Original calming theme one", visibility="public")
        )
        assert not created and same.id == job_id
        assert same.payload["production_profile"] == "balanced_audio_v2"


@pytest.mark.postgres
@pytest.mark.parametrize("mode", ["success", "lost_metadata_response", "stale_metadata_read"])
def test_explicit_hashtag_edit_preserves_visibility_extra_languages_and_avoids_duplicates(
    pipeline, pg_sessions, monkeypatch, mode
):
    import tsu.youtube_job
    from tsu.youtube_metadata import localized_metadata
    from tsu.youtube_upload import UploadError

    _, make, create = pipeline
    runner = make()
    job_id = create(visibility="private")
    # Simulate a job uploaded by the former release, before the hashtag policy.
    current_policy = tsu.youtube_job.discovery_metadata
    monkeypatch.setattr(
        tsu.youtube_job,
        "discovery_metadata",
        lambda texts, hashtags, **kwargs: localized_metadata(texts, **kwargs),
    )
    assert runner.run(job_id)["status"] == "completed_private"
    monkeypatch.setattr(tsu.youtube_job, "discovery_metadata", current_policy)
    with pg_sessions() as db:
        result = db.get(ProductionJob, job_id).payload["result"]
    service = runner.publisher_factory(job_id, result)
    try:
        assert "#Shorts" not in service.metadata["snippet"]["description"]
        service.authorize()
        remote = service.remote()
        old = {
            code: {**text, "description": text["description"].split("\n\n#")[0]}
            for code, text in remote["localizations"].items()
        }
        old["de"] = {"title": "Beibehalten", "description": "Bestehender Text"}
        snippet = {**remote["snippet"], **old["en"], "tags": ["keep-tag"]}
        service.http.data(
            service.http.request(
                "PUT",
                service.http.endpoints.api + "/videos",
                params={"part": "snippet,localizations"},
                json={"id": remote["id"], "snippet": snippet, "localizations": old},
            )
        )
        requests.post(
            YT + "/__control", json={"mode": mode, "preserve": True}, timeout=5
        ).raise_for_status()
        before_paid, before_uploads = (
            len(events(OR)),
            sum(
                e["method"] == "POST" and e["path"] == "/upload/youtube/v3/videos"
                for e in events(YT)
            ),
        )
        with pytest.raises(UploadError, match="Explicit owner authorization"):
            service.update_discovery_metadata()
        if mode == "stale_metadata_read":
            with pytest.raises(UploadError, match="not confirmed"):
                service.update_discovery_metadata(authorized=True)
            # A later read confirms the one accepted PUT despite reordered tags.
        updated = service.update_discovery_metadata(authorized=True)
        assert updated["privacy"] == "private" and updated["new_uploads"] == 0
        assert all(
            "#LiquidFlow" in text["description"] for text in updated["localizations"].values()
        )
        assert service.remote()["localizations"]["de"] == old["de"]
        assert "keep-tag" in service.remote()["snippet"]["tags"]
        writes = sum(e["method"] == "PUT" and e["path"] == "/youtube/v3/videos" for e in events(YT))
        # Replaying a verified edit reads Google, but does not issue another write.
        assert service.update_discovery_metadata(authorized=True)["translations_verified"]
        assert (
            sum(e["method"] == "PUT" and e["path"] == "/youtube/v3/videos" for e in events(YT))
            == writes
        )
        assert all(
            "status" not in e["body"]
            for e in events(YT)
            if e["method"] == "PUT" and e["path"] == "/youtube/v3/videos"
        )
        assert len(events(OR)) == before_paid
        assert (
            sum(
                e["method"] == "POST" and e["path"] == "/upload/youtube/v3/videos"
                for e in events(YT)
            )
            == before_uploads
        )
    finally:
        service.close()


@pytest.mark.postgres
def test_two_distinct_jobs_complete_and_resume_without_duplicate_paid_or_upload_posts(
    pipeline, pg_sessions
):
    settings, make, create = pipeline
    first, second = create("one"), create("two")
    runner = make()
    assert runner.run(first)["status"] == "published"
    assert runner.run(second)["status"] == "published"
    before = (len(events(OR)), len(events(YT)))
    assert make().run(first)["status"] == "published"
    assert make().run(second)["status"] == "published"
    assert (len(events(OR)), len(events(YT))) == before
    with pg_sessions() as db:

        def count(model):
            return db.scalar(select(func.count()).select_from(model))

        assert (
            count(Concept),
            count(VideoGeneration),
            count(Video),
            count(QualityCheck),
            count(Publication),
            count(ModelUsage),
        ) == (2, 4, 2, 2, 2, 8)
        assert db.scalar(select(func.sum(ModelUsage.actual_usd))) == Decimal("1.608200")
        pubs = db.scalars(select(Publication)).all()
        assert len({p.remote_id for p in pubs}) == 2
        assert all(p.status == "processed_public" and p.published_at for p in pubs)
        videos = db.scalars(select(Video)).all()
        assert len({v.final_key for v in videos}) == 2
        assert len({v.sha256 for v in videos}) == 2
        assert all(
            db.get(ProductionJob, job_id).payload["result"]["production_profile"]["version"]
            == "contextual_audio_v3"
            for job_id in (first, second)
        )
        concepts = db.scalars(select(Concept)).all()
        assert len({c.brief["title"] for c in concepts}) == 2
        assert all(
            set(c.brief["localizations"]) == {"en", "fr", "es", "it", "ru", "zh-CN"}
            for c in concepts
        )
    assert sum(x["method"] == "POST" for x in events(OR)) == 8
    assert (
        sum(x["method"] == "POST" and x["path"] == "/upload/youtube/v3/videos" for x in events(YT))
        == 2
    )
    assert not settings.enable_daily_scheduler


@pytest.mark.postgres
@pytest.mark.parametrize(
    "mode,expected",
    [
        ("qa_minor", "published"),
        ("qa_visible_major", "awaiting_local_edit"),
        ("qa_uncertain", "awaiting_owner_review"),
        ("qa_audio_unobservable", "awaiting_owner_review"),
        ("price_increase", "owner_attention"),
        ("chat_error", "owner_attention"),
        ("submit_timeout", "owner_attention"),
        ("overrun", "owner_attention"),
    ],
)
def test_production_quality_and_uncertain_cost_stops(pipeline, pg_sessions, mode, expected):
    _, make, create = pipeline
    requests.post(OR + "/__control", json={"mode": mode}, timeout=5).raise_for_status()
    job = create()
    assert make().run(job)["status"] == expected
    before = sum(x["method"] == "POST" for x in events(OR))
    assert make().run(job)["status"] == expected
    assert sum(x["method"] == "POST" for x in events(OR)) == before
    if expected != "published":
        assert not any(x["method"] == "POST" for x in events(YT))
        with pg_sessions() as db:
            assert db.scalar(select(Alert)) is not None
    with pg_sessions() as db:
        assert db.get(BudgetGuard, 1).frozen == (mode == "overrun")


@pytest.mark.postgres
@pytest.mark.parametrize(
    "youtube_mode", ["lost_completion", "lost_public_response", "processing_delay"]
)
def test_restart_reconciles_youtube_without_new_paid_requests(
    pipeline, pg_sessions, postgres_engine, youtube_mode
):
    settings, make, create = pipeline
    requests.post(
        YT + "/__control", json={"mode": youtube_mode, "multiple": True, "base_url": YT}, timeout=5
    ).raise_for_status()
    job = create()
    initial = make().run(job)
    assert initial["status"] in {"retry_wait", "awaiting_processing"}, initial
    paid_before = sum(x["method"] == "POST" for x in events(OR))
    # A fresh workflow instance, selected through actual dispatch, simulates worker restart.
    assert dispatch(settings, postgres_engine, make(), now=utcnow() + timedelta(minutes=5)) == 1
    with pg_sessions() as db:
        assert db.get(ProductionJob, job).status == "published"
        assert db.scalar(select(func.count()).select_from(Publication)) == 1
    assert sum(x["method"] == "POST" for x in events(OR)) == paid_before == 4
    assert (
        sum(x["method"] == "POST" and x["path"] == "/upload/youtube/v3/videos" for x in events(YT))
        == 1
    )


@pytest.mark.postgres
def test_generation_polling_restart_reuses_known_paid_ids(pipeline, postgres_engine, pg_sessions):
    settings, make, create = pipeline
    job = create()
    assert make(polls=1).run(job)["status"] == "retry_wait"
    assert (
        dispatch(settings, postgres_engine, make(polls=1), now=utcnow() + timedelta(minutes=5)) == 1
    )
    assert (
        dispatch(settings, postgres_engine, make(polls=3), now=utcnow() + timedelta(minutes=10))
        == 1
    )
    with pg_sessions() as db:
        assert db.get(ProductionJob, job).status == "published"
    assert sum(x["method"] == "POST" and x["path"] == "/videos" for x in events(OR)) == 2


@pytest.mark.postgres
def test_real_budget_limits_are_not_replaced_by_first_video_allowance(pipeline, pg_sessions):
    settings, make, create = pipeline
    settings.spending_authorized = False
    first = create()
    assert make().run(first)["status"] == "budget_blocked"
    assert not events(OR) and not events(YT)
    settings.spending_authorized = True
    settings.daily_budget_usd = Decimal("1")
    assert make().run(first)["status"] == "published"
    second = create("two")
    assert make().run(second)["status"] == "budget_blocked"
    assert settings.daily_budget_usd == 1 and settings.monthly_budget_usd == 10
    with pg_sessions() as db:
        assert db.scalar(select(func.sum(ModelUsage.actual_usd))) < 1
        assert db.scalar(select(func.count()).select_from(Publication)) == 1


@pytest.mark.postgres
def test_scheduler_times_timezone_gate_and_concurrency(pipeline, postgres_engine, pg_sessions):
    settings, make, _ = pipeline
    early = datetime(2026, 11, 6, 5, tzinfo=UTC)
    noon = datetime(2026, 11, 6, 12, tzinfo=UTC)
    late = datetime(2026, 11, 6, 22, tzinfo=UTC)
    with pg_sessions.begin() as db:
        assert not schedule_production(db, early, "Africa/Casablanca", ("10:00", "19:00"))
        first = schedule_production(db, noon, "Africa/Casablanca", ("10:00", "19:00"))
        assert len(first) == 1
        assert schedule_production(db, noon, "Africa/Casablanca", ("10:00", "19:00")) == first
        assert len(schedule_production(db, late, "Africa/Casablanca", ("10:00", "19:00"))) == 2
    settings.enable_daily_scheduler = True
    assert dispatch(settings, postgres_engine, make(), now=late) == 0
    assert not events(OR)
    settings.enable_daily_scheduler = False
    with workflow_lock(postgres_engine):
        assert dispatch(settings, postgres_engine, make(), now=late) == 0
    assert not events(OR)


def test_production_api_is_protected_private_by_default_and_durable(local_engine):
    client = TestClient(create_app(Settings(_env_file=None, admin_token=TOKEN), local_engine))
    assert client.get("/api/production/status").status_code == 401
    assert client.post("/api/production/jobs", json={"concept": "Fresh theme"}).status_code == 401
    client.headers["Authorization"] = "Bearer " + TOKEN
    first = client.post(
        "/api/production/jobs", json={"concept": "Fresh theme"}, headers={"Idempotency-Key": "one"}
    )
    assert first.status_code == 201
    assert first.json()["payload"]["visibility"] == "private"
    repeat = client.post(
        "/api/production/jobs", json={"concept": "Fresh theme"}, headers={"Idempotency-Key": "one"}
    )
    assert repeat.status_code == 200 and repeat.json()["id"] == first.json()["id"]
    assert (
        client.post(
            "/api/production/jobs",
            json={"concept": "Changed theme"},
            headers={"Idempotency-Key": "one"},
        ).status_code
        == 409
    )
    assert (
        client.post(
            "/api/production/jobs",
            json={"concept": "Other", "file": "/etc/passwd"},
            headers={"Idempotency-Key": "two"},
        ).status_code
        == 422
    )
    state = client.get("/api/production/status").json()
    assert state["workflow_implemented"] and not state["scheduler_enabled"]
    assert "spending_not_authorized" in state["blockers"]


@pytest.mark.postgres
def test_publication_gate_can_resume_approved_media_without_new_spending(pipeline, pg_sessions):
    settings, make, create = pipeline
    settings.publishing_authorized = False
    job = create()
    assert make().run(job)["status"] == "awaiting_publication_authorization"
    assert not events(YT)
    paid = sum(x["method"] == "POST" for x in events(OR))
    settings.spending_authorized = False
    settings.publishing_authorized = True
    assert make().run(job)["status"] == "published"
    assert sum(x["method"] == "POST" for x in events(OR)) == paid == 4
    with pg_sessions() as db:
        assert db.scalar(select(func.count()).select_from(Publication)) == 1


@pytest.mark.postgres
def test_private_target_remains_private_and_account_approval_is_required(pipeline, pg_sessions):
    _, make, create = pipeline
    job = create(visibility="private")
    assert make().run(job)["status"] == "completed_private"
    assert not any(e["method"] == "PUT" and e["path"] == "/youtube/v3/videos" for e in events(YT))
    with pg_sessions.begin() as db:
        db.scalar(select(SocialAccount)).approved_for_publication = False
    other = create("second")
    starts = sum(e["method"] == "POST" for e in events(YT))
    assert make().run(other)["status"] == "owner_attention"
    assert sum(e["method"] == "POST" for e in events(YT)) == starts


@pytest.mark.postgres
def test_duplicate_concept_stops_before_new_video_generations(pipeline):
    _, make, create = pipeline
    requests.post(
        OR + "/__control", json={"mode": "duplicate_concept"}, timeout=5
    ).raise_for_status()
    assert make().run(create("one"))["status"] == "published"
    assert make().run(create("two"))["status"] == "owner_attention"
    assert sum(e["method"] == "POST" and e["path"] == "/videos" for e in events(OR)) == 2


@pytest.mark.postgres
def test_private_trial_requires_explicit_scope_and_never_enables_global_publication(
    pipeline, pg_sessions, postgres_engine
):
    from tsu.budget import BudgetBlocked
    from tsu.trial import run_trial

    settings, make, _ = pipeline
    settings.spending_authorized = settings.publishing_authorized = False
    settings.daily_budget_usd = settings.monthly_budget_usd = Decimal("0")
    with pg_sessions.begin() as db:
        db.scalar(select(SocialAccount)).approved_for_publication = False
    with pytest.raises(BudgetBlocked):
        run_trial(settings, postgres_engine)
    assert not events(OR) and not events(YT)

    def factory(scoped):
        # Exercise the same real caller and HTTP providers with the one-job context.
        runner = make()
        runner.settings = scoped
        prior_factory = runner.publisher_factory

        def scoped_publisher(job_id, result):
            publisher = prior_factory(job_id, result)
            publisher.settings = scoped
            return publisher

        runner.publisher_factory = scoped_publisher
        return runner

    result = run_trial(
        settings,
        postgres_engine,
        authorized=True,
        reference="synthetic-human-consent",
        workflow_factory=factory,
    )
    assert result["status"] == "completed_private", result
    assert not settings.spending_authorized and not settings.publishing_authorized
    assert settings.daily_budget_usd == settings.monthly_budget_usd == 0
    with pg_sessions() as db:
        assert not db.scalar(select(SocialAccount)).approved_for_publication
        assert db.scalar(select(func.sum(ModelUsage.actual_usd))) <= 1
        assert db.scalar(select(Publication)).published_at is None


@pytest.mark.postgres
def test_paid_intents_are_serialized_even_without_the_outer_worker_lock(
    pipeline, postgres_engine, pg_sessions
):
    from concurrent.futures import ThreadPoolExecutor

    from tsu.workflow import JobProducer

    settings, _, create = pipeline
    job_id = create()
    producers = [
        JobProducer(
            settings,
            postgres_engine,
            OpenRouter("synthetic-openrouter-key", OR, timeout=(1, 0.2)),
            job_id,
            interval=0,
            polls=3,
        )
        for _ in range(2)
    ]
    for producer in producers:
        producer.prepare()

    def creative(producer):
        try:
            producer.creative()
            return True
        except Exception:
            return False  # An in-flight paid intent must stop the competing caller.

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert any(pool.map(creative, producers))
    assert sum(e["method"] == "POST" for e in events(OR)) == 1
    with pg_sessions() as db:
        assert db.scalar(select(func.count()).select_from(ModelUsage)) == 1
        assert db.scalar(select(func.count()).select_from(Concept)) == 1
    for producer in producers:
        producer.provider.session.close()


@pytest.mark.postgres
def test_native_single_generation_preserves_download_and_blocks_edit_or_discard(
    pipeline, pg_sessions, postgres_engine
):
    import hashlib
    from pathlib import Path

    from tsu.native_profile import MODEL
    from tsu.youtube_upload import UploadError

    settings, make, create = pipeline
    settings.video_model = MODEL
    job_id = create("native-original", "private", native=True)
    with pg_sessions() as db:
        profile = db.get(ProductionJob, job_id).payload["production_profile"]
        assert profile["version"] == "native_audio_v5" and profile["clip_count"] == 1
    outcome = make().run(job_id)
    assert outcome["status"] == "completed_private", outcome
    with pg_sessions() as db:
        job = db.get(ProductionJob, job_id)
        result = job.payload["result"]
        generation = db.scalar(select(VideoGeneration))
        video = db.get(Video, result["video_id"])
        asset = Path(video.final_key)
        source = Path(generation.parameters["local_key"])
        assert asset.read_bytes() == source.read_bytes()
        assert hashlib.sha256(asset.read_bytes()).hexdigest() == generation.parameters["sha256"]
        assert video.technical_metadata["metadata"]["streams"][0]["avg_frame_rate"] == "24/1"
        assert result["production_profile"]["postproduction"] is False
        assert result["actual_cost_usd"] == "0.644100"
        assert db.scalar(select(func.count(VideoGeneration.id))) == 1
        assert db.scalar(select(func.count(ModelUsage.id))) == 3
    submissions = [e["body"] for e in events(OR) if e["path"] == "/videos"]
    assert len(submissions) == 1
    assert submissions[0]["duration"] == 8 and submissions[0]["generate_audio"] is True
    assert "frame_images" not in submissions[0]
    snapshot = len(events(OR)), len(events(YT))
    assert make().run(job_id)["status"] == "completed_private"
    assert snapshot == (len(events(OR)), len(events(YT)))
    service = YouTubeJob(settings, postgres_engine, job_id, result)
    try:
        assert set(service.metadata["localizations"]) == {"en", "fr", "es", "it", "ru", "zh-CN"}
        assert all(
            "#Shorts" in t["description"] for t in service.metadata["localizations"].values()
        )
        original = asset.read_bytes()
        asset.write_bytes(original + b"changed after generation")
        with pytest.raises(UploadError, match="preserve the provider output"):
            service.approved()
        asset.write_bytes(original)
        with pg_sessions.begin() as db:
            job = db.get(ProductionJob, job_id)
            job.status = "cancelled"
            job.payload = {**job.payload, "owner_discarded": True, "never_publish": True}
        with pytest.raises(UploadError, match="discarded"):
            service.approved()
        assert make().run(job_id)["status"] == "cancelled"
        assert snapshot == (len(events(OR)), len(events(YT)))
    finally:
        service.close()


@pytest.mark.postgres
@pytest.mark.parametrize(
    "mode",
    [
        "native_price_increase",
        "native_no_audio_capability",
        "native_no_duration",
        "native_unknown_price",
    ],
)
def test_native_unavailable_or_unquoted_plan_stops_before_any_paid_post(pipeline, mode):
    from tsu.native_profile import MODEL

    settings, make, create = pipeline
    settings.video_model = MODEL
    requests.post(OR + "/__control", json={"mode": mode}, timeout=5).raise_for_status()
    assert make().run(create("native-unavailable", native=True))["status"] == "owner_attention"
    assert not [e for e in events(OR) if e["method"] == "POST"]
    assert not events(YT)


@pytest.mark.postgres
@pytest.mark.parametrize(
    "mode,expected",
    [
        ("native_silent", "owner_attention"),
        ("qa_visible_major", "awaiting_owner_review"),
        ("qa_minor", "completed_private"),
    ],
)
def test_native_audio_and_practical_quality_stop_without_editing_or_regenerating(
    pipeline, pg_sessions, mode, expected
):
    from pathlib import Path

    from tsu.native_profile import MODEL

    settings, make, create = pipeline
    settings.video_model = MODEL
    requests.post(OR + "/__control", json={"mode": mode}, timeout=5).raise_for_status()
    job_id = create("native-quality", "private", native=True)
    assert make().run(job_id)["status"] == expected
    with pg_sessions() as db:
        generation = db.scalar(select(VideoGeneration))
        directory = settings.data_root / "jobs" / job_id
        assert (directory / "first-video.mp4").read_bytes() == Path(
            generation.parameters["local_key"]
        ).read_bytes()
    assert len([e for e in events(OR) if e["path"] == "/videos"]) == 1
    if expected != "completed_private":
        assert not events(YT)
        paid_before = [e for e in events(OR) if e["method"] == "POST"]
        make().run(job_id)
        assert paid_before == [e for e in events(OR) if e["method"] == "POST"]
        assert not events(YT)


@pytest.mark.postgres
def test_terminal_provider_error_body_stops_polling_and_keeps_known_intent(pipeline, pg_sessions):
    from tsu.native_profile import MODEL

    settings, make, create = pipeline
    settings.video_model = MODEL
    requests.post(
        OR + "/__control", json={"mode": "terminal_error_body"}, timeout=5
    ).raise_for_status()
    job_id = create("native-terminal-error", "private", native=True)
    assert make().run(job_id)["status"] == "owner_attention"
    assert len([e for e in events(OR) if e["path"] == "/videos"]) == 1
    with pg_sessions() as db:
        generation = db.scalar(select(VideoGeneration))
        assert generation.status == "pending" and generation.remote_job_id
        assert generation.cost_usd is None
        charge = db.scalar(select(ModelUsage).where(ModelUsage.operation_key.endswith(":clip:0")))
        assert charge.reserved_usd > 0 and charge.actual_usd is None
    before = [e for e in events(OR) if e["method"] == "POST"]
    assert make().run(job_id)["status"] == "owner_attention"
    assert before == [e for e in events(OR) if e["method"] == "POST"]
    assert not events(YT)


@pytest.mark.postgres
def test_discarded_trial_cannot_be_reauthorized(pipeline, pg_sessions, postgres_engine):
    from tsu.budget import BudgetBlocked
    from tsu.sound_trial import KEY, THEME
    from tsu.trial import run_trial

    settings, make, _ = pipeline
    settings.spending_authorized = settings.publishing_authorized = False
    settings.daily_budget_usd = settings.monthly_budget_usd = Decimal("0")
    with pg_sessions.begin() as db:
        job, _ = enqueue(db, KEY, ProductionInput(concept=THEME, visibility="private"))
        job_id = job.id
        job.status = "cancelled"
        job.payload = {**job.payload, "owner_discarded": True, "never_publish": True}
    assert make().run(job_id)["status"] == "cancelled"
    with pytest.raises(BudgetBlocked, match="discarded"):
        run_trial(
            settings,
            postgres_engine,
            authorized=True,
            reference="old-consent",
            trial_key=KEY,
            theme=THEME,
        )
    assert not events(OR) and not events(YT)


@pytest.mark.postgres
def test_native_scoped_trial_one_private_cycle_under_170_with_global_flags_off(
    pipeline, pg_sessions, postgres_engine
):
    from tsu.native_profile import MODEL
    from tsu.trial import run_trial
    from tsu.trial_policy import NATIVE_KEY, NATIVE_THEME

    settings, make, _ = pipeline
    settings.video_model = MODEL
    settings.spending_authorized = settings.publishing_authorized = False
    settings.daily_budget_usd = settings.monthly_budget_usd = Decimal("0")
    with pg_sessions.begin() as db:
        db.scalar(select(SocialAccount)).approved_for_publication = False

    def factory(scoped):
        runner = make()
        runner.settings = scoped
        prior = runner.publisher_factory

        def publisher(job_id, result):
            service = prior(job_id, result)
            service.settings = scoped
            return service

        runner.publisher_factory = publisher
        return runner

    def run():
        return run_trial(
            settings,
            postgres_engine,
            authorized=True,
            reference="synthetic-native-owner-consent",
            trial_key=NATIVE_KEY,
            theme=NATIVE_THEME,
            workflow_factory=factory,
        )

    assert run()["status"] == "completed_private"
    snapshot = len(events(OR)), len(events(YT))
    assert run()["status"] == "completed_private"
    assert snapshot == (len(events(OR)), len(events(YT)))
    assert not settings.spending_authorized and not settings.publishing_authorized
    assert settings.daily_budget_usd == settings.monthly_budget_usd == 0
    with pg_sessions() as db:
        job = db.scalar(select(ProductionJob))
        assert job.payload["private_trial_authorization"]["maximum_usd"] == "1.70"
        assert job.payload["result"]["production_profile"]["version"] == "native_audio_v5"
        assert db.scalar(select(func.count(VideoGeneration.id))) == 1
        assert db.scalar(select(func.sum(ModelUsage.actual_usd))) <= Decimal("1.70")
        assert db.scalar(select(Publication)).published_at is None


@pytest.mark.postgres
def test_native_v2_scoped_trial_free_theme_two_dollar_cap_one_private_cycle(
    pipeline, pg_sessions, postgres_engine
):
    from tsu.native_profile import MODEL
    from tsu.trial import run_trial
    from tsu.trial_policy import NATIVE2_DURABLE_KEY, NATIVE2_KEY, NATIVE2_LIMIT

    settings, make, _ = pipeline
    settings.video_model = MODEL
    settings.spending_authorized = settings.publishing_authorized = False
    settings.daily_budget_usd = settings.monthly_budget_usd = Decimal("0")
    with pg_sessions.begin() as db:
        db.scalar(select(SocialAccount)).approved_for_publication = False

    def factory(scoped):
        runner = make()
        runner.settings = scoped
        prior = runner.publisher_factory

        def publisher(job_id, result):
            service = prior(job_id, result)
            service.settings = scoped
            return service

        runner.publisher_factory = publisher
        return runner

    free_theme = (
        "One NEW original satisfying macro subject chosen freely by the creative model, "
        "avoiding every recently used concept."
    )

    def run():
        return run_trial(
            settings,
            postgres_engine,
            authorized=True,
            reference="synthetic-native-v2-owner-consent",
            trial_key=NATIVE2_KEY,
            theme=free_theme,
            workflow_factory=factory,
        )

    assert run()["status"] == "completed_private"
    snapshot = len(events(OR)), len(events(YT))
    assert run()["status"] == "completed_private"
    assert snapshot == (len(events(OR)), len(events(YT)))
    assert not settings.spending_authorized and not settings.publishing_authorized
    assert settings.daily_budget_usd == settings.monthly_budget_usd == 0
    with pg_sessions() as db:
        job = db.scalar(select(ProductionJob))
        assert job.idempotency_key == NATIVE2_DURABLE_KEY
        assert job.payload["private_trial_authorization"]["maximum_usd"] == NATIVE2_LIMIT
        assert job.payload["result"]["production_profile"]["version"] == "native_audio_v5"
        assert db.scalar(select(func.count(VideoGeneration.id))) == 1
        assert db.scalar(select(func.sum(ModelUsage.actual_usd))) <= Decimal("2.00")
        assert db.scalar(select(Publication)).published_at is None


@pytest.mark.postgres
def test_native_v3_scoped_trial_veo_native_audio_one_dollar_cap_one_private_cycle(
    pipeline, pg_sessions, postgres_engine
):
    from tsu.native_profile import MODEL
    from tsu.trial import run_trial
    from tsu.trial_policy import NATIVE3_DURABLE_KEY, NATIVE3_KEY, NATIVE3_LIMIT

    settings, make, _ = pipeline
    settings.video_model = MODEL
    settings.spending_authorized = settings.publishing_authorized = False
    settings.daily_budget_usd = settings.monthly_budget_usd = Decimal("0")
    with pg_sessions.begin() as db:
        db.scalar(select(SocialAccount)).approved_for_publication = False

    def factory(scoped):
        runner = make()
        runner.settings = scoped
        prior = runner.publisher_factory

        def publisher(job_id, result):
            service = prior(job_id, result)
            service.settings = scoped
            return service

        runner.publisher_factory = publisher
        return runner

    def run():
        return run_trial(
            settings,
            postgres_engine,
            authorized=True,
            reference="synthetic-native-v3-owner-consent",
            trial_key=NATIVE3_KEY,
            theme="A fresh original satisfying macro subject chosen by the creative model.",
            workflow_factory=factory,
        )

    assert run()["status"] == "completed_private"
    snapshot = len(events(OR)), len(events(YT))
    assert run()["status"] == "completed_private"
    assert snapshot == (len(events(OR)), len(events(YT)))
    assert not settings.spending_authorized and not settings.publishing_authorized
    assert settings.daily_budget_usd == settings.monthly_budget_usd == 0
    with pg_sessions() as db:
        job = db.scalar(select(ProductionJob))
        assert job.idempotency_key == NATIVE3_DURABLE_KEY
        assert job.payload["private_trial_authorization"]["maximum_usd"] == NATIVE3_LIMIT
        profile = job.payload["result"]["production_profile"]
        assert profile["version"] == "native_audio_v5"
        assert profile["model"] == MODEL and profile["duration_seconds"] == 8
        assert db.scalar(select(func.count(VideoGeneration.id))) == 1
        assert db.scalar(select(func.sum(ModelUsage.actual_usd))) <= Decimal("1.00")
        assert db.scalar(select(Publication)).published_at is None
