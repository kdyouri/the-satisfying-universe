"""Pull a stopped-production VPS snapshot into age-encrypted owner storage on this Mac.

Requires the deployed snapshot helper and a separately protected age identity/recipient.
No scheduler, provider call, email send, retention deletion or restore is performed here.
"""

import argparse
import hashlib
import json
import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOST = "root@203.161.61.3"
SSH = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=12", HOST]


def encrypted_pull(command, output, age, recipient):
    temporary = output.with_suffix(output.suffix + ".partial")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    ssh = None
    try:
        with os.fdopen(descriptor, "wb") as destination:
            ssh = subprocess.Popen([*SSH, command], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            encrypted = subprocess.run(
                [str(age), "--encrypt", "--recipients-file", str(recipient)],
                stdin=ssh.stdout,
                stdout=destination,
                stderr=subprocess.PIPE,
                timeout=300,
            )
            ssh.stdout.close()
            _, remote_error = ssh.communicate(timeout=30)
        if encrypted.returncode or ssh.returncode:
            # Error bodies may include operational detail. Keep them out of chat/logs.
            raise RuntimeError("Encrypted backup transfer failed; partial output discarded")
        temporary.replace(output)
    finally:
        if ssh and ssh.poll() is None:
            ssh.kill()
            ssh.wait()
        temporary.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-confirmed-owner-backup", action="store_true")
    args = parser.parse_args()
    if not args.run_confirmed_owner_backup:
        print("Preview: encrypted database/media and separate recovery configuration; no action.")
        return
    age = ROOT / ".runtime/tools/age/age"
    recipient = ROOT / ".runtime/backup-keys/recipient.txt"
    if not age.is_file() or not recipient.is_file():
        raise RuntimeError("Install age and prepare the owner's protected recipient first")
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    directory = ROOT / "backups" / stamp
    directory.mkdir(parents=True, mode=0o700)
    directory.parent.chmod(0o700)
    encrypted_pull(
        "bash /opt/technoinno/deploy/snapshot-vps.sh",
        directory / "database-media.tar.age",
        age,
        recipient,
    )
    encrypted_pull("cat /opt/technoinno/.env", directory / "recovery.env.age", age, recipient)
    files = [
        {
            "name": path.name,
            "bytes": path.stat().st_size,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
        for path in directory.iterdir()
    ]
    evidence = {
        "directory": str(directory),
        "encrypted_files": files,
        "private_identity_in_backup": False,
        "automatic_schedule": False,
        "new_paid_calls": 0,
    }
    (directory / "transfer.json").write_text(json.dumps(evidence, indent=2) + "\n")
    print(json.dumps(evidence, indent=2))


if __name__ == "__main__":
    main()
