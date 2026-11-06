# Project status

Updated: 2026-11-06, Africa/Casablanca.

## Recurrence ACTIVATED — first scheduled video published publicly

2026-11-06 evening: all readiness blockers cleared and the recurring pipeline is live.
Alerts: SMTP via Gmail app password (owner enabled 2-Step Verification), 3 test alerts
delivered and receipt confirmed, OUTBOUND_ALERTS_CONFIRMED=true. Google grant: the
owner switched the app to Production and reconnected via the studio; the refresh token
now reports no 7-day expiry. Off-host backup: Cloudflare R2 (bucket technoinno-backup,
rclone 1.76 with no_check_bucket), daily 51 KB age-encrypted DB+recovery bundle plus
incremental crypt media sync (56 objects, 136.5 MiB), weekly full bundle, retention
7 daily / 4 weekly, cron 04:30 Africa/Casablanca, failure alerts wired to the email
pipeline. The restore drill from R2 passed end to end: decrypt, 56/56 media hashes,
isolated PostgreSQL 17 restore with exact counts, and grant decryption with the
recovered key. OFFHOST_BACKUP_CONFIRMED=true.

A budget deadlock was diagnosed and resolved with owner authorization: nine standing
reservations (3.427680 USD) counted against the 2.00 USD daily cap; the OpenRouter
account usage (3.043405026) equals the settled sum (3.043409) within display rounding,
proving the held calls were never billed, so the holds were settled at zero with that
arithmetic evidence recorded per row.

Scheduler, worker and Beat are running (12:00 and 20:00 slots, public publication,
account approval granted). Two deployment traps were fixed en route: the worker
container had been running an outdated image and was rebuilt to current source; the
first 20:00 slot job had been created with the superseded v4 profile by that stale
worker and was migrated to native_audio_v5 before any paid call.

The first scheduled video (Sage Matcha Oil Droplet, 93/100, 0.640656 USD) stopped at
manual_review because the review judged its native audio effectively absent (mean
-47.0 dB); the owner accepted it and it published publicly as
https://www.youtube.com/watch?v=5KrRDyHQyU0 (HD, six verified languages, job
published). Steady-state expectation: ~1.30 USD/day within the 2.00/45.00 caps;
manual_review videos stop with an email alert instead of publishing. Evidence:
docs/evidence/recurrence-alerts-grant-2026-11-06.json and
recurrence-activated-first-video-2026-11-06.json.

## Recurrence prepared — superseded by the activation above

The owner's recurring decisions are applied on the VPS: automatic public publication,
two daily slots at 12:00 and 20:00 (Africa/Casablanca), 2.00 USD daily and 45.00 USD
monthly caps, spending and publication authorized, and PRODUCTION_LIVE_VALIDATED=true
justified by the completed, owner-reviewed v3 cycle. The scheduler flag, worker/Beat
and the account publication approval stay off until the remaining readiness blockers
are real: outbound alert delivery (Gmail app passwords require enabling 2-Step
Verification first — the owner saw the setting unavailable) and an always-available
automatic off-host backup destination (owner chose "later"; the one-time encrypted
backup/restore drill already passed). The Google OAuth app also remains in Testing
mode, where refresh tokens expire after 7 days; moving it to Production is a personal
Console action. Only when all are done will the scheduler, worker and Beat start.
Evidence: docs/evidence/recurrence-preparation-2026-11-06.json. No paid call or upload
occurred during this preparation.

## Latest result — first complete native-audio cycle, private on YouTube

2026-11-06: after a free quality/price comparison of the 19 native-audio catalogue
models, the owner selected `google/veo-3.1-lite` native audio (the only candidate with
measured in-house quality: 82/100 and 91/100 on earlier trials; 0.08 USD/s, 0.64 USD
per 8-second generation) with a 1.00 USD cap. Trial
`owner:native-audio-private-trial:v3` ran end to end in one supervised cycle: creative
brief 0.000149 USD (new concept: liquid chrome sphere on obsidian), ONE 8-second
1080p 9:16 generation with native AI audio settled at 0.640000 USD, technical
inspection passed (audible AAC, master byte-identical to the provider download), and
the practical review scored 97/100 with no severe defects. The review routed to
manual_review because it judged the native audio a light continuous electronic hum
lacking organic liquid textures. The owner viewed the local copy and explicitly
accepted that sound for this private test; the acceptance is recorded as an
additional owner-attributed QualityCheck bound to the job and SHA-256, with the AI
finding preserved and the original check untouched.

The video uploaded privately and reconciled: https://www.youtube.com/watch?v=3a2YvpExzac
is processed, HD, on the exact TechnoInno channel, with English default and verified
localized titles/descriptions plus hashtags for en/fr/es/it/ru/zh-CN. The job is
completed_private; nothing was published publicly. Trial cost 0.640755 USD with zero
unsettled reservations, inside the 1.00 USD cap. Global totals: 6 jobs / 9
generations / 3 publications / 25 usage records, 3.043409 USD actual and 3.427680 USD
held (the two failed native reservations remain). All recurring flags and caps stay
off/zero. Evidence: docs/evidence/native-v3-trial-authorization-2026-11-06.json and
native-v3-trial-completed-2026-11-06.json; tests docs/evidence/native-v3-veo-tests-2026-11-06.xml.

Profile change: the reusable native profile is now `native_audio_v5` (veo-3.1-lite,
8 s, 0.70 USD generation ceiling); the superseded v4 profile (gemini-omni, 15 s) is
retained for its stopped trial jobs. The terminal-error-body polling fix and the
v3 trial key are installed; image
sha256:45b5d00a1b2c3f1594f9a4e4779e393f8f567f1fca63fb1fd6394fb1120f2b70, rollback at
/opt/technoinno/deploy-backups/native-trial-v3-20261106. 182 regression tests pass
without skips. A NEW trial or recurring production still requires a fresh explicit
owner decision; recurring prerequisites (alerts, off-host backup schedule, times/caps,
durable Google status) remain outstanding.

## Previous trial — second identical native generation failure; polling defect fixed

2026-11-06: the owner authorized one fresh end-to-end native-audio trial
(`owner:native-audio-private-trial:v2`), maximum 2.00 USD, free creative subject,
private upload. Free preflight passed (catalogue supports 15 s/1080p/9:16/native
audio, quote 1.563840 USD within the 1.60 ceiling; YouTube grant refresh and exact
@techno-inno channel read passed). The creative call settled at 0.000111 USD and
produced a new concept (violet honey on white marble). Exactly one 15-second
generation was submitted to `google/gemini-omni-1.2-flash`
(gen-vid-1793975851-mTAAtfBl39jlBirQ93km). The provider later returned the terminal
body `Video generation failed` with no cost evidence. No video, review or upload
exists; the 1.563840 USD reservation is retained and the job is owner_attention.
The 2.00 USD authorization is consumed; a further attempt needs a new explicit
decision, and this model now has two identical terminal failures — do not retry it
without a new owner decision on a different candidate.

