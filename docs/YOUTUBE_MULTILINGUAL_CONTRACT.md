# Six-language publication of the existing video — 2026-11-05

Completed live after the owner's personal edit consent: the existing video qNsEQFHoMdk
is public, English default, with exact six-language readbacks verified. Public metadata
is accessible without owner login. See evidence/youtube-multilingual-public-live-2026-11-05.json.

The owner explicitly authorized the proposed next step: English default metadata,
French/Spanish/Italian plus Russian and Mandarin translations, then make the same
uploaded video public. Scheduled production and global recurring publication stay off.
Mandarin metadata uses simplified Chinese, the verified YouTube language code zh-CN.
No new upload, AI generation or paid translation call is needed.

## Protected application contract

- GET /api/youtube/publication/plan returns the existing video ID, all six titles and
  descriptions, intended public visibility, and whether edit consent is present.
- POST /api/youtube/publication requires the strict body {confirm_publication:true}.
  It may update only the fixed already-uploaded owner video; no arbitrary ID, title,
  file or language is accepted. Bearer or existing owner-cookie/CSRF protection applies.
- GET /api/youtube/publication reads and verifies the current remote video without
  publishing it. It reports exact metadata, languages, default language and visibility.

Use the existing encrypted grant. New owner connections request youtube.force-ssl in
addition to the original upload/readonly scopes. Existing read/upload grants continue
to work; publication refuses writes until edit scope is actually granted. Google
consent is personally completed by the owner, as reserved in the original brief.

Before any write, require the known video ID, original uploaded SHA/Publication,
exact channel, successful processing, and no reported geographic restriction. A
PostgreSQL advisory lock serializes updates with the original uploader. Persist the
one-video public authorization, intended metadata and a recovery state before writes.
Never infer recurring spending/publication approval from this one-video authorization.

Read snippet/localizations first. Update snippet + localizations with English default
and all six translations while preserving category, tags and any unrelated translations.
Do not include status in that request: Google's part replacement semantics would
otherwise risk changing visibility. Read back every translated title/description and
the English default before issuing a separate status update with privacyStatus=public.
Preserve writable existing status settings; explicitly retain the AI disclosure and
not-for-kids setting. Read back exact ID/channel/public visibility and translated
metadata. Persist published_at only after public visibility is observed.

On a timeout or lost response, retain saved state. The next explicit call reads Google
first and skips updates whose desired state is already present. It never reuploads.
Public visibility without verified translations is not declared success. Unknown
errors remain safe/redacted, with no OAuth token/session URL in output or evidence.

Verification covers the actual caller against the existing local HTTP simulation:
six-language UTF-8 round trips, missing edit scope, partial consent, wrong channel,
metadata failure/readback mismatch, lost metadata/public responses, preserved unrelated
metadata, repeat calls and concurrency. Simulation does not establish Google's real
edit consent, public visibility or native localized display; live verification is separate.

Primary references:
- https://developers.google.com/youtube/data/reference/rest/v3/videos/update
- https://developers.google.com/youtube/data/reference/rest/v3/videos
- https://developers.google.com/identity/protocols/oauth2/web-server#incrementalAuth
- https://support.google.com/youtube/answer/6289575?hl=fr
