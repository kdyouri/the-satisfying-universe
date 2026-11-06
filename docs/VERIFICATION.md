# Verification record — updated 2026-11-05

## Latest reusable-workflow verification — 2026-11-05

119 tests passed against disposable PostgreSQL and local HTTP provider stand-ins,
including 21 workflow tests for distinct jobs/media/translations, retries/restarts,
paid-write ambiguity, actual budgets, duplicate prevention, practical quality routing,
private/public gating, API protection and a scoped private trial. Fourteen historical
OpenRouter HTTP scenarios also passed after shared intent-lock changes. Synthetic
responses do not prove live model quality or binary upload fidelity.

37 installed runtime checks pass. Live read-only controls preserve the original public
video, exact six-language metadata, one publication/two generations/five usage records
and 0.800526 USD confirmed AI cost. All global recurring flags are false, caps zero.
A synthetic render is also checked through real isolated Celery on the VPS; its memory
reports are recorded separately. No new AI generation or media upload was performed.
See evidence/production-workflow-*2026-11-05.* and SCHEDULED_PRODUCTION_READINESS.md.

Earlier sections below retain their historical verification scope.

## Live six-language public publication completed

- Owner personally granted the edit permission and confirmed the new studio status.
  The installed plan reported edit_consent_granted=true for the same video qNsEQFHoMdk.
- One protected publication API POST returned HTTP 200/published_public. Google confirms
  the exact channel, public visibility, English default, all six complete title/description
  translations, successful processing and no regional restriction. No media was reuploaded.
- Separate native hl=en/fr/es/it/ru/zh-CN API reads returned each exact expected localized
  title and description. An unauthenticated official YouTube oEmbed lookup returned 200,
  the English title and author TechnoInno. This establishes public metadata accessibility;
  no claim of worldwide algorithmic distribution is inferred.
- Live controls confirm one Publication, two generations, five model-usage records and
  unchanged AI cost 0.800526 USD. Published time is set, dashboard shows the public video,
  original rejected job is preserved, and scheduler/automatic-spending/publication flags
  remain false with zero caps. No account-wide automatic publication approval was enabled.
- Evidence: evidence/youtube-multilingual-consented-plan-2026-11-05.json,
  evidence/youtube-multilingual-publication-result-2026-11-05.json,
  evidence/youtube-multilingual-public-live-2026-11-05.json and
  evidence/youtube-public-access-2026-11-05.json. Existing 98 regressions, ten OAuth HTTP
  scenarios and 34 runtime checks remain the implementation evidence; only read-only
  live verification was added after actual publication.
- Final service check shows only healthy API/PostgreSQL/Redis; worker and scheduler
  remain off. The final read-only Postman status check retains the known local
  Keychain exit 139; no shared Postman workspace was changed.

The pending-consent section below records the earlier same-day preparation phase.

## Six-language publisher installed — personal edit consent pending

- 98 full regressions passed with real HTTP simulations and disposable PostgreSQL.
  Eleven publication cases cover success, two lost-write-response cases, metadata
  error/mismatch, public write rejection, wrong channel, missing edit scope, concurrency,
  geographic restriction and pending processing. Preserved category/tags/unrelated German
  translation/status flags were asserted; only two PUTs on success/recovery and no
  new media POST occurred. Strict inputs, owner auth and cookie-CSRF were checked.
- Ten real OAuth HTTP scenarios pass, including missing edit scope. Regression checks
  prove a failed/partial reconnect preserves the previous encrypted grant. New consent
  URLs retain exact callback, state and PKCE, add edit scope and incremental consent.
- Initial new mock runs exposed delayed responses referencing later reset fixture state;
  snapshotting the original response fixed that test-fixture crash. The final complete
  suite was rerun successfully. No real Google write was used to test these paths.
- Code-only deployment preserved environment/keys/media. 34 installed runtime checks
  pass, including six-language plan, protected routes, public action CSRF, requested
  edit scope, zero budgets and disabled scheduler/automatic publication. Current API
  plan identifies the existing qNsEQFHoMdk with edit_consent_granted=false. Live
  i18nLanguages verified en/fr/es/it/ru/zh-CN; edit consent and public display remain
  live checks pending owner completion. No additional AI request or upload occurred.
