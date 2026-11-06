"""Call the protected private-test API without printing credentials.

Run inside the installed API container, passing plan, upload or status as argv[1].
Only upload performs the one explicitly authorized private media transfer.
"""

import json
import os
import sys

import requests

action = sys.argv[1]
if action not in {"plan", "upload", "status"}:
    raise SystemExit("Use plan, upload or status")
path = "/api/youtube/test-upload" + ("/plan" if action == "plan" else "")
kwargs = {"json": {"confirm_private_test": True}} if action == "upload" else {}
try:
    response = requests.request(
        "POST" if action == "upload" else "GET",
        "http://127.0.0.1:8000" + path,
        headers={"Authorization": "Bearer " + os.environ["ADMIN_TOKEN"]},
        timeout=(10, 150),
        **kwargs,
    )
except requests.RequestException:
    raise SystemExit("Connection interrupted; query or resume the same saved operation") from None
try:
    result = response.json()
except ValueError:
    raise SystemExit(f"API returned HTTP {response.status_code} without JSON") from None
print(
    json.dumps(
        {"http_status": response.status_code, "result": result}, ensure_ascii=False, indent=2
    )
)
if response.status_code not in {200, 202}:
    raise SystemExit(1)
