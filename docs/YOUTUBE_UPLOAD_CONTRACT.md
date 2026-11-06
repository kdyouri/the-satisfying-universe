# One private API upload test — 2026-11-05

Owner explicitly requested uploading the current video to TechnoInno through the API.
Scope: the existing balanced_audio_v2 preview, private, no subscriber notification.
No public publishing, new AI generation, scheduler or recurring authorization.
The original rejected sample is retained; this edited variant is an owner-requested
private test, not automatic quality approval.

- GET /api/youtube/test-upload/plan: protected fixed-asset SHA/size and French metadata.
- POST /api/youtube/test-upload: protected, strict body {confirm_private_test:true}.
  Cookie writes require existing CSRF protection. No arbitrary path or public visibility.
  The fixed operation is idempotent; changed bytes conflict rather than creating a copy.
- GET /api/youtube/test-upload: protected state; reconcile known remote ID via videos.list.
  No hidden upload on GET. Returned status distinguishes transfer and processing.

Before upload: require full technical/audio check; decrypt the saved offline grant,
refresh only if needed, validate scopes and channels.list(mine=true) against the exact
configured channel. Save refreshed grants encrypted with compare/update protection.

Use videos.insert uploadType=resumable, part=snippet,status, notifySubscribers=false.
Metadata explicitly includes privacyStatus=private, selfDeclaredMadeForKids=false and
containsSyntheticMedia=true. Persist a starting marker before the sole initiation
POST and persist the returned Location encrypted before sending media. Session URLs
must remain on the exact trusted Google upload origin/path; redirects are never followed.

Send bounded chunks. On interruption, a zero-length PUT with Content-Range bytes */N
queries Google's authoritative progress; resume only from the acknowledged next byte.
Persist the video ID immediately on completion. Never issue a new initiation POST after
an ambiguous start or after session expiry; stop for reconciliation instead. A PostgreSQL
advisory lock serializes the fixed test. No session URL, access token or secret in logs/API.

Verify the video belongs to the expected channel, is private, and processing succeeds.
No global spending/publishing flags or account approval changes are required for this
explicitly requested single private test. Public publishing remains disabled.

Primary contracts inspected:
- https://developers.google.com/youtube/data/reference/rest/v3/videos/insert
- https://developers.google.com/youtube/data/guides/using_resumable_upload_protocol
- https://developers.google.com/youtube/data/reference/rest/v3/videos

Reuse local Postman simulation, real HTTP, disposable PostgreSQL and synthetic media
to test success, partial acknowledgement, lost completion response, ambiguous initiation,
wrong channel, rejected grant, bad session URL, processing failure and changed-file replay.
Owner mock discovery remains unavailable due to the known local Postman Keychain issue;
build a contract-derived local stand-in. A passing simulation establishes caller behavior,
not live Google permission, upload acceptance or processing.
