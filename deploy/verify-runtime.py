"""Exercise the installed API over loopback. Print checks, never credentials.

Run from the VPS project folder:
docker compose -f compose.yaml -f compose.vps.yaml exec -T api python - < deploy/verify-runtime.py
This creates a temporary owner session/OAuth state and removes both on logout.
It does not contact Google, submit a job, spend money or upload content.
"""

import html
import json
import os
import re
from decimal import Decimal
from urllib.parse import parse_qs, urlsplit

import requests

BASE = os.environ.get("TSU_VERIFY_BASE", "http://127.0.0.1:8000")
checks = []


def check(condition, label):
    if not condition:
        raise RuntimeError(f"Runtime verification failed: {label}")
    checks.append(label)


def call(method, path, **kwargs):
    return requests.request(method, BASE + path, timeout=15, allow_redirects=False, **kwargs)


check(call("GET", "/health/live").status_code == 200, "live API responds")
for path in (
    "/admin",
    "/health/ready",
    "/api/overview",
    "/api/youtube/status",
    "/api/youtube/publication",
    "/api/youtube/publication/plan",
    "/api/youtube/test-upload",
    "/api/production/status",
    "/about",
    "/privacy",
    "/terms",
):
    check(call("GET", path).status_code == 401, f"anonymous access rejected: {path}")

