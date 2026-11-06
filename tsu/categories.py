"""Owner-defined rotating content categories with one shared visual identity."""

import re
from datetime import date

ANCHOR_DATE = date(2026, 11, 6)

CATEGORIES = (
    (
        "oddly_satisfying",
        "Perfect cuts, seamless fits, clever mechanisms and satisfying transformations; "
        "precise, deliberate motion.",
    ),
    (
        "surreal_impossible",
        "Impossible scenes, miniature worlds and dreamlike visual illusions that stay coherent.",
    ),
    (
        "hypnotic_visuals",
        "Liquids, colors, symmetries and repetitive mesmerizing motion.",
    ),
    (
        "ai_comedy_animals",
        "Animals in human-like situations, gentle visual humor and surprising twists; "
        "family-friendly and kind.",
    ),
    (
        "relaxing_magical_worlds",
        "Miniature gardens, fantastical landscapes, nature and escape; a calm magical atmosphere.",
    ),
)

IDENTITY = (
    "Keep the shared TechnoInno visual identity: one continuous scene, soft cinematic "
    "macro lighting, a calming palette, realistic physics, no people, no cuts, no text."
)

CATEGORY_PATTERN = re.compile(r"^Content category ([a-z_]+): ")


def category_for(date_iso: str, slot: int) -> str:
    """Deterministic round-robin: two slots per day cycle through all categories."""
    day_number = (date.fromisoformat(date_iso) - ANCHOR_DATE).days
    index = (day_number * 2 + (slot - 1)) % len(CATEGORIES)
    return CATEGORIES[index][0]


def theme_for(key: str) -> str:
    description = dict(CATEGORIES)[key]
    return f"Content category {key}: {description} {IDENTITY}"


def category_of(concept: str) -> str | None:
    match = CATEGORY_PATTERN.match(concept or "")
    return match.group(1) if match else None
