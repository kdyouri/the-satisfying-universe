#!/usr/bin/env bash
# Stream a snapshot to the owner's encryption process. No plaintext leaves SSH.
set -euo pipefail
umask 077
cd /opt/technoinno
running=$(docker compose -f compose.yaml -f compose.vps.yaml ps --services --status running)
if [[ "$running" == *worker* || "$running" == *beat* ]]; then
  echo 'Stop production before this supervised snapshot.' >&2
  exit 1
fi
mkdir -p backups
chmod 700 backups
snapshot=$(mktemp -d /opt/technoinno/backups/snapshot.XXXXXXXX)
trap 'rm -rf -- "$snapshot"' EXIT
docker compose -f compose.yaml -f compose.vps.yaml exec -T postgres \
  pg_dump -U tsu -d tsu --format=custom --no-owner --no-privileges > "$snapshot/database.dump"
docker compose -f compose.yaml -f compose.vps.yaml exec -T api python - \
  < deploy/backup-manifest.py > "$snapshot/manifest.json"
volume=$(docker volume inspect technoinno_media --format '{{.Mountpoint}}')
tar -C "$volume" -cf "$snapshot/media.tar" .
(
  cd "$snapshot"
  sha256sum database.dump media.tar manifest.json > SHA256SUMS
  tar -cf - database.dump media.tar manifest.json SHA256SUMS
)