- The local simulation processes and disposable PostgreSQL were stopped after checks.
  Live controls confirm one publication, two generations, five usage entries and
  unchanged confirmed cost 0.800526 USD. Final Postman status still exits 139 with
  the known Keychain limitation; no shared workspace was changed.
- Evidence: evidence/youtube-multilingual-tests-2026-11-05.xml,
  evidence/google-oauth-edit-simulation-2026-11-05.json,
  evidence/youtube-multilingual-runtime-2026-11-05.json,
  evidence/youtube-multilingual-plan-2026-11-05.json and
  evidence/youtube-multilingual-before-consent-2026-11-05.json.

## First private YouTube API upload completed — 2026-11-05

- 85 regression tests passed against disposable PostgreSQL, including 14 actual HTTP
  upload tests. Cases cover strict owner authorization, private metadata, partial
  progress, interrupted transfer/completion, ambiguous initiation, revoked grants,
  wrong channel, untrusted Location, changed-file replay and concurrent execution.
- Local Postman gateway decoding changes observable binary bytes; simulation assertions
  cover ranges, declared sizes, metadata and caller state, not media checksums.
  The real private upload and Google's successful processing provide end-to-end proof.
- Code-only deployment preserved credentials and data; 27 installed runtime checks
  passed before transfer. The protected plan validated the 17,247,488-byte sonorized
  file and exact channel. A single owner-requested API POST uploaded video qNsEQFHoMdk;
  subsequent read-only reconciliation confirmed private, processed/succeeded, HD and
  exact channel UC8DbuevZRxVTWxltG9oDFRw. No duplicate or public upload occurred.
- containsSyntheticMedia=true was sent with private status and no notifications;
  Google does not echo that field in this readback, so its stored value remains
  unverified. The description also explicitly discloses AI-generated visuals.
- The original rejected job remains rejected; the edited video records only the
  explicit private-test authorization. Session reference is encrypted; the dashboard
  links to the private video. Counts are two generations, one publication, five model
  usage records; confirmed AI cost stays 0.800526 USD. Scheduler/public/automatic-spend
  controls remain false, caps zero, account automatic publication approval false.
- Local simulation and disposable PostgreSQL were stopped after verification. Only
  healthy API, PostgreSQL and Redis run on the VPS. The final read-only Postman status
  check still exits 139 with the previously observed local Keychain limitation; local
  simulations ran successfully, and no shared Postman workspace was changed.
- Evidence: evidence/youtube-private-upload-plan-2026-11-05.json,
  evidence/youtube-private-upload-result-2026-11-05.json,
  evidence/youtube-private-upload-verified-2026-11-05.json,
  evidence/youtube-private-upload-live-2026-11-05.json,
  evidence/youtube-upload-runtime-2026-11-05.json and
  evidence/youtube-upload-tests-2026-11-05.xml.

Earlier sections retain their original phase's scope and counts.

## Audio and practical review profile deployed — 2026-11-05

- 71 regression tests passed and 14 actual HTTP simulation scenarios passed with the
  final staged renderer, PostgreSQL and synthetic provider responses. Minor findings
  were accepted; visible major issues routed to local editing; uncertain, low-score and
  unobservable-audio cases routed to manual review, without additional generation POSTs.
- Final and review video bytes contain AAC audio. Missing music stops before provider
  access; absent or silent soundtrack fails technical validation. Source audio requests
  remain disabled; music is composed locally from oscillators and bundled with provenance.
- 27 installed runtime checks passed after final deployment. Protected capabilities
  expose balanced_audio_v2; the installed production module hash matches local source.
  Global spending/publishing/scheduler flags remain false and caps remain zero.
- Real clips rendered to 15.8s, 1080x1920/H.264/30fps/AAC with a 0.2s dissolve, in a
  384 MiB VPS process. Whole-file decoding and audible-volume checks passed; mean/peak
  were -25.9/-15.0 dB. The first one-pass attempt exposed FFmpeg 7 CFR metadata loss;
  normalizing after setpts resolved it, then staging the overlap separately resolved
  the observed SIGKILL under the memory cap. Local tests and simulation were rerun.
- Confirmed cost remains 0.800526 USD; there are still two generations, five usage
  records and zero publications. Legacy resume with a provider object lacking API
  methods returns the existing rejected result, proving no provider call on that path.
- The new preview has no new paid AI review and does not retroactively approve the
  original. Next live model/schema judgment remains to be checked on a future authorized
  manual trial. Local Postman and PostgreSQL test processes were stopped.
