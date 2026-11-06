import shutil
import subprocess

import pytest

from tsu.media import inspect_final


@pytest.fixture(scope="module")
def media_samples(tmp_path_factory):
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        pytest.skip("FFmpeg/FFprobe unavailable")
    root = tmp_path_factory.mktemp("synthetic-media-fixtures")
    for name, size, duration, fps in [
        ("valid", "1080x1920", 16, 30),
        ("invalid", "640x360", 2, 24),
    ]:
        subprocess.run(
            [
                "ffmpeg",
                "-v",
                "error",
                "-f",
                "lavfi",
                "-i",
                f"color=c=blue:s={size}:r={fps}",
                "-t",
                str(duration),
                "-c:v",
                "libx264",
                "-preset",
                "ultrafast",
                "-pix_fmt",
                "yuv420p",
                "-movflags",
                "+faststart",
                str(root / f"{name}.mp4"),
            ],
            check=True,
            capture_output=True,
            timeout=90,
        )
    return root


def test_full_decode_and_final_master_technical_validation(media_samples):
    assert inspect_final(media_samples / "valid.mp4")["technical_pass"]


def test_wrong_duration_aspect_resolution_and_fps_are_rejected(media_samples):
    result = inspect_final(media_samples / "invalid.mp4")
    assert not result["technical_pass"]
    assert len(result["failures"]) >= 3


def test_new_profile_requires_audio(media_samples):
    result = inspect_final(media_samples / "valid.mp4", require_audio=True)
    assert not result["technical_pass"]
    assert "Exactly one audible soundtrack is required" in result["failures"]


def test_silent_audio_stream_is_not_accepted(media_samples, tmp_path):
    path = tmp_path / "silent.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-i",
            str(media_samples / "valid.mp4"),
            "-f",
            "lavfi",
            "-i",
            "anullsrc=r=48000:cl=stereo",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-t",
            "16",
            str(path),
        ],
        check=True,
        capture_output=True,
        timeout=60,
    )
    result = inspect_final(path, require_audio=True)
    assert not result["technical_pass"]
    assert "Soundtrack is silent or too close to clipping" in result["failures"]


def test_corrupt_video_is_not_accepted(tmp_path):
    if not shutil.which("ffprobe"):
        pytest.skip("FFprobe unavailable")
    path = tmp_path / "corrupt.mp4"
    path.write_bytes(b"not a video")
    with pytest.raises(subprocess.CalledProcessError):
        inspect_final(path)
