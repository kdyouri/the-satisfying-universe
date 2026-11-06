# Implementation plan

## Current milestone — reusable workflow installed, 2026-11-05

Per-job production through six-language publication is implemented and deployed disabled.
119 regressions (21 new workflow tests), 14 legacy provider scenarios and 37 installed
runtime checks pass. Scheduling now supports two explicit local times; none are selected.
A private live trial is prepared with a 1.00 USD additional-spend cap, pending explicit
owner authorization. Then verify durable Google access, off-host restore and outbound
alerts, and agree times/recurring caps before enabling worker/Beat. Details and limits:
docs/SCHEDULED_PRODUCTION_READINESS.md. The milestones below are historical plans.

## Earlier milestone — 2026-11-05

Supervised generation, music/dissolve defaults and the first private API upload are
complete. The owner has now authorized localizing that existing video in six languages
(English default, French, Spanish, Italian, Russian, Mandarin/simplified Chinese) and
making it public, while leaving scheduled production off. Implementation is deployed:
98 regression tests, ten OAuth HTTP scenarios and 34 installed runtime checks pass.
The owner subsequently completed personal edit consent; the fixed-video publication
API succeeded. Exact six-language readbacks/public visibility and unauthenticated
public metadata access are verified. No media was reuploaded. This one-video
authorization does not enable recurring publishing/spending. See MANUAL_TASKS.md and
docs/YOUTUBE_MULTILINGUAL_CONTRACT.md. Older planning below is historical where it conflicts.

## Current scope — owner update, 2026-11-04

YouTube-only initial launch: TechnoInno, Google account admin.technoinno@gmail.com,
Hostinger target https://technoinno.live. Instagram and TikTok are paused. Two original
videos/day now means two YouTube publications/day. Original cross-platform milestones
below are superseded by this scope wherever they conflict.

OpenRouter key and YouTube client ID/secret are present in local `.env`; the client ID
matches Google's OAuth ID format. Owner confirmed the Web application client type.
The owner-login/OAuth feature is deployed on the HTTPS studio. Real owner consent,
TechnoInno channel UC8DbuevZRxVTWxltG9oDFRw, encrypted credentials, live token refresh
and channels.list access are verified. Root SSH is working at 203.161.61.3 and
studio.technoinno.live DNS/certificate setup is complete. The Google test-user block
is resolved. Next: generation/quality adapters, exact provider quotes and durable
resumable YouTube upload/reconciliation. Testing-mode grant lifetime must be addressed
before unattended operation. See docs/YOUTUBE_LAUNCH.md. Do not request known details
or secrets again. Paid runs and any test upload remain separately authorized.

## M0 — feasibility and architecture (this session)

Research primary sources; save live capability evidence; model/cost comparison;
identify approval conflicts; document architecture, owner steps and decisions.
Exit: evidence and unresolved facts explicit; no invented approval guarantees.

## M1 — durable, cost-safe foundation (this session)

Implement project/configuration, initial database migration, protected FastAPI
contract, read-only admin shell, durable job queue and preflight worker, idempotent
job creation, lease recovery, financial reservations and immutable settlement.
Define validated brief/quality/provider contracts. Add Docker Compose scaffolding,
test setup, dependency lock, and operations guidance. No paid/provider calls.
Exit: local tests pass; migration and concurrency verified where environment allows;
untested Compose deployment clearly identified.

## M2 — brand and authenticated model discovery

Use the owner-provided Google identity and TechnoInno channel. Confirm the channel URL/ID;
prepare bios and final visual assets, obtain owner-authorized app credentials securely.
Add read-only model discovery with freshness, exact parameter/SKU quotes and provider
origin validation. Implement structured creative and multimodal review adapters.
Exit: configured account identity checked; API limits and spend authorization recorded.

## M3 — low-cost authorized benchmark and production loop

Owner explicitly prioritizes lower cost with sufficient quality. Provisional defaults:
Gemma 4 26B A4B for creative text, Gemini 3.1 Flash Lite for video review, Veo 3.1 Lite
for native-1080p generation. Compare three concepts across Lite 1080p, Lite 720p and
Grok Imagine Video 1.5 Lite 720p. Nine versions cost 5.19 USD generation-only at the
checked catalogue prices; a proposed 10 USD pilot replaces the old 50 USD proposal.
No spending is authorized and no pipeline implementation/quality result is implied.

Record model/resolution/duration/audio, actual cost, latency, joins and quality results.
Keep score >=80 and all severe/technical vetoes. Select by cost per accepted original;
no automatic premium fallback. Revalidate rates and model availability before submission.
Implement download, S3, FFprobe/decode, FFmpeg, quarantine and two-attempt cap.
Exit: reviewed examples pass and owner authorizes the concrete paid test; benchmark
results are evidence, not model-page marketing. See COST_ESTIMATE.md for calculations.

## M4 — OAuth and independent publishers

Configure YouTube owner login, encrypted tokens and expiry alerts;
private/draft end-to-end tests, processing polls, reconciliation and no duplicate retry.
Use verified scopes/API versions. Instagram and TikTok are paused; their publishers,
OAuth setup, approval work and account-creation tasks are deferred.

## M5 — daily autonomous operations

Two timezone-aware slots/day, durable dispatcher, paid submission reconciliation,
rate-limit jitter, timeouts, provider cost reconciliation, budget-stop notifications,
HTTPS, off-host encrypted backups and restore test. Restart and broker/database failure
drills. Owner authorizes production spending and public posts only after reviewing samples.

## M6 — analytics and optimization

Metric-specific scopes and capability checks; real platform ingestion; dashboard
spend/production/errors/links; prompt performance feedback with novelty safeguards.
Never fabricate unavailable watch-time or retention metrics. Follow platform retention
and deletion requirements after verification.

See PROJECT_STATUS.md for actual completion rather than treating this plan as evidence.
