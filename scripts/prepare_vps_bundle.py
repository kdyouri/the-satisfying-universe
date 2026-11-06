"""Prepare a reviewable local release. Does not connect to or modify the VPS."""

import hashlib
import json
import os
import secrets
import tarfile
from pathlib import Path

from cryptography.fernet import Fernet
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / ".runtime"
RUNTIME.mkdir(mode=0o700, exist_ok=True)
RUNTIME.chmod(0o700)
source = dotenv_values(ROOT / ".env")
destination = RUNTIME / "vps.env"
prepared = dotenv_values(destination) if destination.exists() else {}

for field in ("OPENROUTER_API_KEY", "YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET"):
    if not source.get(field):
        raise SystemExit(f"Required local configuration is missing: {field}")

password = prepared.get("POSTGRES_PASSWORD") or secrets.token_urlsafe(36)
owner = prepared.get("ADMIN_TOKEN") or secrets.token_urlsafe(48)
key = prepared.get("TOKEN_ENCRYPTION_KEY") or Fernet.generate_key().decode()
values = {
    "ADMIN_TOKEN": owner,
    "POSTGRES_PASSWORD": password,
    "DATABASE_URL": f"postgresql+psycopg://tsu:{password}@postgres:5432/tsu",
    "REDIS_URL": "redis://redis:6379/0",
    "TZ": "Africa/Casablanca",
    "DATA_ROOT": "/data",
    "DAILY_BUDGET_USD": "0",
    "MONTHLY_BUDGET_USD": "0",
    "SPENDING_AUTHORIZED": "false",
    "PUBLISHING_AUTHORIZED": "false",
    "ENABLE_DAILY_SCHEDULER": "false",
    "OPENROUTER_API_KEY": source["OPENROUTER_API_KEY"],
    "CREATIVE_MODEL": source.get("CREATIVE_MODEL") or "google/gemma-4-26b-a4b-it",
    "QUALITY_MODEL": source.get("QUALITY_MODEL") or "google/gemini-3.1-flash-lite",
    "VIDEO_MODEL": source.get("VIDEO_MODEL") or "google/gemini-omni-1.2-flash",
    "YOUTUBE_CLIENT_ID": source["YOUTUBE_CLIENT_ID"],
    "YOUTUBE_CLIENT_SECRET": source["YOUTUBE_CLIENT_SECRET"],
    "PUBLIC_ORIGIN": "https://studio.technoinno.live",
    "YOUTUBE_LOGIN_HINT": "admin.technoinno@gmail.com",
    "YOUTUBE_CHANNEL_ID": "UC8DbuevZRxVTWxltG9oDFRw",
    "YOUTUBE_HANDLE": "@techno-inno",
    "TOKEN_ENCRYPTION_KEY": key,
}


def env_quote(value):
    return "'" + str(value).replace("\\", "\\\\").replace("'", "\\'") + "'"


descriptor = os.open(destination, os.O_CREAT | os.O_TRUNC | os.O_WRONLY, 0o600)
with os.fdopen(descriptor, "w") as target:
    target.write(
        "# Prepared locally; never commit or display. Deployment requires owner approval.\n"
    )
    target.write("\n".join(f"{name}={env_quote(value)}" for name, value in values.items()) + "\n")
destination.chmod(0o600)

access_file = RUNTIME / "OWNER_ACCESS.txt"
descriptor = os.open(access_file, os.O_CREAT | os.O_TRUNC | os.O_WRONLY, 0o600)
with os.fdopen(descriptor, "w") as target:
    target.write("TechnoInno Studio — prepared owner access\n\n")
    target.write("Not active until deployment and HTTPS are verified.\n")
    target.write("Login: https://studio.technoinno.live/login\n")
    target.write(f"Owner password: {owner}\n\n")
    target.write("This is the studio password, not your Google password. Keep this file private.\n")
access_file.chmod(0o600)

include = (
    "tsu",
    "migrations",
    "deploy",
    "alembic.ini",
    "requirements.lock",
    "pyproject.toml",
    "Dockerfile",
    ".dockerignore",
    "compose.yaml",
    "compose.vps.yaml",
    "compose.pilot.yaml",
)
archive = RUNTIME / "technoinno-release.tar.gz"
files = []
with tarfile.open(archive, "w:gz") as target:
    for item in include:
        path = ROOT / item
        paths = sorted(path.rglob("*")) if path.is_dir() else [path]
        for entry in paths:
            if not entry.is_file() or "__pycache__" in entry.parts or entry.suffix == ".pyc":
                continue
            relative = entry.relative_to(ROOT).as_posix()
            if entry.name == ".env" or relative.startswith(".runtime/"):
                raise RuntimeError("Secret file cannot enter the code archive")
            target.add(entry, arcname=relative)
            files.append(
                {"path": relative, "sha256": hashlib.sha256(entry.read_bytes()).hexdigest()}
            )
archive.chmod(0o600)
(ROOT / "docs/evidence/prepared-vps-release.json").write_text(
    json.dumps(
        {
            "prepared_on": "2026-11-04",
            "deployed": False,
            "secrets_in_archive": False,
            "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
            "files": files,
        },
        indent=2,
    )
    + "\n"
)
print(f"Prepared {len(files)} code/config files; credentials stored separately and privately.")
print("No server connection, deployment, paid request or upload was performed.")