The failure also exposed and fixed a real defect: a 200 response whose JSON body
contains an `error` field was treated as transient by the polling loop, which
retried silently until the 20-minute deadline. `tsu/openrouter.py` now raises
`ProviderTerminalError` for a parsed error body (safe detail only) and the poll
loop stops immediately; paid POSTs keep their never-retry rule and unknown charges
stay reserved. 179 regression tests pass without skips, including the new
terminal-error case. Installed API image
sha256:e1835e958ce0c04e17c8e0d204a821dea4ce3615342b71624114d9deb705618a; rollback
source at /opt/technoinno/deploy-backups/native-trial-v2-20261106. Global totals:
5 jobs / 8 generations / 2 publications / 22 usage records, 2.402654 USD actual and
3.427680 USD held (the two 1.563840 USD native reservations plus earlier holds).
All recurring flags and caps remain off/zero. Evidence:
docs/evidence/native-v2-trial-authorization-2026-11-06.json and
native-v2-trial-failed-2026-11-06.json.

## Previous trial — provider failed without final cost evidence

2026-11-06: the owner authorized one private 15-second native-audio trial with a
maximum of 1.70 USD. The scope patch was deployed with a source rollback archive at
`/opt/technoinno/deploy-backups/native-trial-scope-20261106`; API image
`sha256:b3e633be7ed40f1c64c942e1f0417b0d238732b2502634af0244efbb5f47aa4f` is healthy.
The provider catalogue and the connected @techno-inno upload grant passed free
preflight. All 24 targeted local scope/native integration tests passed.

One creative call settled at 0.000098 USD. Exactly one video generation was submitted
to `google/gemini-omni-1.2-flash`, with a 1.563840 USD reservation. The provider later
reported `failed` without final cost evidence. The durable job is `owner_attention`;
the single generation record remains pending with its known provider ID and its
reservation remains held. Do not resubmit, regenerate, release that hold, run a QA
call, or upload. No video/master or publication was created. The additional
authorization for this one trial is consumed; a fresh generation requires a new
explicit budget decision after cost reconciliation.

Global totals were then 4 jobs / 7 generations / 2 publications / 20 usage records,
2.402543 USD actual and 1.863840 USD held (including earlier holds). The account-wide
spending, publishing, and scheduler flags and both budget caps remain off/zero. Only
API, PostgreSQL and Redis are running; the API is healthy. Evidence:
docs/evidence/native-audio-trial-failed-2026-11-06.json.

The earlier quota-blocked, not-started handoff below is superseded by this execution.

## Current result — native AI audio, one 15-second generation

The owner discarded the turquoise-basin test and explicitly prohibited its upload.
The VPS job is cancelled with never_publish/owner_discarded and withdrawn private
upload consent. Its 0.801011 USD actual and 0.10 USD uncertain holds remain intact;
global totals remain 2.402445 USD actual, 0.30 USD held, 2 existing publications.
No owner sound-acceptance decision or local improvement is pending for that test.

Future new jobs use native_audio_v4: one continuous 15-second 1080p generation with
synchronized native AI environmental audio, no music by default and no montage.
The publication master must remain byte-identical to the provider download. Missing
sound/technical failure stops; clear quality problems require manual review. Minor
imperfections remain tolerated at 80/100. Six languages and hashtags remain.

The selected compatible candidate was google/gemini-omni-1.2-flash, quoted at
1.563840 USD for video+audio generation. Its authorized sample failed before a video
was returned; output quality remains unknown. Full current contract and verification
references: docs/NATIVE_AUDIO_CONTRACT.md. Scheduling/global spend/publication and caps
remain off/zero. The remaining recurring-operation prerequisites in that contract are
still outstanding.

Installed and verified: 157 tests passed without skips; source/container hashes match,
API/future-worker image sha256:d25ae9c0c67639fe725ba9ab71579ce9c279d43a782831465c9fa9ac3e2f285e.
Protected admin HTML displays the new policy; browser screenshot saved. Runtime checks
confirm cancelled execution stops before any provider is created, counts/costs preserved,
public information pages available and owner access protected. Evidence:
docs/evidence/native-audio-installed-2026-11-05.json,
docs/evidence/native-audio-final-tests-2026-11-05.xml,
docs/evidence/studio-native-audio-2026-11-05.png.
Source and private config rollback snapshot are retained on the VPS under
deploy-backups/native-audio-20261105; no worker or scheduler was started.

Earlier records below are historical and do not restore discarded consent.

## Historical result — review completed before owner discarded the test

The owner explicitly authorized one final review after the transport correction,
maximum 0.05 USD within the original 1 USD trial. That distinct operation was consumed
once: HTTP 200 in 55.13 seconds, typed score 90/100, technical pass, no severe defects.
The model classified the water sound as an audio-coherence problem and recorded one
minor full-duration finding: a texture too uniform for the progressive basin filling.
The configured policy therefore returns manual_review, not approved. No upload occurred.
Do not reinterpret the 90 score as automatic approval or change the policy to force a pass.

The two clips, sound and final master are unchanged. Confirmed trial cost is 0.801011
USD, with the two prior uncertain 0.05 USD reviews still held: exposure 0.901011 USD,
below the 1 USD cap. No further AI call is authorized for this trial. Counts are
3 jobs/6 generations/2 publications/18 usage entries; cumulative actual 2.402445 USD
and 0.30 USD held. Original videos and their records remain intact.

The job is awaiting_owner_review. Its stale connection-error reason was preserved
in resolved_transport_reason and replaced by manual_review, reflecting the completed
request honestly. The native QualityCheck stays unapproved and its warning is intact.
Owner was shown the unchanged playable preview and asked to either validate this
sound for this one private test, or request local sound improvement without AI spend.
No answer has arrived yet. If accepted, preserve native findings and record a separate,
explicitly attributed owner decision bound to this private job/hash before upload.
Do not weaken future automatic quality checks or enable recurring operation.

Evidence: docs/evidence/contextual-sound-transport-fixed-owner-consent-2026-11-05.json,
contextual-sound-final-review-2026-11-05.json, and
contextual-sound-review-held-verified-2026-11-05.json.

## Current handoff — studio restored, Google production grant verified, transport fixed

The owner's reported /admin outage was a missing browser owner session. VPS/API,
Nginx, disk and memory were healthy. Unauthenticated HTML browser GET /admin now
redirects to /login; JSON/API and bad Bearer requests retain 401. Missing, invalid and
expired sessions are covered. Live HTTPS checks and a browser screenshot verify the
login form. Existing authentication/CSRF controls stay in force.

The owner personally reconnected @techno-inno after reporting Google En production.
A new callback and credential timestamp, required scopes, real refresh-token exchange
and exact channel read passed. YOUTUBE_LONG_LIVED_GRANT_CONFIRMED is now true on the
VPS and in the protected local deployment config. This is not Google verification
approval or a guarantee that access can never be revoked. Account automatic approval
stays false; all recurring spending/publication/scheduling flags and caps stay off/zero.

