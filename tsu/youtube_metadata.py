"""Reusable six-language metadata policy, with the owner-requested first-video texts."""

import re
from copy import deepcopy

PUBLICATION_OPERATION = "youtube:public:six-languages:first-video:v1"
LANGUAGES = {
    "en": "English",
    "fr": "Français",
    "es": "Español",
    "it": "Italiano",
    "ru": "Русский",
    "zh-CN": "简体中文 · Mandarin",
}
HASHTAGS = "#Shorts #Satisfying #OddlySatisfying #TechnoInno"
FIRST_VIDEO_LOCALIZATIONS = {
    "en": {
        "title": "This Golden Spiral Is Hypnotic ✨",
        "description": (
            "Gentle motion, golden textures, and a few seconds to unwind.\n\n"
            "AI-generated visuals created for TechnoInno. Original music."
        ),
    },
    "fr": {
        "title": "Cette spirale dorée est hypnotisante ✨",
        "description": (
            "Un mouvement lent, une texture dorée, quelques secondes pour souffler.\n\n"
            "Création visuelle générée avec une IA pour TechnoInno. Musique originale."
        ),
    },
    "es": {
        "title": "Esta espiral dorada es hipnótica ✨",
        "description": (
            "Un movimiento suave, una textura dorada y unos segundos para relajarte.\n\n"
            "Imágenes generadas con IA para TechnoInno. Música original."
        ),
    },
    "it": {
        "title": "Questa spirale dorata è ipnotica ✨",
        "description": (
            "Un movimento lento, una texture dorata e qualche secondo per rilassarti.\n\n"
            "Immagini generate con l’IA per TechnoInno. Musica originale."
        ),
    },
    "ru": {
        "title": "Эта золотая спираль завораживает ✨",
        "description": (
            "Плавное движение, золотистая текстура и несколько секунд, чтобы расслабиться.\n\n"
            "Видео создано с помощью ИИ для TechnoInno. Оригинальная музыка."
        ),
    },
    "zh-CN": {
        "title": "令人着迷的金色螺旋 ✨",
        "description": (
            "舒缓的律动、金色的质感，给自己片刻放松。\n\n"
            "由人工智能为 TechnoInno 生成的画面，搭配原创音乐。"
        ),
    },
}
for translation in FIRST_VIDEO_LOCALIZATIONS.values():
    translation["description"] += "\n\n" + HASHTAGS


def localized_metadata(translations, category_id="24", tags=None):
    """Require a complete reviewed language set before any future media upload."""
    if set(translations) != set(LANGUAGES):
        raise ValueError("English, French, Spanish, Italian, Russian and Chinese are required")
    for text in translations.values():
        if set(text) != {"title", "description"}:
            raise ValueError("Each language requires only title and description")
        if not isinstance(text["title"], str) or not 1 <= len(text["title"]) <= 100:
            raise ValueError("YouTube titles must contain 1 to 100 characters")
        if not isinstance(text["description"], str) or not (
            1 <= len(text["description"].encode("utf-8")) <= 5000
        ):
            raise ValueError("YouTube descriptions must contain 1 to 5000 UTF-8 bytes")
        if any(c in text["title"] + text["description"] for c in "<>"):
            raise ValueError("YouTube text cannot contain angle brackets")
    return {
        "snippet": {
            **deepcopy(translations["en"]),
            "defaultLanguage": "en",
            "categoryId": category_id,
            "tags": list(tags or []),
        },
        "localizations": deepcopy(translations),
    }


def discovery_metadata(translations, hashtags, category_id="24", tags=None):
    """Small relevant subject/format block; no claim that tags guarantee distribution."""
    standard = ["Satisfying", "Shorts", "TechnoInno"]
    excluded = {x.casefold() for x in standard} | {"viral", "fyp", "trending", "foryou"}
    subject = []
    for value in hashtags:
        if not isinstance(value, str):
            continue
        match = re.fullmatch(r"#?([^\W_][\w]{1,35})", value.strip())
        if match and match[1].casefold() not in excluded:
            subject.append(match[1])
            excluded.add(match[1].casefold())
        if len(subject) == 2:
            break
    chosen = [*subject, *standard]
    block = " ".join("#" + word for word in chosen)
    updated = deepcopy(translations)
    for text in updated.values():
        description = re.sub(r"(?:\n[ \t]*)+(?:#[\w]+\s*)+$", "", text["description"])
        text["description"] = description.rstrip() + "\n\n" + block
    keywords = []
    seen = set()
    for value in [*(tags or []), *chosen]:
        if value.casefold() not in seen and len(",".join([*keywords, value]).encode()) <= 450:
            keywords.append(value)
            seen.add(value.casefold())
    return localized_metadata(updated, category_id=category_id, tags=keywords)
