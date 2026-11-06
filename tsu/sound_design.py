"""Original action sound synthesis; no recordings, music, paid service or external samples."""

import hashlib
import math
import random
import wave
from array import array
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator

from tsu.contracts import StrictModel

PROFILE = "contextual_audio_v3"


class SoundPlan(StrictModel):
    kind: Literal[
        "water_drops", "liquid_flow", "soft_grains", "soft_friction", "soft_roll", "needs_review"
    ]
    cues_seconds: list[float] = Field(default_factory=list, max_length=12)

    @model_validator(mode="after")
    def bounded_cues(self):
        if any(not math.isfinite(t) or not 0 <= t < 15.8 for t in self.cues_seconds):
            raise ValueError("Sound cues must fall within the final 15.8 seconds")
        if self.kind in {"water_drops", "soft_roll"} and not self.cues_seconds:
            raise ValueError("Impact/rolling sound requires explicit visible-event cues")
        if self.cues_seconds != sorted(set(self.cues_seconds)):
            raise ValueError("Use distinct sound cues in chronological order")
        return self


def contextual_profile():
    return {
        "version": PROFILE,
        "audio_mode": "action_matched_synthesized_effects",
        "audio_ready": True,
        "audio_target_lufs": -24,
        "native_generated_audio": False,
        "automatic_music_fallback": False,
        "unsupported_sound": "manual_review_before_video_spend",
        "sound_kinds": ["water_drops", "liquid_flow", "soft_grains", "soft_friction", "soft_roll"],
        "external_samples": False,
        "additional_audio_api_cost_usd": "0",
        "automatic_regeneration": False,
    }


def synthesize(plan: SoundPlan, path: Path, seconds: float) -> dict:
    if plan.kind == "needs_review":
        raise ValueError("Choose an appropriate sound before generating video")
    if not 15 <= seconds <= 20.05 or any(t >= seconds for t in plan.cues_seconds):
        raise ValueError("Sound plan is outside the actual video duration")
    rate = 32000
    count = round(rate * seconds)
    samples = array("f", [0.0]) * count
    seed = int(hashlib.sha256(plan.model_dump_json().encode()).hexdigest()[:16], 16)
    rng = random.Random(seed)
    # Broadband filtered texture, not a sustained pitched pad or melody.
    smooth = previous = 0.0
    for index in range(count):
        noise = rng.uniform(-1, 1)
        smooth = 0.94 * smooth + 0.06 * noise
        fine = noise - previous
        previous = noise
        t = index / rate
        if plan.kind == "liquid_flow":
            value = (0.7 * smooth + 0.04 * fine) * (0.65 + 0.25 * math.sin(t * 1.7))
        elif plan.kind == "soft_grains":
            value = (0.3 * smooth + 0.035 * fine) * (0.4 + 0.6 * rng.random() ** 8)
        elif plan.kind == "soft_friction":
            value = (0.6 * smooth + 0.015 * fine) * (0.5 + 0.4 * math.sin(t * 2.3) ** 2)
        elif plan.kind == "soft_roll":
            value = 0.4 * smooth * (0.55 + 0.35 * math.sin(t * 19) ** 2)
        else:
            value = 0.012 * smooth
        samples[index] = value
    for cue in plan.cues_seconds:
        start = round(cue * rate)
        f0 = rng.uniform(900, 1700) if plan.kind == "water_drops" else rng.uniform(180, 420)
        for offset in range(min(round(0.32 * rate), count - start)):
            t = offset / rate
            attack = min(1, t / 0.0015)
            ring = math.sin(2 * math.pi * (f0 * t + f0 * 1.8 * t * t)) * math.exp(-t * 34)
            splash = rng.uniform(-1, 1) * math.exp(-t * 95)
            samples[start + offset] += attack * (0.48 * ring + 0.16 * splash)
    peak = max(abs(v) for v in samples) or 1
    pcm = array("h")
    for index, value in enumerate(samples):
        t = index / rate
        fade = min(1, t / 0.03, max(0, seconds - t) / 0.08)
        pcm.append(round(value / peak * 0.58 * fade * 32767))
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as output:
        output.setparams((1, 2, rate, 0, "NONE", "not compressed"))
        output.writeframes(pcm.tobytes())
    return {
        **contextual_profile(),
        "sound_plan": plan.model_dump(),
        "soundtrack_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "soundtrack_source": "original locally synthesized action effects; no external samples",
        "duration_seconds": seconds,
    }