- Evidence: evidence/audio-profile-live-2026-11-05.json,
  evidence/audio-profile-runtime-2026-11-05.json,
  evidence/audio-preview-vps-2026-11-05.json and
  evidence/openrouter-simulation-audio-2026-11-05.json.

The earlier audio phase produced one supervised AI video; no social publishing occurred then.
Google consent and live token refresh passed in an earlier phase. Historical sections
below retain the scope of the checks made at that time.

## First supervised video

- Two real Veo 3.1 Lite clips completed and were downloaded from the fixed authenticated
  OpenRouter content endpoint. The second used a frame from the first. No paid video
  POST was repeated; known IDs were polled again on resume.
- Native master: 1080x1920, H.264/yuv420p, 30 fps, exactly 16 seconds, silent MP4.
  Complete FFmpeg decoding passed on the VPS and locally; SHA-256 copies match.
- Gemini Flash Lite reviewed the entire 540x960 review copy: score 82, severe-defect
  veto, rejected. Reported defects concern the join, liquid motion and spiral instability.
  A passing score alone does not override the veto. No upload was created.
- Confirmed cost and key usage both 0.800526 USD. Original refused-request reservations
  total 0.06 USD and remain held. Global caps zero; all recurring/publishing flags off.
- Nine HTTP simulation scenarios passed with synthetic responses, actual caller,
  PostgreSQL ledger and FFmpeg. The resized-review path was rechecked against this
  simulation. 52 full regression tests then passed; two focused operator-brief tests
  passed after the final unused-model price-check adjustment. Ruff passed.
- The initial simulation schema could not be used for Alembic regressions because it
  had been created directly; a separate clean migrated test database resolved that setup
  issue. A real creative request returned 429; no retry was made. An explicit operator
  brief supplied prompts. The oversized master review returned 413; a bounded review
  copy resolved request size. An unused creative-model price change was not permitted
  to block the review-only resume. Failed requests were not silently marked settled.
- Evidence: evidence/first-video-live-2026-11-04.json and
  evidence/openrouter-simulation-2026-11-04.json. The video is retained as an unapproved
  first sample. It does not establish autonomous production or publication readiness.
- All 27 installed runtime checks passed after deploying the final code, including
  authentication, database readiness, zero caps and disabled scheduler/publishing:
  evidence/first-video-final-runtime-2026-11-04.json. Local Postman/PostgreSQL test
  processes stopped. Exited pilot containers removed without deleting media/records.

## Lower-cost model configuration

- Retrieved current public OpenRouter catalogues without credentials/charges: 31 video
  and 454 total models. Selected model capabilities, structured-output/video-input support,
  expiry fields and exact video SKUs were checked against saved responses.
- Verified all cost arithmetic with Decimal, including cents-to-USD and 16-second clip
  construction. Documented the retiring/incompatible low-price models and 1080p upscale caveat.
- Configured three model IDs in the local/prepared environments and live VPS, preserving
  other environment values and private file permissions. Helper now retains these IDs
  in future release preparation; its Ruff check passed.
- Live configuration verification passed: database ready, YouTube connected, all spending,
  publishing/scheduling controls off and zero budget caps. No generation or model-quality
  benchmark was run; these choices remain provisional until observed brand-content review.
- Evidence: evidence/low-cost-model-selection-2026-11-04.json and
  evidence/low-cost-vps-verification-2026-11-04.json, plus the two saved public catalogues.

## Real owner Google connection follow-up

- Owner completed consent and reported Connected: @techno-inno.
- Saved channel ID matches UC8DbuevZRxVTWxltG9oDFRw. Encrypted credential decryption,
  required scopes and refresh-token presence passed; no secret values were printed.
- A real Google token refresh and authorized channels.list(mine=true) call succeeded;
  refreshed credentials were re-encrypted and saved without overwriting a concurrent grant.
- No upload, paid request or scheduler run occurred. Spending/publication remain disabled.
- Evidence: evidence/youtube-live-connection-2026-11-04.json. Long-term expiry/revocation,
  Google Testing-mode restrictions and upload processing remain separate concerns.

## Browser login regression follow-up

- Replaced the general no-referrer policy with strict-origin so native browser forms
  preserve their genuine HTTPS Origin. Callback responses retain no-referrer.
