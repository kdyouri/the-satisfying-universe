"""Shared defaults for future manual video renders and practical quality reviews."""

import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

from tsu.sound_design import SoundPlan, synthesize

PROFILE = "balanced_audio_v2"
SOUNDTRACK = Path(__file__).resolve().parent / "assets/calm-original.wav"
CROSSFADE_SECONDS = 0.2


def production_profile(soundtrack: Path = SOUNDTRACK) -> dict:
    return {
        "version": PROFILE,
        "audio_mode": "calm_music_in_postproduction",
        "audio_ready": soundtrack.is_file(),
        "audio_target_lufs": -24,
        "native_generated_audio": False,
        "crossfade_seconds": CROSSFADE_SECONDS,
        "quality_minimum_score": 80,
        "quality_visibility": "normal_playback_on_phone",
        "minor_defects": "accepted",
        "visible_major_defects": "timestamped_evidence_required",
        "repair_priority": "local_edit",
        "uncertain_findings": "manual_review",
        "automatic_regeneration": False,
    }


def run_ffmpeg(*arguments):
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *map(str, arguments)],
        check=True,
        capture_output=True,
        timeout=240,
    )


def duration(path: Path) -> float:
    response = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(path)],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return float(json.loads(response.stdout)["format"]["duration"])


def render_final(
    clips: list[Path],
    destination: Path,
    soundtrack: Path = SOUNDTRACK,
    *,
    sound_plan: SoundPlan | None = None,
) -> dict:
    if len(clips) != 2:
        raise ValueError("The current render profile requires two clips")
    if sound_plan is None and not soundtrack.is_file():
        raise RuntimeError("Soundtrack missing; stop before producing a silent final")
    lengths = [duration(clip) for clip in clips]
    total = sum(lengths) - CROSSFADE_SECONDS
    if min(lengths) <= CROSSFADE_SECONDS or not 15 <= total <= 20.05:
        raise ValueError("The rendered duration must remain between 15 and 20 seconds")
    sound_details = {}
    if sound_plan is not None:
        soundtrack = destination.with_suffix(".effects.wav")
        sound_details = synthesize(sound_plan, soundtrack, total)
    graph = (
        # FFmpeg 7 clears frame-rate metadata in setpts; fps must follow it for xfade.
        "[0:v]setpts=PTS-STARTPTS,fps=30,format=yuv420p[v0];"
        "[1:v]setpts=PTS-STARTPTS,fps=30,format=yuv420p[v1];"
        f"[v0][v1]xfade=transition=fade:duration={CROSSFADE_SECONDS}:"
        "offset=0,format=yuv420p[v]"
    )
    encode = [
        "-c:v",
        "libx264",
        "-threads",
        "1",
        "-preset",
        "veryfast",
        "-crf",
        "18",
        "-pix_fmt",
        "yuv420p",
        "-video_track_timescale",
        "15360",
    ]
    temporary = destination.with_name(destination.stem + ".rendering.mp4")
    try:
        # Render only the short overlap with two decoders. Full simultaneous 1080p
        # inputs exceed the 384 MiB pilot limit on the 1 GiB VPS.
        with tempfile.TemporaryDirectory(prefix=".render-", dir=destination.parent) as folder:
            work = Path(folder)
            prefix, join, suffix = [
                work / name for name in ("prefix.mp4", "join.mp4", "suffix.mp4")
            ]
            run_ffmpeg(
                "-filter_threads",
                "1",
                "-threads",
                "1",
                "-i",
                clips[0],
                "-vf",
                "setpts=PTS-STARTPTS,fps=30,format=yuv420p",
                "-an",
                "-t",
                lengths[0] - CROSSFADE_SECONDS,
                *encode,
                prefix,
            )
            run_ffmpeg(
                "-filter_complex_threads",
                "1",
                "-threads",
                "1",
                "-ss",
                lengths[0] - CROSSFADE_SECONDS,
                "-t",
                CROSSFADE_SECONDS,
                "-i",
                clips[0],
                "-threads",
                "1",
                "-t",
                CROSSFADE_SECONDS,
                "-i",
                clips[1],
                "-filter_complex",
                graph,
                "-map",
                "[v]",
                "-an",
                "-t",
                CROSSFADE_SECONDS,
                *encode,
                join,
            )
            run_ffmpeg(
                "-filter_threads",
                "1",
                "-threads",
                "1",
                "-ss",
                CROSSFADE_SECONDS,
                "-i",
                clips[1],
                "-vf",
                "setpts=PTS-STARTPTS,fps=30,format=yuv420p",
                "-an",
                "-t",
                lengths[1] - CROSSFADE_SECONDS,
                *encode,
                suffix,
            )
            listing = work / "concat.txt"
            listing.write_text("file 'prefix.mp4'\nfile 'join.mp4'\nfile 'suffix.mp4'\n")
            audio_filter = (
                f"atrim=duration={total},asetpts=PTS-STARTPTS,loudnorm=I=-24:TP=-2:LRA=7,"
                f"afade=t=in:st=0:d=0.5,afade=t=out:st={total - 0.8}:d=0.8"
            )
            run_ffmpeg(
                "-filter_threads",
                "1",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                listing,
                "-stream_loop",
                "-1",
                "-i",
                soundtrack,
                "-map",
                "0:v:0",
                "-map",
                "1:a:0",
                "-c:v",
                "copy",
                "-af",
                audio_filter,
                "-c:a",
                "aac",
                "-b:a",
                "128k",
                "-ar",
                "48000",
                "-ac",
                "2",
                "-t",
                total,
                "-movflags",
                "+faststart",
                temporary,
            )
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)
    return {
        **production_profile(soundtrack),
        **sound_details,
        "duration_seconds": total,
        "soundtrack_sha256": hashlib.sha256(soundtrack.read_bytes()).hexdigest(),
        "soundtrack_source": sound_details.get(
            "soundtrack_source", "original local synthesis; no external samples"
        ),
    }


