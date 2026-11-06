# The Satisfying Universe

Beautiful things. Perfect moments.

A modular Python platform for original AI video production. **Current milestone: the
first complete native-audio production cycle is validated live; recurring operation
still requires the outstanding owner prerequisites.** The existing public YouTube
sample has English, French, Spanish, Italian, Russian and Mandarin (simplified
Chinese) titles/descriptions.

Current launch scope: **YouTube only**, TechnoInno, https://studio.technoinno.live.
Instagram and TikTok are paused. Scheduling and global automatic spending/publication
remain disabled with zero budget caps. No paid generation or upload occurred during the implementation phase preceding
the separately authorized trial. See [readiness](docs/SCHEDULED_PRODUCTION_READINESS.md)
for the concrete private-trial proposal and remaining unattended-operation work.

138 regressions and 40 installed runtime checks pass. Local simulated providers establish
workflow/recovery behavior, not real model quality. The owner's original public video
and its six localized metadata pairs remain verified. PROJECT_STATUS.md records evidence.
The current regression suite is 182 tests without skips, including the native v3 trial.

Latest live result (2026-11-06): the first complete native-audio cycle succeeded with
`google/veo-3.1-lite` — one 8-second 1080p generation with native AI audio, quality
97/100, owner-accepted sound, uploaded privately as
https://www.youtube.com/watch?v=3a2YvpExzac with verified six-language metadata.
Trial cost 0.640755 USD within its 1.00 USD cap. The earlier 15-second candidate
(gemini-omni-1.2-flash) failed terminally at the provider twice and is retired; a
terminal-error polling defect found during those trials is fixed. See PROJECT_STATUS.md.

New jobs now use action-matched original synthesized effects instead of music. Legacy
jobs retain their captured sound profile. Relevant hashtags are added to all six localized
descriptions; the existing private trial metadata is verified on Google. A separate local
water-sound preview preserves its video stream but is not uploaded or newly AI-reviewed.
No new AI spending or media upload occurred for this change. See PROJECT_STATUS.md.

## Start here

- [Project status](PROJECT_STATUS.md): completed work, verification and blockers.
- [Architecture](ARCHITECTURE.md): services, durability, cost and security boundaries.
- [Implementation plan](IMPLEMENTATION_PLAN.md): milestones and acceptance criteria.
- [Cost estimate](COST_ESTIMATE.md): live-catalogue pricing and proposed benchmark.
- [Owner setup tasks](MANUAL_TASKS.md): separate brand accounts and secure handoffs.
- [Research](docs/RESEARCH.md): primary sources and unresolved platform constraints.
- [Operations](docs/OPERATIONS.md): local setup, container scaffold and recovery.
- [API contract](docs/API_CONTRACT.md), [OpenAPI](docs/openapi.json).

## What is implemented

Protected FastAPI control room, owner sessions/CSRF and encrypted Google OAuth grants;
PostgreSQL durable jobs and serialized budget reservations; per-job OpenRouter creative,
video and practical-review stages; original synthesized action effects and a short dissolve; approved
media upload and six-language verification; private/public publication reconciliation.
Per-job directories, hashes, paid intents and saved upload sessions preserve identity
across restarts. Unknown paid outcomes wait for review; no automatic paid regeneration.

Optional two local daily slots and a single Celery worker are implemented, with live
validation and durable Google-access gates. Times are unset and worker/Beat remain off.
The HTTPS studio, PostgreSQL and Redis are healthy. The private one-job live trial completed within its separately authorized
1.00 USD cap; no further paid sample is authorized. Off-host recovery and outbound notifications remain pending.

## Economic model profile

The owner requested lower-cost models with sufficient quality. Provisional choices are
Gemma 4 26B A4B for ideas, Gemini 3.1 Flash Lite for video review, and Veo 3.1 Lite for
video generation. IDs are configured on the VPS. The first two 8-second 1080p clips
and their review cost 0.800526 USD. The first review rejected the original join/motion;
the edited 15.8-second version adds music and a dissolve but has no new paid AI review.
Its private upload is an owner test, not automatic quality approval. See COST_ESTIMATE.md.
Automatic spending, public publishing and scheduling remain off.

## Development

Python 3.13 recommended. Create/activate a virtual environment, then install
`requirements.lock`. In this workspace, the prepared environment is `../.venv`.
Copy `.env.example` to `.env`, configure a strong local admin token, and leave
budgets at zero. Run migrations before starting the API. Follow OPERATIONS.md
for the SQLite inspection mode versus PostgreSQL workers/financial operations.

```sh
alembic upgrade head
uvicorn tsu.api:app --host 127.0.0.1 --port 8000
pytest -q
ruff check .
```

Database tests need `TSU_TEST_DATABASE_URL` pointing to a disposable PostgreSQL
database ending in `_test`. They clear its application data. Never use production.
The full locally verified suite includes PostgreSQL 15. The VPS Compose deployment
uses PostgreSQL 17 and has passed image build, migration, startup and runtime checks.

No secrets, account ownership changes, credit purchases or experimental uploads
are required to inspect the foundation. Public account URLs and “configured”
confirmation are enough for the next owner handoff; do not share credentials.
