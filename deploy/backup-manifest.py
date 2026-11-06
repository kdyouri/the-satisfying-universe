"""Inventory for a stopped-production snapshot; prints hashes/counts, never credentials."""

import hashlib
import json

from sqlalchemy import func, select, text

from tsu.config import Settings
from tsu.db import Base, make_engine, make_sessions
from tsu.models import ModelUsage, ProductionJob, Publication, VideoGeneration

s = Settings()
assert not any((s.enable_daily_scheduler, s.spending_authorized, s.publishing_authorized))
e = make_engine(s.database_url.get_secret_value())
try:
    with make_sessions(e)() as db:
        counts = {
            name: db.scalar(select(func.count()).select_from(table))
            for name, table in Base.metadata.tables.items()
            if name not in {"owner_sessions", "oauth_flows"}
        }
        state = {
            "schema_revision": db.scalar(text("SELECT version_num FROM alembic_version")),
            "counts": counts,
            "confirmed_usd": str(db.scalar(select(func.sum(ModelUsage.actual_usd)))),
            "held_usd": str(
                db.scalar(
                    select(func.sum(ModelUsage.reserved_usd)).where(ModelUsage.actual_usd.is_(None))
                )
            ),
            "job_statuses": dict(db.execute(select(ProductionJob.id, ProductionJob.status)).all()),
            "publication_ids": list(db.scalars(select(Publication.remote_id))),
            "generation_count": db.scalar(select(func.count()).select_from(VideoGeneration)),
        }
    media = []
    for path in sorted(s.data_root.rglob("*")):
        if path.is_file():
            with path.open("rb") as stream:
                digest = hashlib.file_digest(stream, "sha256").hexdigest()
            media.append(
                {
                    "path": str(path.relative_to(s.data_root)),
                    "bytes": path.stat().st_size,
                    "sha256": digest,
                }
            )
    print(
        json.dumps({"database": state, "media": media, "workers_stopped_snapshot": True}, indent=2)
    )
finally:
    e.dispose()
