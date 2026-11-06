import json
import re
import subprocess
from fractions import Fraction
from math import isfinite
from pathlib import Path


def inspect_final(path: Path, *, require_audio: bool = False, native_seconds=None) -> dict:
    """Validate a local final master. Technical success does not imply visual approval."""
    path = path.resolve(strict=True)
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    metadata = json.loads(result.stdout)
    streams = metadata.get("streams", [])
    video = [s for s in streams if s.get("codec_type") == "video"]
    failures = []
    if len(video) != 1:
        failures.append("Exactly one video stream is required")
    else:
        stream = video[0]
        if (stream.get("width"), stream.get("height")) != (1080, 1920):
            failures.append("Master must be 1080x1920")
        if stream.get("codec_name") != "h264" or stream.get("pix_fmt") != "yuv420p":
            failures.append("Master must use H.264/yuv420p")
        if stream.get("sample_aspect_ratio") not in ("1:1", None):
            failures.append("Master must use square pixels")
        fps = Fraction(stream.get("avg_frame_rate", "0/1"))
        if native_seconds is not None and not 24 <= fps <= 60:
            failures.append("Native frame rate must remain between 24 and 60 fps")
        elif native_seconds is None and fps != 30:
            failures.append("Master must be 30 fps")
        duration = float(stream.get("duration", metadata.get("format", {}).get("duration", 0)))
        if native_seconds is None and not 15 <= duration <= 20.05:
            failures.append("Master must be 15–20 seconds")
        if native_seconds is not None and abs(duration - native_seconds) > 0.2:
            failures.append("Native duration differs from the single-generation plan")
        if any(s.get("rotation", 0) != 0 for s in stream.get("side_data_list", [])):
            failures.append("Rotation metadata must be normalized")
    if "mp4" not in metadata.get("format", {}).get("format_name", "").split(","):
        failures.append("Master must use MP4 container")
    if any(s.get("codec_name") != "aac" for s in streams if s.get("codec_type") == "audio"):
        failures.append("Audio must use AAC")
    audio = [s for s in streams if s.get("codec_type") == "audio"]
    audio_levels = None
    if require_audio:
        if len(audio) != 1:
            failures.append("Exactly one audible soundtrack is required")
        else:
            video_duration = float(metadata["format"]["duration"])
            audio_duration = float(audio[0].get("duration", 0))
            if abs(video_duration - audio_duration) > 0.15:
                failures.append("Audio and video durations must match")
            measured = subprocess.run(
                [
                    "ffmpeg",
                    "-hide_banner",
                    "-i",
                    str(path),
                    "-vn",
                    "-af",
                    "volumedetect",
                    "-f",
                    "null",
                    "-",
                ],
                check=True,
                capture_output=True,
                text=True,
                timeout=120,
            )
            levels = dict(re.findall(r"(mean_volume|max_volume): ([\-\w.]+) dB", measured.stderr))
            mean = float(levels.get("mean_volume", "-inf"))
            peak = float(levels.get("max_volume", "-inf"))
            audio_levels = {
                "mean_db": mean if isfinite(mean) else None,
                "peak_db": peak if isfinite(peak) else None,
            }
            if mean < -60 or peak > -0.5:
                failures.append("Soundtrack is silent or too close to clipping")
    # Decode all frames, not just a successful header probe.
    subprocess.run(
        ["ffmpeg", "-v", "error", "-xerror", "-threads", "1", "-i", str(path), "-f", "null", "-"],
        check=True,
        capture_output=True,
        timeout=120,
    )
    return {
        "technical_pass": not failures,
        "failures": failures,
        "metadata": metadata,
        "audio_levels": audio_levels,
    }