- 26 focused API/OAuth tests passed; one unrelated PostgreSQL test deselected. Added
  policy coverage and explicit rejection of null and foreign origins on login and
  authenticated forms. Ruff passed. Previous full-suite evidence remains historical.
- 27 installed runtime checks passed with the actual owner password, including the
  new login and callback referrer-policy checks; no Google calls, jobs or uploads.
- Native browser submission with an intentionally wrong password now renders the
  normal password error. Earlier raw HTTP checks did not exercise browser generation
  of the Origin header. Real Google consent remains a separate owner action.

## Installed VPS and HTTPS

- Owner authorized installation and personally accepted the current certificate
  agreement. Docker 29.9.3/Compose 5.7.0, Nginx and Certbot installed successfully.
- Both application images built; PostgreSQL 17 migrated to 7d920bb1c441 with 16
  application tables. API, PostgreSQL and Redis are healthy; worker/Beat stay off.
- **25 runtime checks passed on the VPS and again over external HTTPS**, including
  actual owner login, protected routes, CSRF, session revocation, database readiness,
  zero caps/disabled spending and publishing, scheduler off, exact Google redirect/PKCE.
  No Google endpoint was contacted by these runtime checks; test sessions/flows removed.
- Authoritative, Google, Cloudflare and ordinary local DNS queries resolve studio to
  203.161.61.3. This Mac's system HTTP resolver still caches an earlier negative answer;
  external TLS checks used the verified IP with the original domain/SNI and normal
  certificate validation enabled. No TLS verification was disabled.
- Certificate issued for studio.technoinno.live, expiring 2027-02-02. HTTPS health/login
  pass; HTTP redirects to HTTPS. Security headers observed. Nginx syntax passes cleanly.
- Certbot timer and Nginx reload hook enabled; renewal dry run with deploy-hook passed.
- API 8000/PostgreSQL 5432/Redis 6379 are unreachable from outside. Server .env mode
  0600 and deployment directory 0700. Owner access is private in .runtime/OWNER_ACCESS.txt.
- Evidence: vps-runtime-check-2026-11-04.json, vps-https-check-2026-11-04.json,
  vps-port-check-2026-11-04.json and vps-install-2026-11-04.json in docs/evidence/.

## Earlier local owner-login and YouTube OAuth follow-up

- **48 tests passed**, including real local PostgreSQL. Coverage includes browser
  sessions/CSRF, expiry/password-rotation revocation, state/PKCE, same-browser binding,
  wrong-channel/denied/expired grants, replay and concurrent callbacks, encrypted token
  storage, and preservation of a prior connection when reconnect fails.
- **9 HTTP simulations passed** using the actual Google client with synthetic credentials
  and loopback Postman stand-ins. Verified form fields/PKCE, channel parameters, success
  and eight failure modes, and that failures did not save a usable credential.
  Request events were inspected; results: evidence/google-oauth-simulation-2026-11-04.json.
- OAuth migration 7d920bb1c441 rolled back and reapplied; Alembic reported no drift.
  Ruff, compilation, dependency check, bootstrap shell syntax and Compose source checks
  passed. Container runtime/Nginx verification was then pending; it now passes above.
- Postman's proxy certificate lacked an Authority Key Identifier and was rejected by
  Python 3.13 before any request ran. Switched to loopback HTTP simulation; production
  TLS verification is unchanged. The simulation does not establish live Google consent.
- Read-only SSH/DNS verified the server and subdomain; the public channel page supplied
  its unique ID. Real Google authorization and token-refresh lifecycle remain unverified.
- Automatic approval review initially rejected VPS changes before execution. The owner's
  later explicit install instruction resolved that block; installation is complete above.

## Earlier foundation checks

