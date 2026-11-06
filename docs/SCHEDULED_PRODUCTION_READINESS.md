# Scheduled production readiness — 2026-11-05

Reusable workflow implemented, simulated and deployed. Unattended activation is still
pending live validation and operational preparation. Scheduling, global spending and
publication stay disabled, with zero daily/monthly caps. The earlier readiness audit
is preserved in evidence/scheduled-production-readiness-2026-11-05.json.

## Completed after the owner's implementation authorization

- Durable per-job generation, distinct media/concepts and six-language metadata
  (en/fr/es/it/ru/zh-CN), short dissolve and practical quality decisions. New jobs use
  action-matched synthesized effects and relevant hashtags; legacy jobs retain music.
- Actual configured budgets, fresh price checks and paid-intent row locks. Unknown
  paid outcomes stop for review; known remote IDs resume without new submissions.
- Approved per-job media upload, encrypted resumable state, processing/translation
  verification, and a separate explicitly authorized public update. Private is default.
- Timezone-aware two-slot scheduling, disabled and without default times. Dispatch
  requires budgets, authorization, live validation and confirmed durable Google access.
- 119 regressions passed, including 21 reusable-workflow tests against local HTTP
  OpenRouter/YouTube stand-ins and PostgreSQL. Two different synthetic jobs completed;
  repeats made no additional paid POSTs or uploads. Fourteen legacy OpenRouter scenarios
  passed after the shared runner changes. These do not establish live model quality.
- Installed API passed 37 runtime checks. Synthetic rendering through an actual isolated
  Celery prefork task is checked separately on the VPS, without paid provider calls or
  uploads. The future single worker has a 512 MiB cap after the 384 MiB probe reached
  its limit. API, PostgreSQL and Redis remain the only persistent services.

The existing real public video qNsEQFHoMdk is preserved. Read-only live checks confirm
two Publications; after the new trial there are four generations, twelve usage records
and 1.601434 USD cumulative confirmed AI cost.
Its six localized title/description pairs still match. The original rejected generation
job is unchanged. Legacy reservations (0.06 USD total) and the new trial review holds (0.14 USD) remain held.

## Required before unattended activation

1. Private trial completed with supervised recovery: G9wNpynDbPY processed in HD on
   the expected channel, all six exact localized readbacks match, practical review 91/100
   accepted one minor finding and coherent audio. Confirmed cost 0.800908 USD plus 0.14
   USD held remains under the separately authorized 1 USD cap. Two additional calls were
   explicitly authorized and used after the approval block. No clips were regenerated.
   The verified compact-schema/standard-endpoint correction passes 123 regressions;
   app criteria remain strict. The owner should view the result before enabling the
   live-validation confirmation. Recovery required supervision; do not call it proof of
   every unattended failure path. Do not run another trial without new authorization.
2. Verify the Google app's current audience/publishing status and obtain a durable grant
   if necessary. The console was last known as Testing and has not been inspected here.
   Google documents seven-day refresh-token expiry for external Testing apps using these
   scopes: https://developers.google.com/identity/protocols/oauth2#expiration.
   The working connection alone does not establish long-term unattended access.
3. Implement outbound failure delivery to an owner-authorized destination and encrypted
   off-host backups, followed by an isolated restoration test. Current alerts are stored
   in the dashboard; prepared backup instructions do not establish off-host recovery.
4. Select two daily local times (Africa/Casablanca) and explicitly authorize daily/monthly
   caps and recurring publication. Only then set the readiness confirmations and start
   worker/Beat. Implementation authorization is not recurring spending authorization.

Evidence in docs/evidence/: production-workflow-tests-2026-11-05.xml,
production-workflow-simulation-2026-11-05.json,
production-workflow-runtime-2026-11-05.json,
production-workflow-live-controls-2026-11-05.json, and the VPS rendering reports.
Contract: PRODUCTION_WORKFLOW_CONTRACT.md.

Resource validation: the actual isolated Celery prefork task rendered and inspected
1080x1920 video plus AAC review successfully; peak 394.95 MiB under a 512 MiB cap,
with no memory-limit hits or OOM events. Temporary worker removed; only API/PostgreSQL/
Redis remain. Synthetic media only, no provider charge or upload. Evidence:
docs/evidence/production-workflow-celery-render-2026-11-05.json.

Final installation of the compatibility correction is verified: 123 regressions,
37 installed runtime checks, matching source hashes, and matching API/future-worker
image tags. Only API/PostgreSQL/Redis run. Local mocks and disposable PostgreSQL stopped.
Evidence: production-private-review-fix-release-2026-11-05.json and
production-private-trial-fix-runtime-2026-11-05.json in docs/evidence/.
