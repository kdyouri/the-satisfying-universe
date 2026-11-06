# Operations — foundation, not a launched production service

## Local development

Python environment is currently at `../.venv` relative to this project.
For a new clone: `python3.13 -m venv .venv`, activate it, then
`python -m pip install -r requirements.lock`.
Copy `.env.example` to `.env`; create a random ADMIN_TOKEN of at least 32 characters
locally, and do not paste it into chat. Do not enable spending/publishing flags.

For a temporary local-only check, set `DATABASE_URL=sqlite:///./development.db`, run
`alembic upgrade head`, then `uvicorn tsu.api:app --host 127.0.0.1`.
SQLite supports admin inspection and API tests only. Worker claims and financial writes
deliberately require PostgreSQL. The health endpoint never implies production readiness.

Use an HTTP client with a Bearer header for protected `/admin`, `/api/*` and readiness.
Browser owner login now uses Secure/HttpOnly host-only cookies, server-side session
hashes, CSRF and eight-hour expiry. Use it over verified HTTPS with PUBLIC_ORIGIN
configured. The owner password is ADMIN_TOKEN; prepared VPS owner access is stored
privately in ignored .runtime/OWNER_ACCESS.txt and is active after verified VPS deployment and HTTPS.
Rotating ADMIN_TOKEN invalidates existing browser sessions. No secrets go in query
strings or browser local storage. Local HTTP inspection can use bearer headers.
Create reusable jobs at POST /api/production/jobs with a stable Idempotency-Key.
They persist without Redis or provider calls; GET /api/production/status explains gates.
Execution belongs to ProductionWorkflow/the bounded worker, not the API process.
The scheduler remains off by default; configure exactly two explicit HH:MM local times
only after owner agreement. Keep PRODUCTION_LIVE_VALIDATED and
YOUTUBE_LONG_LIVED_GRANT_CONFIRMED false until supported by real evidence.

## Docker Compose — onboarding verified on the VPS

Fill the application DATABASE_URL and POSTGRES_PASSWORD consistently; URL-encode
special password characters in the database URL. `docker compose config --quiet`
validates configuration. On the VPS use both configuration files and start only API:
`docker compose -f compose.yaml -f compose.vps.yaml up -d --build api`.
This starts migrations, PostgreSQL and Redis. Worker/Beat remain off during onboarding;
do not use an unrestricted base-file `up` command because it includes those services.
Only the API binds a loopback host port. No automatic S3 service/account is provisioned.
Use private S3-compatible storage in M3, with separately authorized hosting costs.
Image tags and dependencies should be security reviewed and pinned to image digests
before production. The present lockfile pins Python packages but not OS packages.

## Verification

`pytest -q` runs local contract/quality tests. Set `TSU_TEST_DATABASE_URL` to an
**empty disposable PostgreSQL database** to include migration/locking tests. The
fixture drops application tables in that test database. Never use a production URL.
`ruff check .` checks source style. `alembic check` compares schema to models.
`python scripts/export_openapi.py` refreshes the API contract snapshot.

## Backups (procedure prepared; automated off-host backup pending)

Before launch, schedule daily PostgreSQL custom-format dumps using a protected
connection configuration and `pg_dump --format=custom --file=BACKUP_PATH`.
Do not put passwords in command-line arguments. Encrypt backup files and replicate
to an off-host location with limited credentials. Apply object versioning/lifecycle
to originals and finals; back up the media manifest and secret-manager recovery
separately. Redis is reconstructible transport, not the production record.

Google grants and in-progress PKCE verifiers are now encrypted in the database.
Back up TOKEN_ENCRYPTION_KEY separately from database dumps in owner-controlled
encrypted storage. Without the original key a restored grant cannot be decrypted;
do not rotate it casually. Test restoring the key and grant before unattended uploads.

Restore a dump into an isolated empty database with `pg_restore`, verify migration
revision, row counts, object checksums, and interrupted-job visibility, then start
workers with spending/publishing disabled. Never test restoration by overwriting
the production database. Record a real restore drill before launch. Retention
proposal: 7 daily + 4 weekly encrypted DB backups, reviewed against cost and policy.

## Recovery and alerting

The reusable dispatcher resumes saved per-job state with bounded recovery. Known
remote generation IDs and encrypted upload sessions are reconciled before further
writes. Unknown paid submissions require owner attention; never clear their intents
or ledger reservations to force a retry. Accepted media can await publication authority
without rerunning generation/review. The global workflow advisory lock, paid-intent row
locks and upload locks serialize competing callers. Dashboard alerts are deduplicated.
Unknown charges remain reserved.
Over-reservation cost settlement freezes future spending and creates a persistent alert.
Budget-stop alerts are database records available through `/api/alerts`; outbound
email/chat notifications are not connected and require owner destination/authorization.
Do not clear a freeze without verifying usage and adjusting the quote calculation.


