# Decision log

| Date | Decision | Reason / review trigger |
|---|---|---|
| 2026-11-05 | Complete the same private trial after explicit consent for two extra diagnostic/review calls | Total cost plus retained holds is 0.940908 USD under 1 USD; no clip regeneration or public post |
| 2026-11-05 | Use compact native Gemini schemas and the verified standard AI Studio endpoint, preserving full local validation | Generic INVALID_ARGUMENT did not isolate a cause; this corrected request scored 91 live; 123 regressions pass |
| 2026-11-05 | Keep failed review reservations and no automatic paid retries | Unknown costs remain held even though account aggregate currently agrees with successful calls |
| 2026-11-05 | Implement and simulate reusable per-job production; deploy with all recurring gates off | Owner authorized implementation; no new paid trial or recurring budget was inferred |
| 2026-11-05 | Keep paid intents under row locks and reconcile known remote IDs | Prevent duplicate paid operations even if the outer advisory-lock connection is lost |
| 2026-11-05 | Prepare a private one-job trial with maximum 1 USD additional spend | Concrete next validation, requiring explicit owner budget authorization; no global/account approval change |
| 2026-11-05 | Increase future prefork worker cap from 384 to 512 MiB | Actual isolated Celery synthetic render reached the 384 MiB cap; keep concurrency one and test the larger cap |
| 2026-11-05 | Owner personally granted edit consent; publish the authorized existing video through the API | Six localizations and public visibility verified live, with no new upload or AI charge; scheduler remains off |
| 2026-11-05 | Publish the existing video in six languages; English default, fr/es/it/ru/zh-CN | Owner authorized the proposed next step and added Russian/Mandarin; simplified Chinese is a verified YouTube language code |
| 2026-11-05 | Verify translated metadata before a separate public-status update | Preserve mutable fields under Google's part replacement rules and prevent public visibility before translations are confirmed |
| 2026-11-05 | Request edit consent incrementally and preserve failed reconnect grants | videos.update needs youtube.force-ssl; original upload/readonly grant stays valid; owner personally grants account permissions |
| 2026-11-05 | One-video publication authority only; global flags and scheduler stay off | Latest instruction authorizes this publication, without a recurring budget or scheduled production |
| 2026-11-04 | Python/FastAPI/PostgreSQL/Redis/Celery/FFmpeg/Compose | Requested stack; modular adapters; no orchestration SaaS |
| 2026-11-04 | OpenRouter async video API is the primary generation route | Current primary documentation and live catalogue verified |
| 2026-11-04 | No video default before a three-family paid benchmark | Vendor claims cannot establish brand-specific physics/quality |
| 2026-11-04 | Model-aware clip plans, 15/16/20-sec candidates | Routed duration limits differ; no invented 18-sec parameter |
| 2026-11-04 | Zero configured budget; propose $50 pilot, $12/day/$300 month | Explicit spending authorization is absent |
| 2026-11-04 | TikTok blocked for unattended private uploader | Official intended-use and consent requirements conflict |
| 2026-11-04 | Instagram Login provisionally preferred; no personal Page changes | Account separation requirement; direct docs partly unavailable |
| 2026-11-04 | YouTube quotas follow current documentation, recheck console | Older 1600-unit/private-only guidance differs from current reference |
| 2026-11-04 | DB jobs and leases; broker is transport only | Redis/Celery delivery alone cannot prevent lost work |
| 2026-11-04 | Serialize financial reservations and hold uncertain costs | Concurrent tasks/restarts must not overspend |
| 2026-11-04 | Runtime secrets excluded from Git | Owner retains control; store only account secret references |
| 2026-11-04 | Native 1080p preferred; no invisible quality claims for upscales | Benchmark cost/acceptance may justify changing policy later |
| 2026-11-04 | PostgreSQL 15 available locally; target Compose PostgreSQL 17 | Test local real DB now; validate target deployment separately |
| 2026-11-04 | Launch YouTube only; Instagram/TikTok paused | Latest explicit owner scope; two originals → two publications/day |
| 2026-11-04 | Use TechnoInno with admin.technoinno@gmail.com | Owner-provided destination; verify channel ID before OAuth/upload; no channel rename authorized |
| 2026-11-04 | Hostinger target https://technoinno.live | Owner-provided domain; inspect VPS/access/existing services before choosing deployment route |
| 2026-11-04 | Reuse credentials already stored in local .env | Presence checked without printing values; OAuth ID format recognized, authentication not tested |
| 2026-11-04 | Use studio.technoinno.live for the studio | Main domain pointed elsewhere; owner added subdomain DNS and resolution to 203.161.61.3 was verified |
| 2026-11-04 | Bind Google grant to UC8DbuevZRxVTWxltG9oDFRw | Public @techno-inno page resolved this ID; authorized channel result must match before saving credentials |
| 2026-11-04 | Add owner sessions, CSRF, state/PKCE and encrypted Google grants | Owner must perform consent; session/code replay and wrong-channel grants must fail safely |
| 2026-11-04 | Keep worker and scheduler off during VPS onboarding | One CPU/about 1 GB RAM; use a single worker when production is later enabled |
| 2026-11-04 | Await explicit approval of VPS package/service changes | Automatic approval review rejected the root-level bootstrap; no packages/services were installed |
| 2026-11-04 | Use local HTTP Postman simulation for Google tests | Proxy certificates lack AKI required by Python 3.13 strict X.509 checks; production HTTPS verification is unchanged |

| 2026-11-04 | Owner requests lower-cost models with sufficient quality | Supersedes the expensive initial shortlist and $50 pilot proposal; budget remains zero |
| 2026-11-04 | Provisional creative Gemma 4 26B A4B, quality Gemini 3.1 Flash Lite, video Veo 3.1 Lite | Direct current OpenRouter catalogues checked; none is yet validated on brand content |
| 2026-11-04 | Primary native-1080p plan: two silent 8-second Veo Lite clips | 0.80 USD generation per 16-second attempt; compare 720p alternatives before final default |
| 2026-11-04 | Exclude Seedance 1.5 Pro despite low price | Official model page announces retirement on 2026-11-11; avoid a new dependency near removal |
| 2026-11-04 | No automatic premium fallback or cheaper quality threshold | Preserve 80/100 and technical vetoes; choose by observed cost per accepted video |