The expressly authorized extra contextual-sound review was attempted exactly once and
failed with ConnectionError after 10.02 seconds. Its 0.05 USD reservation remains held,
along with the original 0.05 USD uncertain review. Trial actual 0.800174 USD plus 0.10
USD held = 0.900174 USD exposure. No quality approval or new upload exists. Global
records: 3 jobs, 6 generations, 2 publications, 17 usages; actual 2.401608 USD, held 0.30 USD.

A diagnostic using the private video was rejected by automatic approval review because
that distinct transmission was not authorized; it did not execute. A safer probe used
fabricated bytes only, no real key and an invalid model. A 4.8 MB request reproduced
the write timeout at 10.27 seconds and returned expected HTTP 401 in 51.68 seconds with
a 60-second send limit. Requests retains the connect socket timeout while sending.
The adapter now grants large inline videos a bounded 120-second connect/send budget,
preserving read limits, prices, routing and the no-paid-retry rule. Small calls keep
their old deadlines. A real local slow receiver distinguishes old failure from the fix.

148 regressions pass with PostgreSQL and existing provider simulations; none skipped.
Installed hashes match, API/future-worker image is
sha256:3689bdd10549c4af590461e8dee8b30b0046a0a0467c7dbd1a31aaae3fabc511.
Only API/PostgreSQL/Redis persist. Existing public/private videos and all six localized
readbacks are preserved. Local test services are stopped. No real email was sent.

A final distinct review was expressly approved by the owner and is now running:
quality_contextual_audio_v3_supervised_transport_fixed1, reservation at most 0.05 USD,
total maximum exposure 0.950174 USD, same immutable master, no clip generation, private
upload only if approved, scheduling off. Do not reuse either consumed approval or run
owner:contextual-sound-private-trial:v1 as a new job. Prior uncertain calls/holds remain.
The fresh approval is recorded in docs/evidence/contextual-sound-transport-fixed-owner-
consent-2026-11-05.json. Do not repeat this stage if its result is uncertain. Email
setup/test, automatic off-host storage and recurring times/caps still need owner input.

Evidence in docs/evidence/: studio-login-public-verification-2026-11-05.json,
studio-login-restored-2026-11-05.png, google-production-fresh-grant-2026-11-05.json,
contextual-sound-extra-review-owner-consent-2026-11-05.json,
contextual-sound-extra-review-stopped-2026-11-05.json,
contextual-sound-free-synthetic-transport-probe-2026-11-05.json,
contextual-sound-free-synthetic-transport-longer-2026-11-05.json,
review-upload-final-tests-2026-11-05.xml, review-upload-fixed-runtime-2026-11-05.json,
review-upload-timeout-release-2026-11-05.json,
contextual-sound-transport-fixed-review-proposal-2026-11-05.json.

The sections below preserve earlier stages and are superseded where they differ.

## Latest owner approvals — public pages and one new private sound trial

After reviewing the exact texts, the owner explicitly approved publishing /about,
/privacy and /terms. PUBLIC_INFORMATION_APPROVED is now true on the VPS and in the
protected local deployment configuration. Anonymous HTTPS reads return 200 for those
pages and 401 for /admin and /api/overview. Screenshot and verification evidence:
docs/evidence/google-privacy-public-2026-11-05.png and
prelaunch-public-pages-verified-2026-11-05.json.

The owner also authorized one distinct private trial, maximum 1 USD: water stream in
a turquoise ceramic basin with synthesized water effects, six languages and hashtags.
The two clips and the 15.8-second water-effects master are generated and technically
valid. The quality call lost its provider connection; the durable job is owner_attention.
No upload occurred and no retry was made. Confirmed cost is 0.800174 USD, plus 0.05 USD
held for the uncertain review: total exposure 0.850174 USD. Preserve that intent/hold.
Do not create a duplicate or infer extra paid reviews. Previous trial permissions are
consumed. Scheduling, global
spending/publication and recurring caps remain off/zero. Approval record:
docs/evidence/prelaunch-owner-confirmations-2026-11-05.json.

The owner personally completed Google Branding/Audience and reported En production.
A fresh post-production YouTube reconnect is requested; the working old grant alone
does not confirm durable access. A separate additional quality review was proposed,
maximum 0.05 USD, preserving the original uncertain hold and all media, with total
exposure bounded at 0.900174 USD. It is prepared/dry-run only and awaits explicit approval.
No new long-lived grant is yet confirmed. Authenticated email setup/test, an automatic
off-host backup destination, and recurring times/caps remain outstanding. Earlier
sections below describe the state before these latest explicit approvals.

Local preview: generated/contextual-sound-trial/turquoise-basin-water-effects.mp4,
SHA256 4d2b9396eab125cf6b5c907e52cfeebc6a7aa3830f66c13db49824bcf74a1a4a.
The downloaded copy matches the server. Audio mean -28.1 dB, peak -7.0 dB; full decode
passes. A contact sheet shows the requested basin/stream, but is not a quality-model
approval. Free OpenRouter models/key reads return 200 after the failure; its individual
cause and any original review charge remain unknown. Evidence: contextual-sound-assets-
2026-11-05.json, contextual-sound-trial-stopped-2026-11-05.json,
contextual-sound-review-recovery-proposal-2026-11-05.json and
google-production-owner-confirmation-2026-11-05.json under docs/evidence/.

## Prelaunch operations prepared — owner decisions pending

Owner authorized proceeding with launch preparation. Alert destination is
admin.technoinno@gmail.com and the first off-host restore test may use this Mac.
A live read of Google project satisfyinguniverse under the brand account shows Testing;
Publish is disabled pending branding completion. The agent browser could not load
Branding/Clients after retry, while the owner could and reported empty homepage,
privacy, terms and logo fields. No Google setting, grant or legal acceptance was changed.

Completed: age-encrypted DB/media backup and separate encrypted recovery configuration
on this Mac. Real isolated PostgreSQL 17 restore verified 41 media files (79,467,284
bytes), schema revision, business counts, job states, remote publication IDs and Google
grant decryption with the recovered key. A tampered copy was rejected. All plaintext
temporary files and the isolated restore database were removed; production was untouched.
Private identity remains outside the backup directory. This is a one-time backup/restore,
not proof of scheduled always-available off-host replication.

Prepared and installed owner-only previews at /about, /privacy and /terms, with factual
Google data use and manual maintenance/deletion responsibilities. PUBLIC_INFORMATION_APPROVED
stays false pending owner review; these are not published legal commitments yet. Full
review text: docs/PAGES_GOOGLE_A_RELIRE.md. Logo is optional. Owner must handle final
Google publication and consent personally. No claim of Google verification approval.

Email adapter uses verified SMTP TLS, generic safe messages and a durable once-only
intent. An uncertain send is not repeated automatically. Local real-protocol TLS tests
pass; no SMTP credentials are configured and no real email was sent. A protected local
configuration template is at .runtime/email-alerts.env; test message preview is in
 docs/evidence/owner-email-test-preview.eml. Recipient preference alone did not authorize
