# Reusable production workflow — authorized implementation, live controls off

Current override (2026-11-05): new production jobs use native_audio_v4, one 15-second
native AI video+audio generation, no montage and byte-preserved publication master.
The turquoise-basin trial is cancelled and must never be uploaded. See
[NATIVE_AUDIO_CONTRACT.md](NATIVE_AUDIO_CONTRACT.md) for the current price guards,
validation limits and pending live authorization. Legacy rendering references below
apply only to captured historical jobs, not to newly created production.


Owner approved completing and testing the reusable workflow. This authorizes code,
local simulations, deployment and read-only live checks. It does not enable recurring
spending/publication or authorize an additional paid sample. Preserve existing public
video qNsEQFHoMdk, its records, credentials and first-video resume behavior.

## Per-video lifecycle

Create a distinct durable job and working directory from its database UUID. Its
immutable input is concept/theme + target visibility (private by default). Generate a
fresh brief with English source metadata, all six localized title/description pairs
(en/fr/es/it/ru/zh-CN) and two English continuity prompts. Include recent concepts to
discourage repetition; reject an exact normalized concept duplicate without a paid retry.

Reuse bounded model quotes, ledger reservations, recorded paid-request intent and
remote generation IDs. Honor actual configured budgets: the legacy first-video 1 USD
override must never apply to the reusable workflow. Do not automatically retry an
uncertain paid chat/video POST. Resume GET polling/download for known remote IDs.

Large inline-video review requests have a bounded 120-second connect/send socket
budget, preserving the configured read deadline. Requests uses the same socket
timeout while sending a body; the former ten-second limit interrupted a 4.8 MB request.
Catalogue, text-only and small video/URL requests keep their existing timeouts.
This transport correction never retries an uncertain paid intent or releases its hold.

Render the 15.8s portrait profile with planned action-matched synthesized effects
and practical review. Existing balanced_audio_v2 jobs retain their original music.
See DISCOVERY_AND_SOUND_CONTRACT.md for the v3 sound and relevant-hashtag policy.
Only technical pass + accepted practical review permit upload. Minor visible findings
can pass; important visible defects route to local editing, uncertainty to owner review.
No automatic paid regeneration. Preserve approved media/result across a restart.

Bind upload to the approved Video and QualityCheck, its hash, job and configured channel.
Reuse resumable transfer with encrypted session state scoped by job, never the old
first-video key or asset. Upload privately with the job's six translations and explicit
AI disclosure; verify processing and exact localized metadata. If public was requested,
perform a separate explicit public-status update only with configured publishing
authorization and account approval. Never publish on a GET/status request.

## Protected API and dispatch

- POST /api/production/jobs: strict concept + visibility, Idempotency-Key required.
  Persist only; no provider call. Return 201 on creation, 200 replay, 409 changed input.
- GET /api/production/status: implemented components, current gates, configured times,
  languages and authorization blockers; never starts a task.
- Existing /api/jobs/{id} reports durable state/reason. Production execution belongs
  to the bounded worker/CLI, not the API web process.

Use a PostgreSQL advisory lock to serialize complete workflows on the 1 GB VPS, plus
durable per-job states. Recover interrupted jobs from saved intents/IDs. Failures and
budget stops create deduplicated dashboard alerts. Authorized pending processing may
be polled later; uncertain paid submissions require owner attention. No deletion/requeue
of state to repeat an uncertain provider write.

Optional two daily local times are configuration, empty until selected. Scheduler
must remain off now. When later authorized, enqueue due slots idempotently by local
date/slot, honor timezone, avoid dispatching future jobs and expire stale scan messages.
No operator-approved first sample may be selected as a new production input.

## Verification scope

Run actual caller/HTTP/PostgreSQL/FFmpeg against existing local OpenRouter/YouTube
stand-ins. Verify two distinct jobs and metadata, complete accepted/minor paths,
quality stops, budget gates, changed price, ambiguous paid submissions, interrupted
generation/upload/public response, processing delay and concurrent/restarted dispatch.
Prove repeated execution does not repeat paid submissions or create duplicate uploads.
Keep old regressions and first-video/publication behavior intact.

Deploy disabled and benchmark a synthetic full render through the worker's memory
profile on the VPS. No new real AI/publication call without a concrete authorized cap.
Durable OAuth, off-host recovery and outbound alert delivery remain separately visible
readiness conditions; code/simulation success alone does not claim unattended readiness.
