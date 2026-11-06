"""Decrypt and verify an owner backup; restore PostgreSQL only into a new isolated database."""

import argparse
import hashlib
import json
import os
import shlex
import shutil
import subprocess
import tarfile
import tempfile
from pathlib import Path
from uuid import uuid4

from cryptography.fernet import Fernet
from dotenv import dotenv_values

from tsu import models  # noqa: F401 -- register every application table
from tsu.db import Base

ROOT = Path(__file__).resolve().parents[1]
HOST = "root@203.161.61.3"
SSH = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=12", HOST]
COMPOSE = [
    "docker",
    "compose",
    "-f",
    "/opt/technoinno/compose.yaml",
    "-f",
    "/opt/technoinno/compose.vps.yaml",
    "exec",
    "-T",
    "postgres",
]


def remote(args, **kwargs):
    return subprocess.run(
        [*SSH, shlex.join(args)], capture_output=True, check=True, timeout=180, **kwargs
    )


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("backup", type=Path)
    parser.add_argument("--run-confirmed-restore-drill", action="store_true")
    args = parser.parse_args()
    if not args.run_confirmed_restore_drill:
        print("Preview: isolated temporary database only; no action.")
        return
    backup = args.backup.resolve()
    assert backup.is_relative_to((ROOT / "backups").resolve()) and backup.is_dir()
    identity = ROOT / ".runtime/backup-keys/owner-age.key"
    assert identity.stat().st_mode & 0o077 == 0
    age = ROOT / ".runtime/tools/age/age"
    suffix = uuid4().hex
    database = "tsu_restore_" + suffix
    remote_dir = "/opt/technoinno/backups/restore." + suffix
    created = False
    report = {}
    with tempfile.TemporaryDirectory(prefix="restore-drill-", dir=ROOT / ".runtime") as temp:
        work = Path(temp)
        try:
            for source, name in [
                ("database-media.tar.age", "backup.tar"),
                ("recovery.env.age", "recovery.env"),
            ]:
                output = work / name
                subprocess.run(
                    [
                        str(age),
                        "--decrypt",
                        "--identity",
                        str(identity),
                        "--output",
                        str(output),
                        str(backup / source),
                    ],
                    check=True,
                    capture_output=True,
                    timeout=180,
                )
                output.chmod(0o600)
            with tarfile.open(work / "backup.tar") as archive:
                archive.extractall(work / "snapshot", filter="data")
            snapshot = work / "snapshot"
            expected_files = {"database.dump", "media.tar", "manifest.json"}
            for row in (snapshot / "SHA256SUMS").read_text().splitlines():
                expected_hash, name = row.split()
                assert name in expected_files and digest(snapshot / name) == expected_hash
                expected_files.remove(name)
            assert not expected_files
            manifest = json.loads((snapshot / "manifest.json").read_text())
            with tarfile.open(snapshot / "media.tar") as archive:
                archive.extractall(work / "media", filter="data")
            for item in manifest["media"]:
                path = (work / "media" / item["path"]).resolve()
                assert path.is_relative_to((work / "media").resolve())
                assert path.stat().st_size == item["bytes"] and digest(path) == item["sha256"]
            recovery = dotenv_values(work / "recovery.env")
            remote(["mkdir", "-m", "700", remote_dir])
            subprocess.run(
                [
                    "scp",
                    "-o",
                    "BatchMode=yes",
                    "-o",
                    "ConnectTimeout=12",
                    str(snapshot / "database.dump"),
                    HOST + ":" + remote_dir + "/database.dump",
                ],
                check=True,
                capture_output=True,
                timeout=90,
            )
            remote([*COMPOSE, "createdb", "-U", "tsu", "--template=template0", database])
            created = True
            # Stream the dump into PostgreSQL's own version-matched restore client.
            command = (
                "cat "
                + shlex.quote(remote_dir + "/database.dump")
                + " | "
                + shlex.join(
                    [
                        *COMPOSE,
                        "pg_restore",
                        "-U",
                        "tsu",
                        "-d",
                        database,
                        "--exit-on-error",
                        "--no-owner",
                        "--no-privileges",
                    ]
                )
            )
            subprocess.run(
                [*SSH, "bash", "-o", "pipefail", "-c", shlex.quote(command)],
                check=True,
                capture_output=True,
                timeout=180,
            )
            names = list(manifest["database"]["counts"])
            assert set(names).issubset(Base.metadata.tables)
            pairs = ",".join(f"'{name}',(SELECT count(*) FROM {name})" for name in names)
            query = (
                "SELECT json_build_object('counts',json_build_object(" + pairs + "),"
                "'schema_revision',(SELECT version_num FROM alembic_version),"
                "'credentials',(SELECT json_agg(credentials_encrypted) FROM oauth_credentials),"
                "'jobs',(SELECT json_object_agg(id,status) FROM production_jobs),"
                "'publications',(SELECT json_agg(remote_id) FROM publications));"
            )
            result = remote(
                [
                    *COMPOSE,
                    "psql",
                    "-U",
                    "tsu",
                    "-d",
                    database,
                    "-XAtq",
                    "-v",
                    "ON_ERROR_STOP=1",
                    "-c",
                    query,
                ]
            )
            restored = json.loads(result.stdout)
            assert restored["counts"] == manifest["database"]["counts"]
            assert restored["schema_revision"] == manifest["database"]["schema_revision"]
            assert restored["jobs"] == manifest["database"]["job_statuses"]
            assert sorted(restored["publications"]) == sorted(
                manifest["database"]["publication_ids"]
            )
            credentials = restored["credentials"] or []
            assert credentials
            for encrypted in credentials:
                raw = json.loads(
                    Fernet(recovery["TOKEN_ENCRYPTION_KEY"].encode()).decrypt(encrypted.encode())
                )
                assert raw.get("refresh_token")
                assert raw["client_id"] == recovery["YOUTUBE_CLIENT_ID"]
            corrupt = work / "corrupt.age"
            shutil.copyfile(backup / "recovery.env.age", corrupt)
            data = bytearray(corrupt.read_bytes())
            data[-1] ^= 1
            corrupt.write_bytes(data)
            rejected = subprocess.run(
                [str(age), "--decrypt", "--identity", str(identity), str(corrupt)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                timeout=15,
            )
            assert rejected.returncode != 0
            report = {
                "backup_directory": str(backup),
                "age_version": "1.3.2",
                "encrypted_backup_integrity_verified": True,
                "tampered_copy_rejected": True,
                "media_files_verified": len(manifest["media"]),
                "media_bytes_verified": sum(x["bytes"] for x in manifest["media"]),
                "restored_counts": restored["counts"],
                "schema_revision": restored["schema_revision"],
                "job_states_and_publication_ids_match": True,
                "google_grants_decrypt_with_recovered_key": True,
                "isolated_database_only": True,
                "production_database_overwritten": False,
                "restored_workers_started": False,
                "provider_calls": 0,
                "automatic_offhost_backup": False,
            }
        finally:
            if created:
                remote([*COMPOSE, "dropdb", "-U", "tsu", database])
            remote(["rm", "-rf", "--", remote_dir])
    report["plaintext_temporary_files_removed"] = True
    report["isolated_restore_database_removed"] = True
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    os.umask(0o077)
    main()