sending. The future periodic task is installed but worker/Beat remain stopped.

Recurring readiness now enforces outbound-alert and automatic-offhost-backup confirmations.
Both remain false; scheduling/global spending/publication stay off with zero caps and
no times. A distinct one-video sound trial is implemented/proposed at 1 USD maximum,
private only, but has not been run or charged; previous trial approvals are not reused.
Public model prices refreshed without a key: Veo silent 1080p 0.05 USD/s (0.80/16s),
Gemma 0.0765/0.255 and Gemini 0.25/1.50 USD per million input/output tokens.

144 regressions and 47 installed runtime checks pass; installed source hashes match.
Existing 2 jobs/4 generations/2 publications/12 usages and 1.601434 USD actual plus
0.20 USD held are preserved. All six existing private-video translations and hashtags
still match Google, and previous public video is unchanged. Pending: owner legal-page
review/publication approval and fresh private-test cap; authenticated email setup/test;
durable Google status/new grant; automatic off-host destination; recurring times/caps.

Evidence: docs/evidence/owner-offhost-backup-transfer-2026-11-05.json,
owner-offhost-restore-drill-2026-11-05.json, prelaunch-google-console-inspection-2026-11-05.json,
prelaunch-final-tests-2026-11-05.xml, prelaunch-operations-runtime-2026-11-05.json,
prelaunch-operations-installed-2026-11-05.json and prelaunch-current-pricing-2026-11-05.json.
Review proposal: docs/PRELAUNCH_PROPOSAL.md. Earlier sections follow as history.

## Current update — discovery hashtags and action sound defaults

Owner requested relevant hashtags and action-matched sound rather than music. Installed
contextual_audio_v3 for new reusable jobs: planned original synthesized effects, no paid
audio service or automatic music substitution. Unsupported plans stop before paid video
generation. Practical minor-defect tolerance remains unchanged; legacy jobs keep music.
New creative guidance includes accurate concise localized titles, subject-first descriptions,
relevant hashtags, immediate action and a coherent ending. Hashtags are included in all
six descriptions; no claim of guaranteed views is made.

Google confirms the existing private trial G9wNpynDbPY has the requested hashtag block
in en/fr/es/it/ru/zh-CN. Its media/music/privacy and original 91-point approval are unchanged.
The initial incomplete confirmation was reconciled by reads; saved intent now tolerates
Google tag reordering and never resends a submitted edit. The previous public qNsEQFHoMdk
and all counts/costs/holds remain intact: 2 publications, 4 generations, 12 usages,
1.601434 USD confirmed and 0.20 USD held. No new paid AI call or upload occurred.

A separate local 15.8s preview with synthesized water sounds is ready in
generated/private-trial/blue-ceramic-leaf-water-sounds-preview.mp4. Its elementary video
stream hash exactly matches the approved original and technical/audio checks pass. It
has not been uploaded or given a new AI quality approval. YouTube requires a new upload
to change the media file; never overwrite the old approval or silently duplicate it.

138 regressions and 40 installed runtime checks pass; source hashes and API/future-worker
images match. Only API/PostgreSQL/Redis run. Local simulators and disposable PostgreSQL
are stopped. Postman status succeeds with normal Keychain access and is signed out.
Scheduling and global spending/publication remain off, budgets zero. New SoundPlan fields
and real sound-quality review have not been exercised through a paid live model; keep
this limitation and the durable Google/off-host backup/notification prerequisites visible.

Evidence: docs/evidence/discovery-sound-final-tests-2026-11-05.xml,
discovery-sound-runtime-2026-11-05.json, discovery-sound-release-2026-11-05.json,
discovery-sound-private-trial-verified-2026-11-05.json and water-sounds-preview-2026-11-05.json.
Contract: docs/DISCOVERY_AND_SOUND_CONTRACT.md. Earlier milestone sections follow as history.

## Private trial completed — 91/100, six languages, private on YouTube

The separately authorized one-video trial completed after supervised quality recovery:
https://www.youtube.com/watch?v=G9wNpynDbPY. Google confirms processed_private, HD,
expected TechnoInno channel, English default and exact hl=en/fr/es/it/ru/zh-CN title/
description readbacks. Final source hash and the local owner-review copy match.
Practical review scored 91/100, with coherent audio and one minor visible finding;
the configured tolerant policy accepted it. The same two clips were reused throughout.

Confirmed trial cost: 0.800908 USD. Three failed/uncertain review reservations remain
held (0.14 USD), so trial exposure is 0.940908 USD under the 1.00 USD maximum. The owner
explicitly authorized two further diagnostic/corrected-review calls after automatic
approval rejected a diagnostic request; exactly those two calls were then used. No
blocked call executed before consent, no clips were regenerated, and no public post
was made. Existing public video qNsEQFHoMdk and original rejected job are preserved.
There are now two publications/four generations/twelve usage entries, cumulative
confirmed AI cost 1.601434 USD; older 0.06 USD holds are also preserved.

Google's diagnostic body reported only generic INVALID_ARGUMENT. A compact native
schema plus the standard Google AI Studio endpoint succeeded; the individual cause
was not isolated. Full Pydantic score/timestamp/audio validation remains unchanged.
The persistent correction applies the verified request shape to Gemini reviews and
uses a 300-second read deadline in reusable production. 123 regressions pass, including
four new compatibility/no-retry cases, using local HTTP providers and PostgreSQL.
The correction is installed: 37 runtime checks pass, installed hashes match tested
source, and the future worker tag uses the same image. Only API/PostgreSQL/Redis run.

Scheduling/global spending/publication/account automatic approval remain disabled,
with zero recurring caps. The operational live-validation confirmation stays false
pending owner review and unattended-operation preparation. This was a supervised
recovery, not proof of fully unattended robustness. Next: owner views the private result;
then durable Google access, off-host restore, outbound alerts and agreed times/budgets.

Evidence: production-private-trial-live-verified-2026-11-05.json,
production-private-trial-progress-2026-11-05.json,
production-private-trial-fix-tests-2026-11-05.xml and production-private-review-fix-release-
2026-11-05.json in docs/evidence/.

## Earlier stopped trial stage — subsequently recovered

The owner explicitly authorized one private trial, maximum 1.00 USD additional spend.
Job a13b3205-90ae-49ef-8675-24bd919ff709 generated its own six-language brief and two
8-second clips of a water droplet on a blue ceramic leaf, then rendered original music
and a 0.2s dissolve. Final file: 15.8s, 1080x1920 H.264/30fps/AAC, 8,745,758 bytes;
full decode/audio checks pass. SHA-256:
9f1babe950ef63a4f1ec0294c02a3021dee794218c89420b5accf202293416f6.
A matching owner-review copy is generated/private-trial/blue-ceramic-leaf.mp4.

