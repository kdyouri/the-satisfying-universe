"""Actual HTTP + PostgreSQL + FFmpeg against a local synthetic Postman provider."""

import base64
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import requests  # noqa: E402
from sqlalchemy import delete, select  # noqa: E402
from sqlalchemy.engine import make_url  # noqa: E402

from tsu.config import Settings  # noqa: E402
from tsu.db import Base, make_engine, make_sessions  # noqa: E402
from tsu.models import BudgetGuard, ModelUsage, Publication  # noqa: E402
from tsu.openrouter import OpenRouter, ProviderError, usd  # noqa: E402
from tsu.pilot import MODELS, FirstVideo  # noqa: E402

url = os.environ["TSU_TEST_DATABASE_URL"]
parsed = make_url(url)
assert parsed.get_backend_name() == "postgresql" and parsed.database.endswith("_test")
engine = make_engine(url)
Base.metadata.create_all(engine)
sessions = make_sessions(engine)
base = "http://127.0.0.1:4011/openrouter"
control = base + "/__control"
results = []

for mode in (
    "success",
    "qa_minor",
    "qa_visible_major",
    "qa_uncertain",
    "qa_low_score",
    "qa_audio_unobservable",
    "price_increase",
    "chat_error",
    "submit_error",
    "submit_timeout",
    "missing_cost",
    "failed_video",
    "overrun",
    "bad_media",
):
    with sessions.begin() as session:
        for table in reversed(Base.metadata.sorted_tables):
            session.execute(delete(table))
        session.add(BudgetGuard(id=1, frozen=False))
    response = requests.post(control, json={"mode": mode}, timeout=5)
    assert response.headers.get("X-TSU-Mock") == "openrouter"
    response.raise_for_status()
    provider = OpenRouter("synthetic-openrouter-key", base, timeout=(1, 0.2))
    settings = Settings(_env_file=None, **MODELS)
    with tempfile.TemporaryDirectory(prefix="tsu-first-video-sim-") as temporary:
        runner = FirstVideo(settings, engine, provider, Path(temporary), interval=0, polls=3)
        failure = None
        try:
            result = runner.run()
        except (ProviderError, RuntimeError) as error:
            failure = str(error)
        events = requests.get(control, timeout=5).json()["events"]
        posts = [event for event in events if event["method"] == "POST"]
        if mode == "success" or mode.startswith("qa_"):
            assert failure is None and result["technical_pass"]
            assert result["quality_score"] == (78 if mode == "qa_low_score" else 91)
            assert result["actual_cost_usd"] == "0.804100"
            expected = (
                "accepted"
                if mode in ("success", "qa_minor")
                else "local_edit"
                if mode == "qa_visible_major"
                else "manual_review"
            )
            assert result["quality_decision"] == expected
            assert result["quality_pass"] == (expected == "accepted")
            assert not result["published"] and not result["scheduler_enabled"]
            assert result["production_profile"]["audio_mode"] == "calm_music_in_postproduction"
            assert result["production_profile"]["duration_seconds"] == 15.8
            assert len(posts) == 4
            video_posts = [event for event in posts if event["path"] == "/videos"]
            assert len(video_posts) == 2
            assert "frame_images" not in video_posts[0]["body"]
            assert video_posts[1]["body"]["frame_images"][0]["frame_type"] == "first_frame"
            qa_post = [p for p in posts if p["path"] == "/chat/completions"][-1]
            video_url = qa_post["body"]["messages"][0]["content"][1]["video_url"]["url"]
            import subprocess

            proxy = Path(temporary) / "observed-request.mp4"
            proxy.write_bytes(base64.b64decode(video_url.split(",", 1)[1]))
            streams = json.loads(
                subprocess.check_output(
                    ["ffprobe", "-v", "error", "-show_streams", "-of", "json", str(proxy)],
                    timeout=30,
                )
            )["streams"]
            assert any(s["codec_name"] == "aac" for s in streams)
            assert runner.run() == result
        else:
            assert failure, mode
            before = len(posts)
            try:
                runner.run()
            except (ProviderError, RuntimeError):
                pass
            after = requests.get(control, timeout=5).json()["events"]
            assert sum(e["method"] == "POST" for e in after) == before, mode
            if mode == "price_increase":
                assert before == 0
            elif mode == "chat_error":
                assert before == 1
            else:
                assert before == 2
        with sessions() as session:
            charges = session.scalars(select(ModelUsage)).all()
            assert all(c.reserved_usd <= 1 for c in charges)
            assert not session.scalar(select(Publication))
            assert session.get(BudgetGuard, 1).frozen == (mode == "overrun")
            if mode in ("submit_error", "submit_timeout", "missing_cost", "chat_error"):
                assert any(c.actual_usd is None for c in charges)
        results.append(
            {
                "scenario": mode,
                "passed": True,
                "paid_post_count": len(posts),
                "failure": failure,
                "http_event_count": len(events),
            }
        )

# Fixed-origin, malformed identifiers and bounded download checks use actual HTTP.
requests.post(control, json={"mode": "success"}, timeout=5).raise_for_status()
provider = OpenRouter("synthetic-openrouter-key", base)
for invalid in (None, "https://untrusted.invalid/x", "../key", "x?token=y"):
    try:
        provider.job_path(invalid)
    except ProviderError:
        pass
    else:
        raise AssertionError("Untrusted job identifier accepted")
identifier = provider.submit(
    {
        "model": MODELS["video_model"],
        "duration": 8,
        "resolution": "1080p",
        "aspect_ratio": "9:16",
        "generate_audio": False,
    }
)
with tempfile.TemporaryDirectory() as temporary:
    target = Path(temporary) / "bounded.mp4"
    try:
        provider.download(identifier, target, maximum=10)
    except ProviderError:
        assert not target.exists() and not target.with_suffix(".partial").exists()
    else:
        raise AssertionError("Unbounded download")
assert str(usd("0.00000001")) == "0.000001"
evidence = {
    "provider": "local Postman HTTP stand-in",
    "real_credits_used": False,
    "database": "disposable PostgreSQL",
    "scenarios": results,
    "boundary_checks": "fixed origin, job IDs, download size/cleanup, rounded costs",
    "limitations": "Synthetic media and scores establish no real provider quality",
}
Path("docs/evidence/openrouter-simulation-audio-2026-11-05.json").write_text(
    json.dumps(evidence, indent=2) + "\n"
)
print(json.dumps(evidence, indent=2))
engine.dispose()
