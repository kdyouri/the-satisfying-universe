# First video — one-time run

Owner request: produce the first video now, keeping scheduled production disabled.
The preceding quoted plan is two 8-second Veo 3.1 Lite clips, 1080p portrait,
without audio: 0.80 USD generation. The runner limits this one requested video to
1.00 USD including bounded creative text and video review. No automatic regeneration,
YouTube upload, recurring spending or scheduler activation is included.

Concept: slow golden liquid forming a spiral inside a dark ceramic bowl, macro view,
warm studio light, no people, text or logos. The second shot uses a frame from the
first to improve continuity. Join and normalize locally to H.264/MP4, 1080x1920,
30 fps, 15–20 seconds. Inspect the whole file with FFmpeg and review the video with
Gemini Flash Lite. A rejected sample is retained honestly for owner review.

The installed API keeps its zero recurring caps and disabled work flags. Only this
manual runner constructs a 1 USD authorization context, recorded in the job payload.
PostgreSQL reservations and settlements use the existing serialized ledger. A fixed
first-video job key and an advisory lock prevent a second concurrent run. Each paid
submission is marked durably before HTTP. Ambiguous submissions cannot be repeated.
Known video job IDs can be polled/downloaded again without creating a new generation.
Unknown provider cost remains reserved; actual overrun freezes further spending.

Provider contract: OpenRouter POST /chat/completions (structured text/video review),
GET /videos/models and /models (fresh rates/capabilities), POST /videos (202 and id),
GET /videos/{id} (terminal status and usage.cost), GET /videos/{id}/content (MP4 bytes).
Construct URLs from the fixed API origin, never from returned polling URLs. Do not
follow authenticated redirects, log signed URLs or send the API key to another host.
Chat provider max_price bounds token rates; video SKU and parameters are rechecked
before submission. There is no paid POST retry or automatic model fallback.

Verification must cover real HTTP serialization, prices/capabilities, failed or
ambiguous submissions, missing cost, download boundaries and repeat/resume behavior.
The Postman stand-in is based on the official contract; it is synthetic evidence,
not evidence of real video quality or provider acceptance. Provider-owned mock lookup
is unavailable because Postman signed-in status fails in the local macOS Keychain.

Validation: nine real HTTP simulation scenarios passed against disposable PostgreSQL,
including successful assembly and resume without paid duplicates, changed prices,
chat/video errors, ambiguous timeout, missing cost, provider overrun and invalid media.
The full regression suite passed 51 tests in a separately migrated test database.
An initial attempt to reuse the simulation-created schema for Alembic tests failed
with duplicate tables; using a clean disposable database resolved this test setup issue.

Live first-run adaptation: the creative text route returned HTTP 429 before any clip.
Key usage remained zero when checked. No automatic retry or model substitution was
performed. The operator prepared the two prompts and French metadata explicitly in
operator-brief.json. This optional path preserves the original call marker and budget
reservation, records brief_source, and creates the same two planned clips. A dedicated
test confirms it makes no replacement creative API call and does not duplicate clips.
The original 0.01 USD reservation remains held until cost evidence is reconciled.
This supervised sample does not establish a fully autonomous creative workflow.

The first full-master review exceeded the upstream request size limit (HTTP 413).
The adapter does not retry it. The final implementation encodes a 540x960, full-duration
review copy, checks it is at most 6 MiB before sending, and reserves a separately named
quality_proxy operation. The old 0.05 USD reservation remains held. Source clips and
the native 1080p master are preserved. There is no video regeneration during resume.

Final observed result: 16 seconds, 1080x1920/30fps/H.264, technical pass. Confirmed cost
0.800526 USD, matching API key usage. Quality score 82/100 with severe-defect veto:
join discontinuity, incoherent liquid motion and spiral instability. Job/video rejected;
no publication, recurring flags off. Deliver as a first test requiring correction.

References:
- https://openrouter.ai/docs/guides/overview/multimodal/video-generation
- https://openrouter.ai/docs/guides/features/structured-outputs
- https://openrouter.ai/docs/guides/routing/provider-selection#max-price
- https://openrouter.ai/docs/guides/overview/multimodal/videos