Confirmed new cost is 0.800132 USD (creative 0.000132 + two 0.40 clips). The original
quality call lost its connection and was not automatically repeated. A separate,
supervised review of the exact same review payload, within the trial cap, received
HTTP 400. Both reservations remain held: 0.10 USD total. No quality decision was
invented, no media was regenerated and no YouTube upload occurred. The job remains
owner_attention. The known HTTP 400 needs diagnostic details; the adapter currently
exposes only a safe status, so the supervised helper now prepares private error capture.

Automatic approval rejected a further diagnostic call because the single-trial consent
was judged insufficiently explicit for that additional request. The owner was asked
to authorize at most two further calls (diagnostic and corrected review), still within
1.00 USD total. No blocked call was executed. A 0.04 diagnostic reservation followed
by at most 0.05 for corrected review would keep total exposure at 0.990132 USD if
all existing uncertain reservations remain held. They are not additional video runs.

Only API/PostgreSQL/Redis run; all global recurring flags/caps/account approval remain
off/zero. There are four generations, one publication, ten usage entries and cumulative
confirmed AI cost 1.600658 USD; legacy holds 0.06 plus this trial's 0.10 remain held.
The original public sample is preserved. This trial has NOT established complete real
automatic quality approval or publication. Evidence: production-private-trial-authorization,
production-private-trial-progress, production-private-trial-media-audit and
production-private-trial-key-usage (2026-11-05) in docs/evidence/.

The reusable implementation snapshot below predates this paid trial.

## Reusable workflow installed — live validation pending

The owner authorized completing the reusable workflow and testing it with simulated
providers while leaving recurring controls off. Per-job creative briefs, media,
six-language metadata, original music, practical review and approved-video uploads
are now connected to dispatch. Optional two daily timezone-aware slots are implemented
but unset. Budget reservations use actual configured limits; durable paid/upload intents,
row locks and resumable reconciliation prevent duplicate external submissions in the
tested cases. Minor findings can pass; important defects/uncertainty stop without
paid automatic regeneration. Exact duplicate concepts and finished media are blocked.

119 regressions passed, including 21 complete-workflow/recovery tests with local HTTP
OpenRouter/YouTube stand-ins and PostgreSQL. Fourteen legacy OpenRouter scenarios also
passed. The installed API passes 37 runtime checks. A real isolated Celery prefork
process is used for a synthetic render/resource check; the future worker cap is 512 MiB
because the 384 MiB probe reached its cap. Worker and Beat stay off after validation.
No new paid model request or YouTube upload occurred during implementation.

Live checks preserve one Publication, two generations, five model-usage entries and
0.800526 USD confirmed cost, plus 0.06 USD conservatively held legacy reservations.
The public video qNsEQFHoMdk retains its six localized titles/descriptions. Global
spending, publishing and scheduler flags remain false; caps are zero and account
automatic approval remains false. A one-job private trial is prepared, capped at
1.00 USD additional spend, but requires explicit human authorization before execution.

Before unattended launch: complete that real cycle, verify durable Google access
(last known Testing; console not inspected), implement outbound failure delivery and
off-host encrypted backup/restore, then choose two times and recurring budget caps.
Details: docs/SCHEDULED_PRODUCTION_READINESS.md and docs/PRODUCTION_WORKFLOW_CONTRACT.md.
Evidence: docs/evidence/production-workflow-*2026-11-05.*.

Earlier sections below record previous milestones and their historical counts.

## Six-language public publication completed

The owner authorized the proposed next step (localize and publish the same video),
adding Russian and Mandarin to English/French/Spanish/Italian. English is the default;
Mandarin metadata uses simplified Chinese, code zh-CN verified against the live
i18nLanguages response. Six reviewed titles/descriptions, preserving the AI disclosure,
are implemented without additional paid AI calls. They are visible in the dashboard
and protected publication plan for video qNsEQFHoMdk.

The fixed-video publisher preserves existing tags/category/other translations, updates
metadata first, reads back every translation, then makes the same video public and
verifies it. It reconciles lost responses before repeating writes and never uploads
another video. Published time is set only after public visibility is observed.
The original private upload remains idempotent and can report an explicitly authorized
later public state. Global generation/publication/scheduler flags remain false.

98 regression tests passed, including eleven real-HTTP simulated publication cases,
and ten OAuth HTTP simulation scenarios passed. All 34 installed runtime checks pass.
The owner personally granted the additional edit scope and confirmed completion.
The live plan reports edit_consent_granted=true, and the authorized publication API
returned HTTP 200, published_public, on the same video qNsEQFHoMdk. Google confirms
English default, all six title/description pairs, public visibility, processed media
and no regional restriction. Individual hl=en/fr/es/it/ru/zh-CN reads each return the
exact prepared localized title and description. An unauthenticated YouTube oEmbed
request also returned HTTP 200 with TechnoInno and the English title.

There is still one Publication, two generations, five model-usage entries and confirmed
AI cost 0.800526 USD. Published time is recorded; the original rejected generation job
is preserved. No media reupload or new AI call occurred. The dashboard reports the
public video. Scheduling, automatic spending/publication, account automatic approval
and zero budget caps are unchanged. This one-video milestone is complete.

Implementation: tsu/youtube_metadata.py, youtube_publication.py, youtube_auth.py,
youtube_upload.py, api.py and admin.html; protected contract:
docs/YOUTUBE_MULTILINGUAL_CONTRACT.md. Evidence: docs/evidence/youtube-multilingual-plan-2026-11-05.json,
youtube-multilingual-runtime-2026-11-05.json, youtube-multilingual-tests-2026-11-05.xml
and google-oauth-edit-simulation-2026-11-05.json. Earlier sections retain prior phases.
Live completion: docs/evidence/youtube-multilingual-publication-result-2026-11-05.json,
youtube-multilingual-public-live-2026-11-05.json and youtube-public-access-2026-11-05.json.

## First private YouTube API upload completed

The owner requested uploading the current video through the installed API. The
balanced_audio_v2 preview (15.8s, original music, 1080x1920) was uploaded once to
@techno-inno, privately and without subscriber notifications:
https://www.youtube.com/watch?v=qNsEQFHoMdk. Google's videos.list confirms the exact
configured channel, privacy=private, uploadStatus=processed, processingStatus=succeeded
and definition=hd. YouTube reports the rounded duration PT16S. The source SHA-256 is
29d699d71eb424c369bef415d5191b313f806961aec46907aee5d836a17a4eaf.

Resumable transfer, encrypted saved sessions, private-only protected API routes and
processing reconciliation are deployed. A fixed operation and PostgreSQL lock prevent
duplicates; uncertain initiation stops rather than creating another upload. The
dashboard links to the uploaded video. The request sent containsSyntheticMedia=true
and a clear AI disclosure in the description; Google's readback omits that boolean,
so its stored value is not independently verified. No public publishing was enabled.

