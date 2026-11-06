"""Synthetic full render in the worker memory profile; no model, DB or YouTube call."""

import json
import resource
import subprocess
from pathlib import Path

from tsu.media import inspect_final
from tsu.production import render_final, review_proxy, run_ffmpeg
from tsu.workflow import JobProducer  # noqa: F401 — load the real workflow's dependencies
from tsu.youtube_job import YouTubeJob  # noqa: F401 — load the actual publishing dependencies

directory = Path("/data/validation/production-workflow-20261105")
directory.mkdir(parents=True, exist_ok=True)
clips = [directory / f"synthetic-clip-{n}.mp4" for n in (1, 2)]
for clip, color in zip(clips, ("0x061d3a", "0x0a2840"), strict=True):
    run_ffmpeg(
        "-f",
        "lavfi",
        "-i",
        f"color=c={color}:s=1080x1920:r=30:d=8",
        "-an",
        "-c:v",
        "libx264",
        "-threads",
        "1",
        "-preset",
        "ultrafast",
        "-crf",
        "35",
        "-pix_fmt",
        "yuv420p",
        clip,
    )
final = directory / "worker-render.mp4"
editing = render_final(clips, final)
technical = inspect_final(final, require_audio=True)
assert technical["technical_pass"]
proxy = directory / "worker-review.mp4"
review_proxy(final, proxy)
metadata = json.loads(
    subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_streams", "-of", "json", str(proxy)], timeout=30
    )
)
assert any(s["codec_name"] == "aac" for s in metadata["streams"])
limit = int(Path("/sys/fs/cgroup/memory.max").read_text())
peak = int(Path("/sys/fs/cgroup/memory.peak").read_text())
assert limit == 512 * 1024 * 1024 and peak <= limit
print(
    json.dumps(
        {
            "synthetic_media_only": True,
            "real_provider_calls": 0,
            "new_publications": 0,
            "technical_pass": True,
            "duration_seconds": editing["duration_seconds"],
            "resolution": "1080x1920",
            "final_and_review_audio": "AAC, audible final checked",
            "worker_memory_limit_mib": limit / (1024 * 1024),
            "worker_cgroup_peak_mib": round(peak / (1024 * 1024), 2),
            "maximum_ffmpeg_child_rss_mib": round(
                resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss / 1024, 2
            ),
        },
        indent=2,
    )
)