login = call("GET", "/login")
check(login.status_code == 200, "login page renders")
check(
    login.headers.get("Referrer-Policy") == "strict-origin", "form policy preserves browser origin"
)
nonce = html.unescape(re.search(r'name="csrf" value="([^"]+)"', login.text).group(1))
nonce_cookie = login.cookies["__Host-tsu_login"]
check("Secure" in login.headers["Set-Cookie"], "login cookie requires HTTPS")
check(
    call("POST", "/login", data={"password": "invalid"}).status_code == 403,
    "login without CSRF rejected",
)
signed_in = call(
    "POST",
    "/login",
    headers={"Cookie": f"__Host-tsu_login={nonce_cookie}", "Origin": os.environ["PUBLIC_ORIGIN"]},
    data={"password": os.environ["ADMIN_TOKEN"], "csrf": nonce},
)
check(
    signed_in.status_code == 303 and signed_in.headers.get("Location") == "/admin",
    "real owner password accepted",
)
owner_cookie = signed_in.cookies["__Host-tsu_owner"]
cookie_flags = signed_in.headers["Set-Cookie"]
check(
    all(flag in cookie_flags for flag in ("Secure", "HttpOnly", "SameSite=lax")),
    "owner cookie security attributes present",
)
owner_headers = {
    "Cookie": f"__Host-tsu_owner={owner_cookie}",
    "Origin": os.environ["PUBLIC_ORIGIN"],
}
try:
    admin = call("GET", "/admin", headers=owner_headers)
    check(admin.status_code == 200 and "Connect YouTube" in admin.text, "owner dashboard renders")
    for page in ("/about", "/privacy", "/terms"):
        preview = call("GET", page, headers=owner_headers)
        check(
            preview.status_code == 200 and "Brouillon privé" in preview.text,
            "private owner draft renders: " + page,
        )
    csrf = html.unescape(re.search(r'name="csrf" value="([^"]+)"', admin.text).group(1))
    check(
        call("GET", "/health/ready", headers=owner_headers).status_code == 200,
        "database and migrations ready",
    )
    callback = call(
        "GET", "/auth/youtube/callback?state=runtime-invalid&code=synthetic", headers=owner_headers
    )
    check(
        callback.status_code == 400 and callback.headers.get("Referrer-Policy") == "no-referrer",
        "callback errors suppress referrer URLs",
    )
    overview = call("GET", "/api/overview", headers=owner_headers).json()
    check(
        not overview["email_alerts"]["enabled"] and not overview["email_alerts"]["configured"],
        "real email sending remains disabled and unconfigured",
    )
    check(
        Decimal(overview["daily_cap_usd"]) == 0 and Decimal(overview["monthly_cap_usd"]) == 0,
        "daily and monthly spending caps remain zero",
    )
    gates = overview["capabilities"]
    profile = gates["production_profile"]
    check(
        profile["version"] == "contextual_audio_v3"
        and profile["audio_mode"] == "action_matched_synthesized_effects",
        "new jobs use contextual sound effects",
    )
    check(
        not profile["automatic_music_fallback"] and profile["additional_audio_api_cost_usd"] == "0",
        "no automatic music fallback or paid sound service",
    )
    check("Hashtags pertinents" in admin.text, "dashboard explains hashtag and sound defaults")
    check(
        not any(
            gates[name]
            for name in (
                "generation_available",
                "publishing_available",
                "spending_authorized",
                "publishing_authorized",
            )
        ),
        "paid work and publishing disabled",
    )
    check(gates["youtube_oauth_configured"], "YouTube OAuth configuration present")
    check(os.environ["ENABLE_DAILY_SCHEDULER"].lower() == "false", "scheduler disabled")
    status = call("GET", "/api/youtube/status", headers=owner_headers).json()
    check(not status["publishing_enabled"], "YouTube publishing remains disabled")
    production = call("GET", "/api/production/status", headers=owner_headers)
    check(
        production.status_code == 200
        and production.json()["workflow_implemented"]
        and not production.json()["scheduler_enabled"]
        and not production.json()["configured_local_times"]
        and not production.json()["live_validation_completed"]
        and "budget_caps_zero" in production.json()["blockers"],
        "reusable workflow is installed with live scheduling and budgets off",
    )
    check(
        call(
            "POST",
            "/api/production/jobs",
            headers=owner_headers,
            json={"concept": "Synthetic verification must not create a task"},
        ).status_code
        == 403,
        "production job without CSRF rejected",
    )
    plan = call("GET", "/api/youtube/publication/plan", headers=owner_headers)
    check(
        plan.status_code == 200
        and set(plan.json()["languages"]) == {"en", "fr", "es", "it", "ru", "zh-CN"}
        and plan.json()["default_language"] == "en"
        and not plan.json()["scheduler_enabled"],
        "six-language plan is ready without enabling the scheduler",
    )
    check(
        call(
            "POST",
            "/api/youtube/publication",
            headers=owner_headers,
            json={"confirm_publication": True},
        ).status_code
        == 403,
        "public publication without CSRF rejected",
    )
    check(
        call("POST", "/auth/youtube/start", headers=owner_headers).status_code == 403,
        "YouTube connection without CSRF rejected",
    )
    start = call("POST", "/auth/youtube/start", headers=owner_headers, data={"csrf": csrf})
    check(start.status_code == 303, "YouTube connection initiation responds")
    destination = urlsplit(start.headers["Location"])
    parameters = parse_qs(destination.query)
    check(
        destination.scheme == "https" and destination.hostname == "accounts.google.com",
        "authorization points to official Google endpoint",
    )
    check(
        parameters.get("redirect_uri") == [os.environ["PUBLIC_ORIGIN"] + "/auth/youtube/callback"],
        "exact HTTPS callback configured",
    )
    check(
        parameters.get("code_challenge_method") == ["S256"]
        and bool(parameters.get("code_challenge")),
        "OAuth PKCE enabled",
    )
    check(
        set(parameters.get("scope", [""])[0].split())
        == {
            "https://www.googleapis.com/auth/youtube.upload",
            "https://www.googleapis.com/auth/youtube.readonly",
            "https://www.googleapis.com/auth/youtube.force-ssl",
        },
        "new owner consent requests the edit permission",
    )
    check(parameters.get("include_granted_scopes") == ["true"], "incremental consent enabled")
    check(
        call("POST", "/logout", headers=owner_headers).status_code == 403,
        "logout without CSRF rejected",
    )
finally:
    if "csrf" in locals():
        logged_out = call("POST", "/logout", headers=owner_headers, data={"csrf": csrf})
        check(logged_out.status_code == 303, "verification session logged out")

check(
    call("GET", "/admin", headers=owner_headers).status_code == 401, "logged-out session rejected"
)
print(
    json.dumps(
        {
            "checks_passed": checks,
            "check_count": len(checks),
            "google_contacted": False,
            "paid_requests": 0,
            "uploads": 0,
        },
        indent=2,
    )
)