## Installed VPS

Host root@203.161.61.3, project /opt/technoinno, public studio
https://studio.technoinno.live/login. API/PostgreSQL/Redis are healthy; worker/Beat
remain off. Deployment root is 0700 and .env 0600. Certificate expires 2027-02-02;
Certbot timer and Nginx reload hook are installed and passed a renewal dry run.
Run `certbot renew --cert-name studio.technoinno.live --dry-run --run-deploy-hooks`
for a future renewal check. The reusable workflow and six-language publication adapters are installed. The future
single prefork worker uses a 512 MiB cap; worker/Beat remain off. Global paid/scheduling/
publication flags and caps remain off. No unrestricted Compose up is authorized.

## Prepared private validation

`python -m tsu.trial` previews one private trial without creating a job or calling
providers. Only after the owner explicitly authorizes its maximum 1.00 USD additional
spend, execute the confirmed-run option with a human authorization reference in a
bounded one-off worker container. Do not place secrets in that reference. The fixed
trial idempotency key resumes the same job; a stopped quality decision is not permission
to regenerate. Its per-job private publication authority cannot publish publicly or
approve the account globally. Global environment flags/caps stay unchanged.

Record actual charges, quality routing, private processing and six localized metadata
readbacks. A successful cycle can support PRODUCTION_LIVE_VALIDATED only after review;
it does not authorize recurring spending. The complete activation conditions are in
SCHEDULED_PRODUCTION_READINESS.md.

## Completed scoped private trial and supervision limits

The fixed trial is completed_private, video G9wNpynDbPY. Re-running the same operation
returns saved completion; do not create another job to force a review. Two extra
calls were explicitly authorized after an automatic-approval block and have been used.
The private-trial review helpers are operator-only recovery tools, bound to the existing
trial; they are not configured in Beat or worker dispatch. Preserve all three unresolved
review reservations (0.14 USD), plus earlier legacy holds, until per-request evidence
supports settlement. Account-level usage alone does not settle an individual request.
The dashboard alert now records cost reconciliation rather than an unfinished video.

Native trials are versioned: `python -m tsu.native_trial --version v2` shows the
v2 proposal (2.00 USD cap, free creative subject); v1 keeps its fixed 1.70 USD theme.
Both v1 and v2 native generations failed terminally at the provider without cost
evidence; their reservations remain held and their jobs are owner_attention. A parsed
provider error body (HTTP 200 with an `error` field) now raises ProviderTerminalError
and stops polling immediately instead of silently retrying until the deadline; paid
POSTs are still never retried.

The native Gemini request uses a compact structure schema and the verified standard
AI Studio endpoint; the full Pydantic validation still enforces every score, timestamp,
audio and severity requirement. The default reusable client allows 300s for review
reads. Unknown paid outcomes still stop, with no automatic repeated POST. Keep
PRODUCTION_LIVE_VALIDATED false until the owner reviews the supervised result and
unattended-operation preparation is accepted. No recurring activation is implied.

## Prelaunch preparation update — 2026-11-05

The first encrypted Mac backup and real isolated restore passed. Use scripts/backup_vps.py
for the supervised pull and scripts/restore_backup_drill.py for an isolated drill. age
identity stays at .runtime/backup-keys outside backups/; recovery configuration is a
separate ciphertext. No automatic retention deletion or always-on off-host schedule is
installed. OFFHOST_BACKUP_CONFIRMED remains false until that recurring capability is real.

Owner SMTP notifications are installed, disabled and unconfigured. Readiness is available
through overview/production status and python -m tsu.notifications without sending.
The local private .runtime/email-alerts.env is a setup template, not live server credentials.
Unknown SMTP acceptance remains a durable attempted/uncertain state, with no automatic
resend. OUTBOUND_ALERTS_CONFIRMED remains false until an authorized real delivery is received.

/about, /privacy and /terms are private owner previews while PUBLIC_INFORMATION_APPROVED
is false. Owner review/publication approval is separate from deployment. Google consent
and application publication remain personal actions. Current Testing status is not durable.

python -m tsu.sound_trial only prints the prepared capped private proposal. Its run flag
and human authorization reference are reserved for a fresh explicit 1 USD approval.
The old completed trial and its holds must never be reset to repeat production.