85 regression tests passed, including 14 private-upload tests using a local HTTP
simulation and PostgreSQL. All 27 installed runtime checks passed. The local mock
cannot verify binary fidelity; actual Google acceptance and successful processing
establish the real media transfer. The original rejected job remains unchanged; the
edited variant is recorded as an owner-requested private test, without new AI approval.
There are two generations, one publication and five usage records. Confirmed AI cost
remains 0.800526 USD. Global spending/publication/scheduler flags remain false and
budget caps zero. Only API, PostgreSQL and Redis run; worker/Beat remain off.

Evidence: docs/evidence/youtube-private-upload-live-2026-11-05.json,
youtube-private-upload-verified-2026-11-05.json, youtube-upload-runtime-2026-11-05.json
and youtube-upload-tests-2026-11-05.xml. The earlier sections below describe prior
phases; their zero-publication counts are historical.

## Audio and practical review defaults implemented

The owner's follow-up requested that the suggested audio and more tolerant quality
rules apply to future videos. Profile balanced_audio_v2 is now implemented in the
shared renderer and the manual runner, and exposed in protected capabilities and the
dashboard. Source clips still request generate_audio=false, but final renders MUST
include an audible original ambient track mixed locally. The review copy retains AAC
audio. A missing soundtrack stops before any paid call; absent/silent audio blocks
technical validation. Music provenance and its generator are retained in the repository.

A 0.2s dissolve softens the join; two 8s clips render to 15.8s. The score threshold
remains 80. Minor/inspection-only defects are tolerated; important normally visible
issues require timestamps and concrete evidence. Fixable major issues route to local
editing. Uncertain findings, ungrounded severe claims, low scores or unobservable audio
route to manual review. No decision triggers an automatic paid regeneration.

71 regression tests and 14 real HTTP simulation scenarios passed. The actual review
payload was decoded and checked for AAC audio. Existing completed results return
unchanged before provider access, preserving the rejected first sample and avoiding
new charges on resume. Unfinished legacy jobs require explicit migration.

A separate local preview was rendered from the two already purchased clips:
generated/first-video/first-video-v2.mp4, with music and the short dissolve. It has not
received a new paid AI review and does not retroactively approve the first job.
Details: docs/PRODUCTION_PROFILE.md and docs/evidence/openrouter-simulation-audio-2026-11-05.json.
Deployment verified: all 27 installed runtime checks passed. The protected capabilities
API exposes balanced_audio_v2 with music ready, and the installed production module
hash matches local source. Live counts remain two generations, zero publications,
five usage records and 0.800526 USD confirmed cost. A completed legacy resume using a
provider object with no API methods returns the original rejected result unchanged.

The initial one-pass dissolve failed on FFmpeg 7 (CFR metadata order), then exceeded
the 384 MiB process limit. The final renderer normalizes frame-rate metadata after
timestamp changes and renders the short overlap separately, concatenating encoded
prefix/join/suffix before adding music. Real source clips now render and fully decode
successfully on the VPS within the existing 384 MiB limit; review AAC is retained.
No VPS upgrade, extra paid model call or retrospective approval occurred.
Evidence: docs/evidence/audio-profile-live-2026-11-05.json,
audio-profile-runtime-2026-11-05.json and audio-preview-vps-2026-11-05.json.

## First supervised video produced — automatic production remains off

The owner requested a first video now, explicitly keeping scheduled production off.
One native-1080p portrait, silent, 16-second MP4 was produced from two 8-second
Veo 3.1 Lite clips. The delivered master is generated/first-video/first-video.mp4;
its SHA-256 matches the VPS copy. FFmpeg confirms 1080x1920, H.264/yuv420p,
30 fps, exactly 16 seconds and complete decoding without errors.

Confirmed cost: **0.800526 USD** (two clips 0.40 each, review 0.000526), matching
the API key's total reported usage. The one manual runner used a 1 USD authorization
context; global environment caps stay zero and spending/publishing/scheduler flags
stay false. No worker or Beat was started and there are zero publications.

The review scored 82/100 but **vetoed approval** because of the visible join at 8s,
incoherent liquid motion across it, and spiral flicker/geometry instability. The
persisted job/video status is rejected. This is a first test artifact, not approved
publication material or proof that the economical model meets brand quality.
No extra video generation or automatic regeneration was performed.

The initial creative route returned HTTP 429; the operator prepared the brief instead
without repeating that request. Sending the full 17 MB master for review returned 413;
a bounded 540x960 full-duration review copy was then used. The master stayed intact.
Two original reservations (0.01 and 0.05 USD) remain conservatively held; no per-request
settlement evidence was invented. The key usage agrees with the confirmed successful
operations. A change in the unused creative model's current price was handled by
skipping its price validation only when an explicit operator brief is present.

Nine actual HTTP simulation scenarios passed with PostgreSQL and FFmpeg, followed by
52 full regression tests and two focused operator-brief tests. This first sample
does not establish an autonomous creative workflow. Evidence and review breakdown:
docs/evidence/first-video-live-2026-11-04.json; scripts and scope: docs/FIRST_VIDEO.md.
After deployment, all 27 installed runtime checks passed, including owner login,
database readiness, zero recurring caps and disabled scheduling/publishing. Temporary
test services were stopped and the four exited pilot containers were removed; media
and database records are retained. Only API, PostgreSQL and Redis remain running.


## Current model policy — lower cost with sufficient quality

The owner explicitly requested cheaper models with a useful quality/cost balance.
Current public OpenRouter catalogues were refreshed: 31 video models and 454 total
models. Provisional model IDs are configured locally and on the VPS:

- Creative: google/gemma-4-26b-a4b-it (0.027/0.08 USD per million input/output tokens).
- Video review: google/gemini-3.1-flash-lite (0.25/1.50 USD per million input/output tokens).
- Video: google/veo-3.1-lite, planned native 1080p portrait, silent, two 8-second clips:
  0.80 USD generation per 16-second attempt. A 720p variant costs 0.48 USD.
- Alternative comparison: x-ai/grok-imagine-video-1.5-lite, 720p portrait, 15 seconds,
  0.45 USD generation. Its 1080p mode is upscaled from 720p and is not the chosen mode.

These are configured candidates, not a completed live generation integration or proof
of brand-specific quality. Keep the existing 80/100 threshold and severe-defect vetoes;
no automatic premium-model fallback. Judge by measured cost per accepted video.
Seedance 1.5 Pro is excluded because its page announces removal on 2026-11-11.
The cheapest catalogue item Mischief 1 is image-to-video/landscape-only and unsuitable.

The old 50 USD benchmark proposal is superseded by a nine-version, 5.19 USD generation
comparison; a maximum 10 USD pilot would still require explicit authorization after
adapters are ready. Production budget remains zero. At 60/75 native-1080p attempts,
video generation alone would cost 48/60 USD, excluding text/review and infrastructure.

VPS verification passed: selected IDs loaded, database ready, YouTube still connected,
all spending/publication/scheduler controls off, no paid request or upload. Other
credentials/settings were preserved. No image or database migration change was needed.
Cost details: COST_ESTIMATE.md. Evidence: docs/evidence/low-cost-model-selection-2026-11-04.json
and low-cost-vps-verification-2026-11-04.json; raw catalogues saved alongside them.

