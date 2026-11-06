# Phase Zero research — checked 2026-11-04

Evidence levels: public documentation, live unauthenticated catalogue, local tests.
No authenticated generation, platform upload, paid benchmark, or approval has occurred.

## OpenRouter

Text uses `POST /api/v1/chat/completions` with a configurable model and bounded
output. Compatible models support JSON Schema structured output; validate locally too.
Sources: [API overview](https://openrouter.ai/docs/api_reference/overview),
[structured output](https://openrouter.ai/docs/guides/features/structured-outputs).

Video is a separate async API: submit at `/api/v1/videos`, persist its job ID,
poll `/api/v1/videos/{id}`, then retrieve `/content`. Poll responses can contain
usage cost. Use polling initially. Source:
[video generation](https://openrouter.ai/docs/guides/overview/multimodal/video-generation).

The [live catalogue](https://openrouter.ai/api/v1/videos/models) was fetched without
credentials or charges. A selected-field snapshot is saved in
[evidence](evidence/openrouter-video-models-2026-11-04.json). This is stronger evidence
for routed capabilities than illustrative schemas or marketing pages. Fetch again
before benchmarking; combinations may still have provider-specific restrictions.

| Candidate | Actual catalogue durations | Portrait | Resolutions | Proposed target construction |
|---|---|---|---|---|
| google/veo-3.1-fast | 4, 6, 8 sec | 9:16 | 720p, 1080p, 4K | 2 × 8 sec = 16 sec |
| bytedance/seedance-2.0 | integers 4–15 sec | 9:16 | 480p, 720p, 1080p, 4K | 1 × 15 sec |
| alibaba/wan-2.6 | 5, 10 sec | 9:16 | 720p, 1080p | 2 × 10 sec = 20 sec |

Wan's [model page](https://openrouter.ai/alibaba/wan-2.6) advertises up to 15 seconds,
but the routed catalogue exposes 5/10. Its lowest advertised rate is a 480p SKU,
while 480p is not in supported resolutions. Do not use that teaser rate in the budget.
Veo's [page](https://openrouter.ai/google/veo-3.1-fast) makes it a useful lower-cost
candidate; Seedance's [page](https://openrouter.ai/bytedance/seedance-2.0) describes
reference/camera consistency and provides the video-token formula. These are candidate
rationales, not a quality benchmark for our brand.

Video SKU selection must include modality, resolution, audio and pixel dimensions.
See COST_ESTIMATE.md for catalogue-based arithmetic. No duration padding or slow-motion
stretching is assumed. For multi-clip models, benchmark continuity and transitions too.

[Limits](https://openrouter.ai/docs/api_reference/limits) vary by provider. Respect
Retry-After on throttles, apply jitter and bounded polling, and distinguish depleted
credit from transient in-flight limits. Check `/api/v1/key` using the owner's future
key; do not infer account limits from public docs. [Pricing](https://openrouter.ai/pricing)
currently lists a 5.5% Standard credit-purchase fee, exclusive of applicable taxes.
Do not assume failed video jobs are free from text-token billing statements.

## Publishing feasibility

| Platform | Verified route and constraints | Launch consequence |
|---|---|---|
| YouTube | `videos.insert`, OAuth `youtube.upload`; use resumable upload and explicit private visibility during validation | Brand Google identity/channel and OAuth configuration required |
| TikTok | Direct Post scope `video.publish`; creator-info and status polling, audited public posting, required per-post controls | Private internal uploader conflicts with intended use; unattended direct posting blocked |
| Instagram | Meta's official collection verifies Professional accounts, a Facebook Login/Page route, Reels containers and publish | Direct Instagram Login preferred provisionally; verify its app-specific access before implementing |

YouTube's [current insert reference](https://developers.google.com/youtube/data/reference/rest/v3/videos/insert)
states unverified projects are **not** restricted to private uploads, and documents
100 upload calls/day with one Video Uploads bucket unit per call. This differs from
older guidance. Recheck the actual console quota and OAuth requirements; API project
audit and OAuth consent verification are distinct. Explicitly set visibility and
`containsSyntheticMedia` where applicable. [Google OAuth](https://developers.google.com/identity/protocols/oauth2/web-server)
requires owner consent and refresh-token lifecycle management for unattended use.

TikTok's [sharing guidelines](https://developers.tiktok.com/docs/en/content-sharing-guidelines)
exclude owner/team-only uploader utilities, require an audit for public API posting,
and require editable metadata, manual privacy selection, preview and express consent.
Do not build a consent bypass. A manual export workflow is possible; an approved broader
integration needs separate feasibility review. [Direct Post setup](https://developers.tiktok.com/docs/en/content-posting-api-get-started)
also requires a registered app, scopes and verified media URL ownership.

Meta's [official collection](https://www.postman.com/meta/instagram/documentation/6yqw8pt/instagram-api)
documents Business/Creator accounts. Its Facebook Login route needs a linked Page,
`instagram_basic`, `instagram_content_publish`, and `pages_read_engagement`; Page
selection can require `pages_show_list`. Reels use a media container, processing wait,
then `media_publish`. Save container and published media IDs independently.

Direct Meta documentation returned 429/unavailable during research. Consequently,
Instagram Login scope names (`instagram_business_basic`, `instagram_business_content_publish`),
access level, review requirements, publishing quota, API version and insights permissions
remain provisional until verified in the owner's new app and accessible primary docs:
[Instagram Login](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login/),
[publishing](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login/content-publishing/).
Do not switch to personal Facebook login to work around this limitation.

## Analytics coverage

[YouTube Analytics](https://developers.google.com/youtube/analytics/metrics) supports
watch duration, engagement, subscribers and report-dependent retention data with
separate owner authorization. [TikTok's video object](https://developers.tiktok.com/docs/en/tiktok-api-v2-video-object)
exposes views, likes, comments and shares; it does not establish access to watch time
or retention. Instagram metrics remain capability-gated pending permission and current
metric discovery. Store each source, retrieval date and missing-data reason.

## Environment and gaps

Workspace initially empty. Python 3.13/3.14, FFmpeg/FFprobe, Git and PostgreSQL 15
binaries available. Docker/Compose and uv not found. Use Python 3.13 project venv.
Local PostgreSQL can validate schema and concurrent financial controls independently
of Docker. Deployment targets PostgreSQL 17 and needs its own Compose verification.

Postman CLI exists (1.80.0), but status fails with macOS Keychain error
`SecItemCopyMatching failed -50` (exit 139). Signed-in discovery and workspace
operations were skipped; no Postman workspace was created or published. Orbit's free
discovery and integration subsequently succeeded; the selected endpoints cover catalogue,
submission, polling and retrieval. Its [brief](evidence/orbit-openrouter-brief-2026-11-04.json)
corroborates primary documentation, but illustrative parameters are not live capabilities;
the direct catalogue takes precedence. No third-party workspace or paid service was created.

Timezone handling follows current IANA rules rather than a fixed Casablanca offset.
The [IANA July 2026 archive](https://lists.iana.org/hyperkitty/list/tz%40iana.org/2026/7/?count=50)
records the September switch to UTC. Tests cover budget boundaries before and after
that change. Container Python uses the pinned tzdata package rather than stale OS rules.

No username availability or account access is established by public search. Claim
availability must be checked in each platform's creation flow by the owner.