| Check | Result | Scope |
|---|---|---|
| Full pytest suite | 36 passed, 1 upstream deprecation warning | Real PostgreSQL 15 + local API/contract/media tests |
| Concurrent budget reservations | Passed | 10 simultaneous $1 reservations under $5 cap: exactly five accepted |
| Concurrent duplicate reservation | Passed | Same operation returns one ledger record |
| Budget-stop alerts | Passed | Concurrent alerts persist as one deduplicated row |
| Unknown prior-period costs | Passed | Outstanding reservations remain held after day/month rollover |
| Overrun and settlement | Passed | Actual overrun freezes new spending; settlement cannot be changed |
| Job retry/recovery | Passed | Durable row survives new app instance; stale lease cannot complete newer work |
| Duplicate job requests | Passed | Same input replays; changed body conflicts; concurrent creation yields one job |
| API protection and contract | Passed | Protected paths reject missing/bad auth; OpenAPI snapshot matches |
| Quality contract | Passed | Technical/severe defects veto high scores; threshold boundary enforced |
| Capability constraints | Passed | Wan's unsupported 15-second/480p requests rejected from saved live data |
| Technical video inspection | Passed | Full synthetic 16-sec 1080×1920 master decodes; wrong-format/corrupt files rejected |
| Schema migration round trip | Passed | Upgrade, downgrade, upgrade; guard seed restored |
| Alembic drift check | Passed | No new upgrade operations detected |
| Backup/restore smoke | Passed | Separate local disposable database; all 13 table counts/revision match |
| Source checks | Passed | Ruff lint, formatting, Python compilation and dependency consistency |
| Compose source parse | Passed | Six service definitions; only API loopback port; no DB/Redis host ports |
| Docker image / Compose runtime | Not tested | Docker unavailable |
| Celery broker transport | Not tested | Redis service unavailable; scanner logic tested directly on PostgreSQL |
| Paid model benchmark | Not run | Explicit spending authorization and secure credentials required |
| OAuth/uploads/metrics | Not run | Dedicated accounts, permissions and verified platform access required |

Temporary PostgreSQL used a local Unix socket with no TCP listener. Its data and a
test backup are in the ignored `.runtime/` directory. The test database contains no
real videos, accounts or credentials. It is stopped after the session.

The Starlette TestClient warning advises migration from its deprecated httpx
integration; it does not represent a failed assertion. Postman status separately
fails with a macOS Keychain error, so no Postman workspace checks are claimed.

Resource validation: the actual isolated Celery prefork task rendered and inspected
1080x1920 video plus AAC review successfully; peak 394.95 MiB under a 512 MiB cap,
with no memory-limit hits or OOM events. Temporary worker removed; only API/PostgreSQL/
Redis remain. Synthetic media only, no provider charge or upload. Evidence:
docs/evidence/production-workflow-celery-render-2026-11-05.json.

Final CLI status check: Postman exited 0 but is signed out. Earlier Keychain errors
are historical; no signed-in workspace validation or publication is claimed. Local
simulations, source lint and installed application checks are the recorded evidence.

## Subsequent authorized private live trial — incomplete quality stage

The owner authorized 1 USD maximum. Real creative + two video generations cost
0.800132 USD; the 15.8s final passes complete decode, 1080x1920/30fps and audible AAC
checks (mean -25.9 dB, peak -15.0 dB). Server/local SHA-256 matches. Six-language text
was generated but has not been uploaded or read back from Google. No new publication.
Original review: connection failure; one separate supervised review: HTTP 400. Both
0.05 USD reservations remain held. A further diagnostic request was rejected by automatic
approval, so no diagnostic POST occurred. This does not prove live quality acceptance,
private upload or an unattended cycle. App source is unchanged from the 119-test release;
new operator helpers passed lint and the media/budget dry-run checks. The prepared
successful-trial verifier has NOT run successfully. Additional explicit consent is pending.

## Final private-trial recovery and compatibility correction

Owner explicitly authorized at most two further calls, still under the 1 USD total.
The diagnostic returned generic Google AI Studio INVALID_ARGUMENT; the corrected
compact-schema/standard-endpoint call scored 91 with coherent audio and one tolerated
minor finding. Cause was not isolated between schema complexity and endpoint selection.
All original reservations/intents remain; no regeneration occurred. Confirmed cost
0.800908 USD plus held 0.14 USD is within cap. Google verifies private processed HD
video G9wNpynDbPY and six exact native localized readbacks. Original public video and
rejected original job are preserved. The full corrected app suite passes 123 tests;
full local validation remains in force and unknown POSTs still stop without retry.
Earlier incomplete-stage notes above are superseded by the final evidence.

Final installation of the compatibility correction is verified: 123 regressions,
37 installed runtime checks, matching source hashes, and matching API/future-worker
image tags. Only API/PostgreSQL/Redis run. Local mocks and disposable PostgreSQL stopped.
Evidence: production-private-review-fix-release-2026-11-05.json and
production-private-trial-fix-runtime-2026-11-05.json in docs/evidence/.
