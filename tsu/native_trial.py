"""One owner-authorized native-audio trial; global scheduling remains off."""

import argparse
import json
from decimal import Decimal

from tsu.config import Settings
from tsu.db import make_engine
from tsu.native_profile import V4, native_profile
from tsu.trial import run_trial
from tsu.trial_policy import (
    NATIVE2_KEY,
    NATIVE2_LIMIT,
    NATIVE2_THEME,
    NATIVE3_KEY,
    NATIVE3_LIMIT,
    NATIVE3_THEME,
    NATIVE_KEY,
    NATIVE_LIMIT,
    NATIVE_THEME,
)

TRIALS = {
    "v1": (NATIVE_KEY, NATIVE_LIMIT, NATIVE_THEME),
    "v2": (NATIVE2_KEY, NATIVE2_LIMIT, NATIVE2_THEME),
    "v3": (NATIVE3_KEY, NATIVE3_LIMIT, NATIVE3_THEME),
}
PROFILES = {"v1": V4, "v2": V4, "v3": native_profile()}


def proposal(version="v1"):
    key, limit, theme = TRIALS[version]
    profile = PROFILES[version]
    return {
        "operation": key,
        "theme": theme,
        "channel": "@techno-inno",
        "visibility": "private",
        "maximum_additional_usd": limit,
        "maximum_reserved_stages_usd": str(
            Decimal(profile["maximum_generation_usd"]) + Decimal("0.06")
        ),
        "profile": profile,
        "languages": ["en", "fr", "es", "it", "ru", "zh-CN"],
        "hashtags_in_all_descriptions": True,
        "scheduler_activation": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", choices=sorted(TRIALS), default="v1")
    parser.add_argument("--run-confirmed-private-trial", action="store_true")
    parser.add_argument("--authorization-reference", default="")
    args = parser.parse_args()
    key, limit, theme = TRIALS[args.version]
    if not args.run_confirmed_private_trial:
        print(json.dumps(proposal(args.version), ensure_ascii=False, indent=2))
        return
    settings = Settings()
    engine = make_engine(settings.database_url.get_secret_value())
    try:
        print(
            json.dumps(
                run_trial(
                    settings,
                    engine,
                    authorized=True,
                    reference=args.authorization_reference,
                    trial_key=key,
                    theme=theme,
                ),
                ensure_ascii=False,
                indent=2,
            )
        )
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