def sound_preview(master: Path, destination: Path, plan: SoundPlan) -> dict:
    """Create a separate local variant, copying all video frames; never overwrite approval."""
    if master.resolve() == destination.resolve():
        raise ValueError("Sound preview must preserve the approved original")
    seconds = duration(master)
    soundtrack = destination.with_suffix(".effects.wav")
    details = synthesize(plan, soundtrack, seconds)
    temporary = destination.with_name(destination.stem + ".rendering.mp4")
    try:
        run_ffmpeg(
            "-i",
            master,
            "-i",
            soundtrack,
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-c:v",
            "copy",
            "-af",
            "loudnorm=I=-24:TP=-2:LRA=7,afade=t=in:st=0:d=0.03,"
            f"afade=t=out:st={seconds - 0.15}:d=0.15",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-ar",
            "48000",
            "-ac",
            "2",
            "-t",
            seconds,
            "-movflags",
            "+faststart",
            temporary,
        )
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)
    return {**details, "new_video_generation": False, "new_ai_review": False}


def review_proxy(master: Path, destination: Path):
    run_ffmpeg(
        "-filter_threads",
        "1",
        "-threads",
        "1",
        "-i",
        master,
        "-vf",
        "scale=540:960",
        "-c:v",
        "libx264",
        "-threads",
        "1",
        "-preset",
        "veryfast",
        "-crf",
        "24",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "64k",
        "-movflags",
        "+faststart",
        destination,
    )
    if destination.stat().st_size > 6 * 1024 * 1024:
        raise RuntimeError("Review copy exceeds the request limit; stop before billing")


def review_instruction(concept: str, seconds: float, audio_mode: str | None = None) -> str:
    if audio_mode == "native_ai_generated_audio":
        return f"""Review this single continuous {seconds:.2f}-second satisfying video at normal
phone playback speed. Concept: {concept}. Both visuals and sound were generated together by AI.
There is no montage or added soundtrack. Score realism /25, motion /20, aesthetics /20,
prompt compliance /20, technical /15. Threshold 80; small discrete imperfections and details
only visible when paused or zoomed are tolerated. Do not invent theoretical physics defects.
Report only concrete observed issues with start/end times and evidence; mark uncertain findings
uncertain. A major issue clearly harms normal viewing: broken geometry, sustained flicker,
obvious cut, jarring or clearly mismatched audio. Judge synchronized material-appropriate
environmental sounds, no music or speech. Quiet sound is allowed. Set audio_coherence to
not_observable if you cannot hear it. The original passed full decoding, 1080x1920 H.264/AAC,
native frame-rate and audible-audio checks. Technical validity is separate from subjective realism.
The attached 540x960 copy with audio is for review only; never penalize its review resolution.
No editing or paid regeneration is authorized. Use manual_review for a clear problem that would
require altering the output. Leave severe_defects empty and use issues instead. Minor issues
do not veto approval. Explain findings in French. Return only the requested JSON."""
    instruction = f"""Review this {seconds:.2f}-second satisfying video as a viewer watching
at normal speed on a phone. Concept: {concept}.
Score realism /25, motion /20, aesthetics /20, prompt compliance /20, technical /15.
Small discrete artifacts and details noticeable only by pausing or zooming are tolerated.
Do not invent physics defects from theory or expect laboratory-perfect realism.
For each issue give a start/end time, a concrete description and observable evidence.
A major issue must clearly harm normal viewing: obvious jump, sustained flicker,
broken geometry, jarring audio or clearly mismatched sound. A short subtle dissolve
is intentional editing and is not itself a defect. Mark uncertain observations uncertain.
Prefer local_edit for a fixable transition, audio level or trim. Never order a paid retry.
Use issues for findings and leave the legacy severe_defects list empty.
The master passed complete FFmpeg decoding and 1080x1920, H.264/30fps/AAC checks;
technical_pass concerns file validity, not subjective motion realism.
The attached full-duration review copy is 540x960 WITH its soundtrack. Do not penalize
its review resolution. Judge audio coherence; use not_observable if you cannot hear it.
The score threshold is 80; minor issues do not veto it. Explain findings in French.
Return only the requested JSON."""
    if audio_mode == "action_matched_synthesized_effects":
        instruction += (
            "\nThis version uses original synthesized action effects, not background music. "
            "Check that water, friction, grains or rolling sounds fit the visible material and "
            "that distinct impacts match visible events. Quiet subtle sound is intentional; "
            "not every movement needs a plop. Clearly unrelated, repetitive or mistimed effects "
            "are an audio coherence problem and should route to local editing with timestamps."
        )
    return instruction