## Current owner handoff — YouTube connected and verified live

The owner completed Google's consent flow and reported Connected: @techno-inno.
A server-side check confirms the saved connection matches TechnoInno,
channel UC8DbuevZRxVTWxltG9oDFRw. The required YouTube scopes and offline refresh
credential are present. Encrypted credential decryption succeeded; a real Google token
refresh and authorized channels.list(mine=true) check both passed. Refreshed credentials
were encrypted and saved with a compare-and-update guard against a concurrent reconnect.
No token material was printed or placed in evidence. No upload or paid request occurred.

Evidence: docs/evidence/youtube-live-connection-2026-11-04.json.
Daily/monthly budgets remain zero; spending, publishing and the daily scheduler are off.
The earlier Google test-user 403 is resolved. Do not ask the owner to repeat consent,
credentials, DNS, SSH or certificate setup. The last reported app status was Testing;
seven-day grant expiry must be addressed before unattended operation. A successful refresh
now does not prove that the grant will survive that Testing limit or future revocation.

## Latest fix — native browser login origin rejection

The owner reported `Request origin is not allowed` from the browser login form.
Global `Referrer-Policy: no-referrer` caused native HTML form POSTs to carry
`Origin: null`, which the exact origin check correctly rejected. Earlier scripted
HTTP tests supplied Origin explicitly and did not expose this browser behavior.

The middleware now uses `strict-origin` on ordinary pages (origin only, no path/query),
while the OAuth callback keeps `no-referrer`. Exact origin checks, CSRF, secure cookies,
and callback secrecy remain in place. Null and foreign origins are still rejected.
API rebuilt/deployed over SSH; a rollback image and code archive were retained.

Focused API/OAuth regression tests: **26 passed**, one PostgreSQL-specific test deselected.
The installed verifier now checks form and callback policies; **27 runtime checks passed**.
A native in-app-browser form submission with an intentionally wrong test password now
shows the expected password error instead of an origin error. This demonstrates that
normal form submission reaches password validation. Real owner login succeeds in HTTP
runtime checks. The browser has been left at the owner login for the human to sign in.

Primary behavior reference: https://fetch.spec.whatwg.org/#append-a-request-origin-header
Evidence: docs/evidence/vps-origin-fix-runtime-2026-11-04.json and
vps-origin-fix-https-2026-11-04.json. No paid request or upload was performed.

## VPS installation and public HTTPS verified

The owner explicitly authorized installation over SSH on 2026-11-04, resolving the
previous approval-review block. Docker 29.9.3, Compose 5.7.0, Nginx and Certbot are
installed on root@203.161.61.3. Code and separate private credentials were transferred
via SSH to /opt/technoinno (directory 0700, environment file 0600).

- API, PostgreSQL 17 and Redis are running and healthy; migration 7d920bb1c441 applied
  and all 16 application tables exist. Worker and Beat have not been started.
- All **25 installed runtime checks passed**, exercising actual owner login, session
  logout/revocation, CSRF, protected endpoints, database readiness, zero budget caps,
  disabled spending/publishing/scheduler and the exact Google OAuth redirect/PKCE.
- The verifier created and removed its temporary session/flow. There are zero owner
  sessions, OAuth flows/credentials and production jobs after verification.
- Both authoritative servers, Google and Cloudflare return studio A 203.161.61.3;
  no studio AAAA. The root domain also points to the VPS. The agent changed no DNS.
- External ACME validation route returned 200. Trusted HTTPS is now active; plain
  HTTP redirects to HTTPS. The 25 checks also passed over external TLS, including real
  owner login. API 8000/PostgreSQL 5432/Redis 6379 are unreachable from outside.
- About 453 MB memory available and 13 GB disk free after startup. API uses about
  93 MiB of its 256 MiB limit; PostgreSQL about 73 MiB, Redis about 6 MiB.
- The owner personally accepted Let's Encrypt Subscriber Agreement v1.8 and explicitly
  authorized the request. Certificate issued for studio.technoinno.live, expiring
  2027-02-02. Nginx syntax/TLS checks pass; renewal timer/reload hook enabled and a
  Certbot renewal dry run with deploy-hook execution succeeded.
- Ordinary DNS queries now also resolve on this Mac, but its system HTTP resolver still
  caches the earlier missing result. External TLS tests used the verified IP while retaining
  the domain, SNI and normal certificate validation. Public authoritative/Google/Cloudflare
  DNS and CA validation succeeded; no DNS changes are needed.
- No real Google consent, paid AI request, video generation or upload occurred.

Evidence: docs/evidence/vps-runtime-check-2026-11-04.json,
vps-https-check-2026-11-04.json, vps-port-check-2026-11-04.json,
dns-ready-2026-11-04.json and vps-install-2026-11-04.json.

## Earlier DNS recheck — historical

At the earlier check, direct queries to both registrar nameservers returned NXDOMAIN
for studio.technoinno.live; the root domain had no A answer. Google (8.8.8.8) and
Cloudflare (1.1.1.1) agreed. The owner has since corrected the names as verified above.
Active NS records are the two registrar-servers.com servers. The studio A record
was not then published at the intended name. Follow-up authoritative queries found
`studio.technoinno.live.technoinno.live` and `technoinno.live.technoinno.live`, both
pointing to 203.161.61.3: full names were apparently entered in the Host fields.
Correct the studio Host to `studio`; root Host would be `@` only if the owner wants
the main domain on this VPS. Keep the IP and save. Earlier successful VPS-resolver resolution is historical
and must not be treated as present authoritative DNS readiness. Main-domain A records
are separate; do not alter them without the owner's requested scope.

At that time deployment was pending approval; the later explicit installation
instruction above supplies that authorization.

## Latest owner handoff — YouTube only

- Google account: admin.technoinno@gmail.com.
- YouTube channel: TechnoInno, https://www.youtube.com/@techno-inno.
- Public channel page resolved ID UC8DbuevZRxVTWxltG9oDFRw; Google authorization must
  return this same ID before a connection is stored.
- Instagram: paused. TikTok: paused. Neither is a launch dependency.
- SSH inspection succeeded as root@203.161.61.3. Fresh Ubuntu 24.04.5, one CPU,
  about 1 GB RAM, 16 GB free disk; only SSH listening, no Docker/web server installed.
- Owner added studio.technoinno.live DNS; resolution to 203.161.61.3 was verified.
  This earlier resolver result was superseded by the fresh checks above.
- Local `.env` contains OpenRouter key and YouTube OAuth client ID/secret. Presence
  checked without showing values; OAuth client ID format recognized. Credentials
  have not been authenticated. Owner confirmed the OAuth client is a Web application.
- Local `.env` permissions restricted to owner access. No secret values copied to docs.
- Target: two original videos/day published to YouTube only. No channel rename,
  public upload, paid run or server modification was performed in this handoff.

## Completed

