"""Per-video YouTube statistics collection and per-category performance report."""

import argparse
import json
from collections import defaultdict
from datetime import UTC, datetime
from decimal import Decimal

import requests
from sqlalchemy import delete, select

from tsu.categories import category_of
from tsu.config import Settings
from tsu.db import make_engine, make_sessions
from tsu.models import (
    Analytics,
    OAuthCredential,
    ProductionJob,
    Publication,
    SocialAccount,
    Video,
    VideoGeneration,
)
from tsu.youtube_auth import YouTubeConnections

METRICS = ("view_count", "like_count", "comment_count")
SOURCE_PREFIX = "youtube-videos-list"


def _refreshed_token(settings, engine):
    with make_sessions(engine)() as db:
        account = db.scalar(
            select(SocialAccount).where(
                SocialAccount.platform == "youtube",
                SocialAccount.external_id == settings.youtube_channel_id,
            )
        )
        credential = db.scalar(
            select(OAuthCredential).where(OAuthCredential.account_id == account.id)
        )
        raw = json.loads(
            YouTubeConnections(settings, make_sessions(engine))
            .cipher()
            .decrypt(credential.credentials_encrypted.encode())
        )
    token = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "grant_type": "refresh_token",
            "refresh_token": raw["refresh_token"],
            "client_id": raw["client_id"],
            "client_secret": settings.youtube_client_secret.get_secret_value(),
        },
        timeout=(10, 30),
    ).json()
    if not token.get("access_token"):
        raise RuntimeError("YouTube token refresh failed")
    return token["access_token"]


def _fetch_statistics(settings, engine, video_ids, token_getter=_refreshed_token):
    token = token_getter(settings, engine)
    response = requests.get(
        "https://www.googleapis.com/youtube/v3/videos",
        params={"part": "statistics", "id": ",".join(video_ids)},
        headers={"Authorization": "Bearer " + token},
        timeout=(10, 30),
    )
    response.raise_for_status()
    return {item["id"]: item.get("statistics", {}) for item in response.json().get("items", [])}


def collect(settings, engine, fetch=None):
    """Store today's per-video statistics for our published videos."""
    fetch = fetch or _fetch_statistics
    source = SOURCE_PREFIX + ":" + datetime.now(UTC).date().isoformat()
    sessions = make_sessions(engine)
    with sessions() as db:
        rows = db.execute(
            select(Publication.remote_id, Publication.id).where(
                Publication.remote_id.is_not(None),
                Publication.status.in_(["processed_public", "published"]),
            )
        ).all()
    if not rows:
        return {"collected": 0, "reason": "no public publications"}
    remote_to_publication = {remote: publication_id for remote, publication_id in rows}
    statistics = fetch(settings, engine, list(remote_to_publication))
    collected = 0
    with sessions.begin() as db:
        for remote, stats in statistics.items():
            publication_id = remote_to_publication.get(remote)
            if publication_id is None:
                continue
            for metric in METRICS:
                db.execute(
                    delete(Analytics).where(
                        Analytics.publication_id == publication_id,
                        Analytics.metric == metric,
                        Analytics.source == source,
                    )
                )
                value = stats.get(metric)
                db.add(
                    Analytics(
                        publication_id=publication_id,
                        metric=metric,
                        value=Decimal(value) if value else Decimal(0),
                        source=source,
                    )
                )
                collected += 1
    return {"collected": collected, "videos": len(statistics), "source": source}


def _publication_category(db, publication_id):
    video_id = db.scalar(select(Publication.video_id).where(Publication.id == publication_id))
    generation_id = db.scalar(select(Video.generation_id).where(Video.id == video_id))
    job_id = db.scalar(select(VideoGeneration.job_id).where(VideoGeneration.id == generation_id))
    concept = db.scalar(
        select(ProductionJob.payload["concept"].as_string()).where(ProductionJob.id == job_id)
    )
    return category_of(concept or "")


def report(settings, engine):
    sessions = make_sessions(engine)
    with sessions() as db:
        rows = db.execute(
            select(Analytics.publication_id, Analytics.metric, Analytics.value).where(
                Analytics.metric.in_(METRICS)
            )
        ).all()
        per_publication = defaultdict(dict)
        for publication_id, metric, value in rows:
            per_publication[publication_id][metric] = int(value or 0)
        categories = defaultdict(lambda: {"videos": 0, "views": 0, "likes": 0, "comments": 0})
        for publication_id, stats in per_publication.items():
            key = _publication_category(db, publication_id) or "uncategorized"
            bucket = categories[key]
            bucket["videos"] += 1
            bucket["views"] += stats.get("view_count", 0)
            bucket["likes"] += stats.get("like_count", 0)
            bucket["comments"] += stats.get("comment_count", 0)
    summary = []
    for key, totals in sorted(categories.items()):
        videos = max(totals["videos"], 1)
        summary.append(
            {
                "category": key,
                "videos": totals["videos"],
                "total_views": totals["views"],
                "avg_views": round(totals["views"] / videos, 1),
                "total_likes": totals["likes"],
                "avg_likes": round(totals["likes"] / videos, 1),
                "avg_comments": round(totals["comments"] / videos, 1),
            }
        )
    summary.sort(key=lambda item: item["avg_views"], reverse=True)
    return {"generated_at": datetime.now(UTC).isoformat(), "categories": summary}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--collect", action="store_true")
    parser.add_argument("--report", action="store_true")
    args = parser.parse_args()
    settings = Settings()
    engine = make_engine(settings.database_url.get_secret_value())
    try:
        if args.collect:
            print(json.dumps(collect(settings, engine), indent=2))
        if args.report or not args.collect:
            print(json.dumps(report(settings, engine), ensure_ascii=False, indent=2))
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
