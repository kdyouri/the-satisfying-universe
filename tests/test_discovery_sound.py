import subprocess
import wave
from copy import deepcopy

import pytest
from pydantic import ValidationError

from tsu.sound_design import SoundPlan, synthesize
from tsu.youtube_metadata import FIRST_VIDEO_LOCALIZATIONS, discovery_metadata


def test_discovery_preserves_six_texts_adds_relevant_tags_and_is_repeatable():
    original = deepcopy(FIRST_VIDEO_LOCALIZATIONS)
    metadata = discovery_metadata(
        original,
        ["#viral", "#WaterDrops", "#waterdrops", "#CeramicLeaf", "#bad tag"],
        tags=["keep-tag", "shorts"],
    )
    block = "#WaterDrops #CeramicLeaf #Satisfying #Shorts #TechnoInno"
    assert original == FIRST_VIDEO_LOCALIZATIONS
    for code, text in metadata["localizations"].items():
        assert text["title"] == original[code]["title"]
        assert text["description"].endswith(block)
        assert text["description"].count("#Shorts") == 1
        assert "#viral" not in text["description"]
    assert metadata["snippet"]["tags"] == [
        "keep-tag",
        "shorts",
        "WaterDrops",
        "CeramicLeaf",
        "Satisfying",
        "TechnoInno",
    ]
    assert (
        discovery_metadata(
            metadata["localizations"],
            ["#WaterDrops", "#CeramicLeaf"],
            tags=metadata["snippet"]["tags"],
        )
        == metadata
    )


@pytest.mark.parametrize("cues", [[], [16], [-1], [3, 2], [2, 2], [float("nan")]])
def test_drop_plan_rejects_unusable_or_out_of_bounds_events(cues):
    with pytest.raises(ValidationError):
        SoundPlan(kind="water_drops", cues_seconds=cues)


def test_synthesized_drops_have_quiet_gaps_and_audible_events(tmp_path):
    path = tmp_path / "drops.wav"
    info = synthesize(SoundPlan(kind="water_drops", cues_seconds=[2, 9]), path, 15.8)
    with wave.open(str(path)) as audio:
        assert audio.getnframes() / audio.getframerate() == 15.8
        audio.setpos(32000)
        quiet = audio.readframes(3200)
        audio.setpos(64000)
        impact = audio.readframes(3200)
    import struct

    def energy(data):
        values = struct.unpack("<" + "h" * (len(data) // 2), data)
        return sum(v * v for v in values) / len(values)

    assert energy(impact) > energy(quiet) * 100
    assert info["additional_audio_api_cost_usd"] == "0"
    with pytest.raises(ValueError, match="appropriate sound"):
        synthesize(SoundPlan(kind="needs_review"), path, 15.8)


def test_preview_preserves_source_and_video_stream_without_new_render(tmp_path):
    from tsu.media import inspect_final
    from tsu.production import sound_preview

    original = tmp_path / "original.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "color=c=blue:s=1080x1920:r=30:d=15.8",
            "-c:v",
            "libx264",
            "-threads",
            "1",
            "-preset",
            "ultrafast",
            "-pix_fmt",
            "yuv420p",
            str(original),
        ],
        check=True,
        capture_output=True,
        timeout=60,
    )
    before = original.read_bytes()
    preview = tmp_path / "preview.mp4"
    info = sound_preview(original, preview, SoundPlan(kind="water_drops", cues_seconds=[2, 9]))
    assert original.read_bytes() == before

    def video_hash(path):
        return subprocess.check_output(
            [
                "ffmpeg",
                "-v",
                "error",
                "-i",
                str(path),
                "-map",
                "0:v:0",
                "-c:v",
                "copy",
                "-f",
                "hash",
                "-hash",
                "sha256",
                "-",
            ],
            timeout=30,
        )

    assert video_hash(original) == video_hash(preview)
    assert inspect_final(preview, require_audio=True)["technical_pass"]
    assert not info["new_ai_review"] and not info["new_video_generation"]
