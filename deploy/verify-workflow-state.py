"""Read-only installed workflow status; never creates a job or provider request."""

import json
import os

import requests

response = requests.get(
    "http://127.0.0.1:8000/api/production/status",
    headers={"Authorization": "Bearer " + os.environ["ADMIN_TOKEN"]},
    timeout=20,
)
response.raise_for_status()
status = response.json()
assert status["workflow_implemented"]
assert not status["scheduler_enabled"]
assert not status["live_validation_completed"]
assert not status["configured_local_times"]
assert not status["account_publication_approved"]
assert status["languages"] == ["en", "fr", "es", "it", "ru", "zh-CN"]
assert set(status["blockers"]) == {
    "spending_not_authorized",
    "budget_caps_zero",
    "automatic_publication_not_authorized",
    "daily_times_not_selected",
    "durable_google_access_not_confirmed",
    "complete_live_cycle_not_validated",
    "account_publication_not_authorized",
}
print(json.dumps(status, ensure_ascii=False, indent=2))
