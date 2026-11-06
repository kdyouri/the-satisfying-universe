"""Reviewable contextual-sound trial; no paid action without a fresh explicit cap."""

import argparse
import json

from tsu.config import Settings
from tsu.db import make_engine
from tsu.trial import run_trial

KEY = "owner:contextual-sound-private-trial:v1"
THEME = (
    "A narrow clear stream of water flows slowly into a small turquoise ceramic basin, "
    "fixed macro camera and simple continuous motion. Gentle synthesized water-flow sound, "
    "no music, no people or lettering. Two complementary continuous views of the same basin."
)


def proposal():
    return {
        "theme": THEME,
        "visibility": "private",
        "channel": "@techno-inno",
        "maximum_additional_usd": "1.00",
        "quoted_video_generation_usd": "0.80",
        "maximum_reserved_stages_usd": "0.86",
        "audio": "original synthesized water-flow effects, no music",
        "languages": ["en", "fr", "es", "it", "ru", "zh-CN"],
        "hashtags_in_all_descriptions": True,
        "automatic_regeneration": False,
        "scheduler_activation": False,
        "requires_fresh_explicit_human_budget_authorization": True,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-confirmed-one-dollar-private-trial", action="store_true")
    parser.add_argument("--authorization-reference", default="")
    args = parser.parse_args()
    if not args.run_confirmed_one_dollar_private_trial:
        print(json.dumps(proposal(), ensure_ascii=False, indent=2))
        return
    settings = Settings()
    engine = make_engine(settings.database_url.get_secret_value())
    try:
        result = run_trial(
            settings,
            engine,
            authorized=True,
            reference=args.authorization_reference,
            trial_key=KEY,
            theme=THEME,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
