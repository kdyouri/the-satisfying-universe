import json
from pathlib import Path
from types import SimpleNamespace

from sqlalchemy import select

from tsu.config import Settings
from tsu.db import make_sessions
from tsu.jobs import create_job
from tsu.models import VideoGeneration
from tsu.pilot import KEY, MODELS, FirstVideo, PilotBrief


def test_operator_brief_does_not_retry_uncertain_creative_call(local_engine, tmp_path):
    sessions = make_sessions(local_engine)
    uncertain = {"state": "submitting", "input_hash": "original-input"}
    with sessions.begin() as session:
        job, _ = create_job(session, KEY, {"scope": "one first video"})
        job.payload = {**job.payload, "calls": {"creative": uncertain}}
    brief = PilotBrief(
        concept="Golden liquid in a black bowl",
        title="Golden spiral",
        description="Original test concept",
        hashtags=[],
        prompts=["A slow golden liquid spiral in a stationary black ceramic bowl."] * 2,
    )
    (tmp_path / "operator-brief.json").write_text(brief.model_dump_json())
    # No provider methods exist: any attempt to call the external API fails this test.
    runner = FirstVideo(Settings(_env_file=None, **MODELS), local_engine, object(), tmp_path)
    assert runner.creative() == brief
    assert runner.creative() == brief
    with sessions() as session:
        job = runner.job(session)
        assert job.payload["calls"]["creative"] == uncertain
        assert job.payload["brief_source"].startswith("operator-prepared")
        assert len(session.scalars(select(VideoGeneration)).all()) == 2


def test_operator_plan_ignores_price_of_unused_creative_model(local_engine, tmp_path):
    catalogue = json.loads(Path("postman/mocks/openrouter/catalogue.json").read_text())
    videos = {m["id"]: m for m in catalogue["videos"]}
    models = {m["id"]: m for m in catalogue["models"]}
    models[MODELS["creative_model"]]["pricing"]["prompt"] = "1"
    (tmp_path / "operator-brief.json").write_text("{}")
    provider = SimpleNamespace(verify_key=lambda: None, catalogues=lambda: (videos, models))
    runner = FirstVideo(Settings(_env_file=None, **MODELS), local_engine, provider, tmp_path)
    runner.prepare()
    assert str(runner.clip_quote) == "0.400000"


def test_missing_soundtrack_stops_before_any_provider_call(local_engine, tmp_path, monkeypatch):
    import pytest

    import tsu.pilot

    monkeypatch.setattr(tsu.pilot, "production_profile", lambda: {"audio_ready": False})
    runner = FirstVideo(Settings(_env_file=None, **MODELS), local_engine, object(), tmp_path)
    with pytest.raises(RuntimeError, match="before any paid submission"):
        runner.prepare()
