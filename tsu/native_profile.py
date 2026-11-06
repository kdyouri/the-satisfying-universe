"""Owner-selected single-generation policy; a price ceiling grants no spend authority."""

VERSION = "native_audio_v5"
MODEL = "google/veo-3.1-lite"
SECONDS = 8
MAX_GENERATION_USD = "0.70"
NATIVE_VERSIONS = ("native_audio_v4", VERSION)

# Superseded 15-second candidate profile retained for its stopped trial jobs.
V4 = {
    "version": "native_audio_v4",
    "model": "google/gemini-omni-1.2-flash",
    "duration": 15,
    "resolution": "1080p",
    "aspect_ratio": "9:16",
    "generate_audio": True,
    "duration_seconds": 15,
    "clip_count": 1,
    "audio_mode": "native_ai_generated_audio",
    "postproduction": False,
    "master_preserved": True,
    "background_music": False,
    "minimum_score": 80,
    "minor_defects_tolerated": True,
    "automatic_regeneration": False,
    "maximum_generation_usd": "1.60",
    "live_validation_completed": False,
}


def generation_parameters(seconds=SECONDS):
    return {
        "duration": seconds,
        "resolution": "1080p",
        "aspect_ratio": "9:16",
        "generate_audio": True,
    }


def native_profile():
    return {
        "version": VERSION,
        "model": MODEL,
        **generation_parameters(),
        "duration_seconds": SECONDS,
        "clip_count": 1,
        "audio_mode": "native_ai_generated_audio",
        "postproduction": False,
        "master_preserved": True,
        "background_music": False,
        "minimum_score": 80,
        "minor_defects_tolerated": True,
        "automatic_regeneration": False,
        "maximum_generation_usd": MAX_GENERATION_USD,
        "live_validation_completed": False,
    }


def is_native(profile):
    return (profile.get("version") if isinstance(profile, dict) else profile) in NATIVE_VERSIONS