- Read project brief and inspected empty workspace, tools and available runtimes.
- Researched current OpenRouter text/video API, live video catalogue, pricing/limits.
- Compared three video families and calculated production/pilot scenarios.
- Researched official YouTube/TikTok documentation and Meta's official collection.
- Created architecture, plan, cost estimate, owner setup checklist and decision log.
- Prepared starter profile text and unverified handle candidates.
- Implemented M1: protected admin API/status shell and versioned OpenAPI contract;
  all 11 requested database tables plus budget guard and alerts; frozen initial migration.
- Implemented durable idempotent jobs, preflight leases/fencing, expired-lease recovery,
  two idempotent daily slot keys, Celery/Redis configuration and a preflight scanner.
- Implemented PostgreSQL-serialized decimal cost reservations, immutable settlements,
  stale reservation holds, overrun freeze and deduplicated persistent budget alerts.
- Added structured creative/quality/provider contracts, capability validation and
  real full-file FFmpeg/FFprobe technical checks. No real AI agents are connected yet.
- Created Docker Compose scaffold, environment example, dependency lock, operations
  procedure, owner setup guidance and saved research evidence.
- Orbit free API discovery/integration succeeded; brief saved without credentials.
- Implemented owner browser login, session hashes/expiry, password-rotation revocation,
  CSRF protection, and a Google YouTube OAuth adapter with state/PKCE and channel binding.
- Added three OAuth/session tables and migration; Google grants are encrypted with a
  separate deployment key. No upload starts from the connection flow.
- Deployed the VPS release, memory limits and ACME-only Nginx configuration.
  Built both application images and applied migrations; installed runtime checks pass.

## Latest verification — local OAuth milestone

- **48 tests passed**, including real local PostgreSQL, concurrent OAuth state consumption,
  owner password rotation, failed reconnect preservation, and previous foundation coverage.
- **9 HTTP simulation scenarios passed** using the real Google client against local Postman
  stand-ins: success, wrong/empty channel, missing refresh token/scope, token/API errors,
  server failure and timeout. Request events and stored credential counts were inspected.
- OAuth migration rollback/reapply and Alembic drift checks passed on PostgreSQL 15.
- Ruff, compilation, dependency checks, bootstrap shell syntax and Compose source checks passed.
- Proxy mode exposed a local CLI certificate/Python 3.13 compatibility issue; simulation used
  loopback HTTP with synthetic credentials. Production Google HTTPS verification is unchanged.
- Postman signed-in status still fails on macOS Keychain; local simulation works without sign-in.
- Temporary local test services stopped after verification. No live Google grant, upload,
  paid generation or deployed HTTPS was tested in that local milestone.
  The later VPS image build and runtime checks above now pass.

## Earlier foundation verification — historical evidence

- **36 tests passed**, including real PostgreSQL 15 concurrency, reservation deduplication,
  daily/monthly caps, cost-overrun freeze, persistent alert deduplication, worker fencing,
  expired leases, job idempotency, auth, contract snapshot and synthetic-video decode checks.
- Migration upgrade → downgrade → upgrade passed; Alembic reports no schema drift.
- Local custom-format test DB backup restored to a separate disposable database;
  all 13 application-table row counts and migration revision matched. This does not
  establish encrypted off-host production backups or media-object restoration.
- Ruff lint and formatting passed; dependency consistency check passed.
- Compose YAML parsed; actual Docker image build, Redis/Celery transport and target
  PostgreSQL 17 deployment remain unverified because Docker is unavailable.
- One upstream Starlette warning: its httpx TestClient integration is deprecated;
  the tests pass. Migrate test transport before that compatibility path is removed.
- Temporary database stopped after verification; no service is left running.

## Historical foundation status

Phase Zero, M1 foundation and the local owner/YouTube OAuth feature are delivered.
This is not the complete production system. Live creative/video/visual-QA adapters,
S3, post-production encoding, publishers, autonomous full-pipeline
recovery, outbound alerts, full dashboard and analytics remain. Synthetic fixtures
were used only for technical tests, not as brand content.

## Historical foundation blockers and uncertainties

- Real Google consent, channel binding, encrypted storage, token refresh and channel read
  are verified. Upload/processing/reconciliation workflows remain unimplemented and untested.
- Resolve Google Testing-mode grant expiry before unattended use. OpenRouter credential
  presence is known; its authenticated provider access remains unverified.
- No explicit spending cap authorization or public-publishing authorization yet.
- Instagram and TikTok are paused; their setup and policy constraints do not block YouTube.
- Paid three-model benchmark not run; no default video model selected.
- The earlier automatic approval-review block was resolved by the owner's explicit
  installation instruction. VPS packages, image build and onboarding deployment now pass.
- Docker/Compose remain unavailable locally; Docker verification ran on the authorized VPS.
- Postman CLI status fails with macOS Keychain error (exit 139); external workspace
  discovery/publishing skipped. Local API contract does not depend on it.
- Certificate terms, issuance, HTTPS and renewal test are complete; no hosting approval remains.

## Historical foundation next task

Implement the YouTube-only generation and quality pipeline, exact current model quotes,
and durable resumable upload/reconciliation. Keep all paid submissions and uploads off
until a concrete sample/benchmark is reviewable and the owner authorizes its spending
cap and any private test upload. Real token refresh/channel access are now verified;
Google project production/personal-use configuration and off-host recovery still need
resolution before a daily autonomous launch. No account setup needs repeating.

## Session artifact index

- Planning: ARCHITECTURE.md, IMPLEMENTATION_PLAN.md, COST_ESTIMATE.md, MANUAL_TASKS.md,
  DECISIONS.md, README.md, docs/RESEARCH.md, docs/BRAND_STARTER.md, docs/PROJECT_BRIEF.md.
- Backend: tsu/config.py, db.py, models.py, budget.py, jobs.py, worker.py, api.py,
  contracts.py, media.py and admin.html.
- Contracts/deployment: docs/API_CONTRACT.md, docs/openapi.json, migrations/, alembic.ini,
  compose.yaml, Dockerfile, pyproject.toml, requirements.lock, .env.example, .gitignore.
- Verification: tests/, docs/VERIFICATION.md, saved catalogue/Orbit evidence in docs/evidence/.
- OAuth: tsu/security.py, browser_auth.py, youtube_auth.py, login.html; new migration;
  tests/test_youtube_auth.py; docs/OAUTH_CONTRACT.md; Postman contract/mock/simulation.
- Deployment: deploy/, compose.vps.yaml, scripts/prepare_vps_bundle.py; local code release
  and separate private runtime files are in ignored .runtime/. Code and the private
  environment were transferred via SSH; secret files are not in the code archive.

Resource validation: the actual isolated Celery prefork task rendered and inspected
1080x1920 video plus AAC review successfully; peak 394.95 MiB under a 512 MiB cap,
with no memory-limit hits or OOM events. Temporary worker removed; only API/PostgreSQL/
Redis remain. Synthetic media only, no provider charge or upload. Evidence:
docs/evidence/production-workflow-celery-render-2026-11-05.json.
