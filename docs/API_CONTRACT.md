# M1 admin API contract — agreed before implementation

Current override (2026-11-05): new production jobs use native_audio_v4, one 15-second
native AI video+audio generation, no montage and byte-preserved publication master.
The turquoise-basin trial is cancelled and must never be uploaded. See
[NATIVE_AUDIO_CONTRACT.md](NATIVE_AUDIO_CONTRACT.md) for the current price guards,
validation limits and pending live authorization. Legacy rendering references below
apply only to captured historical jobs, not to newly created production.


Local base URL: http://127.0.0.1:8000. No external provider side effects in M1.
Protected API paths accept `Authorization: Bearer <ADMIN_TOKEN>` or an authenticated
owner browser session. Public `/`, `/login` and `/health/live` are exceptions.
Browser writes require CSRF protection; see OAUTH_CONTRACT.md for the login/OAuth routes.
Google branding information at /about, /privacy and /terms is owner-protected by default.
Only the separate PUBLIC_INFORMATION_APPROVED setting makes these factual pages public
after the owner reviews the drafts. Administrative routes retain authentication.
The overview also reports whether owner email alerts are enabled/configured; never SMTP secrets.
No token in query strings. Missing token returns 401; bad token 401; absent server
configuration 503. Request bodies reject extra fields.
An unauthenticated browser GET /admin that accepts HTML redirects to /login (303).
This also covers expired/invalid browser sessions. API requests and explicit invalid
Bearer credentials continue returning 401; protected contents are never rendered first.

| Method/path | Contract |
|---|---|
| GET /health/live | Process liveness only, no database details |
| GET /health/ready | Protected DB readiness; 503 on unavailable database |
| GET /admin | Protected read-only status page; no secret values |
| GET /api/overview | Job-state counts, reserved/settled day/month USD, caps and gates, unresolved alerts; zeros mean no actual records |
| POST /api/jobs | `Idempotency-Key` required; body `{concept: string}`; returns 201 first time, 200 replay, 409 changed body; creates durable queued job only |
| GET /api/jobs | Bounded limit 1–100, newest first |
| GET /api/jobs/{id} | Durable job and preflight reason, 404 unknown |
| GET /api/alerts | Persistent unresolved operational alerts |
| GET /api/capabilities | Explicit disabled/unconfigured generation and publishing gates |
| GET /api/openapi.json | Protected generated OpenAPI contract |
| GET /api/youtube/status | Protected connection metadata only; never returns tokens or makes an implicit Google call |
| GET /api/youtube/test-upload/plan | Protected fixed sonorized preview, SHA/size and private French metadata; no Google upload |
| POST /api/youtube/test-upload | Strict `{confirm_private_test:true}`; one fixed private resumable test; 200 completed/reconciled, 202 processing, 409 safe conflict/interruption; never public or arbitrary paths |
| GET /api/youtube/test-upload | Protected current private-test state; reconciles a known video ID against Google, never sends media implicitly |
| GET /api/youtube/publication/plan | Protected six-language metadata, existing video ID and edit-consent status; no provider write |
| POST /api/youtube/publication | Strict `{confirm_publication:true}`; update and verify six translations, then publish the existing video; requires granted edit scope; no new upload, AI call or scheduler |
| GET /api/youtube/publication | Read current Google metadata/visibility and reconcile already-authorized publication state; never publishes implicitly |
| POST /api/production/jobs | Protected strict concept + visibility (private default), Idempotency-Key 1–120; persist a distinct reusable workflow job only; 201/200/409 |
| GET /api/production/status | Protected implementation/configuration/blockers, languages and account-approval state; no provider call or implicit task start |

`POST /api/jobs` does not reserve money or call a provider. Job acceptance remains
available while Redis is offline: dispatcher finds the row later. Inputs use canonical
JSON hashing; idempotency is scoped to this single-owner application. A duplicate key
with different input is a client conflict, not a new task. Jobs stop at
`awaiting_configuration` in this milestone; no progress claim is inferred from queueing.

Schema source of truth is FastAPI/Pydantic; `docs/openapi.json` is its generated,
versioned snapshot. Regenerate with `python scripts/export_openapi.py`; a test detects drift.
No Swagger UI is exposed. The browser owner login and YouTube connection routes are
implemented and deployed. Read/upload consent is verified live; edit consent is a
separate owner step for modifying the existing video. The private-test status endpoint
also reports public visibility after the explicit one-video publication operation;
the original upload POST never makes the video public. See YOUTUBE_MULTILINGUAL_CONTRACT.md.
