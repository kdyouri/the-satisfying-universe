"""Invoke the installed fixed-video publication API; never print credentials."""

import json
import os
import sys

import requests

action = sys.argv[1]
if action not in {"plan", "status", "publish"}:
    raise SystemExit("Use plan, status or publish")
path = "/api/youtube/publication" + ("/plan" if action == "plan" else "")
kwargs = {"json": {"confirm_publication": True}} if action == "publish" else {}
try:
    response = requests.request(
        "POST" if action == "publish" else "GET",
        "http://127.0.0.1:8000" + path,
        headers={"Authorization": "Bearer " + os.environ["ADMIN_TOKEN"]},
        timeout=(10, 150),
        **kwargs,
    )
except requests.RequestException:
    raise SystemExit(
        "Connection interrupted; query the existing publication before resuming"
    ) from None
try:
    result = response.json()
except ValueError:
    raise SystemExit(f"API returned HTTP {response.status_code} without JSON") from None
print(
    json.dumps(
        {"http_status": response.status_code, "result": result}, ensure_ascii=False, indent=2
    )
)
if response.status_code != 200:
    raise SystemExit(1)
