import json
import subprocess
from pathlib import Path

import pytest

from tsu.media import inspect_final
from tsu.production import SOUNDTRACK, production_profile, render_final, review_proxy


def test_render_and_review_keep_audible_music_and_valid_duration(tmp_path):
    clip = tmp_path / "clip.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "color=c=blue:s=1080x1920:r=24:d=8",
            "-c:v",
            "libx264",
            "-threads",
            "1",
            "-preset",
            "ultrafast",
            "-pix_fmt",
            "yuv420p",
            str(clip),
        ],
        check=True,
        capture_output=True,
        timeout=60,
    )
    final = tmp_path / "final.mp4"
    editing = render_final([clip, clip], final)
    technical = inspect_final(final, require_audio=True)
    assert technical["technical_pass"], technical["failures"]
    assert editing["duration_seconds"] == 15.8
    assert -60 < technical["audio_levels"]["mean_db"] < -10
    assert technical["audio_levels"]["peak_db"] <= -0.5
    proxy = tmp_path / "review.mp4"
    review_proxy(final, proxy)
    metadata = json.loads(
        subprocess.check_output(
            ["ffprobe", "-v", "error", "-show_streams", "-of", "json", str(proxy)],
            timeout=30,
        )
    )
    assert [s["codec_name"] for s in metadata["streams"] if s["codec_type"] == "audio"] == ["aac"]
    assert proxy.stat().st_size < 6 * 1024 * 1024


def test_missing_music_blocks_render(tmp_path):
    assert SOUNDTRACK.is_file() and production_profile()["audio_ready"]
    with pytest.raises(RuntimeError, match="Soundtrack missing"):
        render_final([Path("first"), Path("second")], tmp_path / "final.mp4", tmp_path / "missing")
