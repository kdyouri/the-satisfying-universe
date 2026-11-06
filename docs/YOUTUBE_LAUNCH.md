# YouTube-only launch handoff

Owner update: 2026-11-04. Initial destination: TechnoInno.

## Latest handoff — six-language publication, 2026-11-05

The owner authorized the next step: six-language metadata and public visibility for
the existing video qNsEQFHoMdk. English default; translations fr/es/it/ru/zh-CN
(Mandarin written in simplified Chinese). The publisher is installed, 98 regressions,
ten OAuth scenarios and 34 runtime checks pass. The owner personally completed Google
edit consent; the live update succeeded. All six localized reads, English default,
public visibility and absence of regional restrictions are verified. Public oEmbed
metadata is also accessible without login. No new upload, AI spend or scheduler activation.
Completion evidence: evidence/youtube-multilingual-public-live-2026-11-05.json.

## Current milestone — 2026-11-05

The first sonorized video was uploaded once through the installed API to @techno-inno,
privately with no subscriber notification. Google confirms private visibility, exact
channel, successful processing and HD:
https://www.youtube.com/watch?v=qNsEQFHoMdk. There are 85 passing regression tests and
27 passing installed runtime checks. Fixed-operation resumable upload/reconciliation
is implemented; public publishing and scheduled production remain disabled.

Next: the owner can watch the private result and choose whether to make that video
public. A reusable general publishing workflow, durable unattended OAuth setup and
off-host recovery remain future work before scheduled operation. New generation,
public visibility and recurring budgets each require their concrete authorization.
See evidence/youtube-private-upload-live-2026-11-05.json and YOUTUBE_UPLOAD_CONTRACT.md.
The sections below retain the initial installation handoff, before production/upload.

## Confirmed by owner

Google account: admin.technoinno@gmail.com. YouTube channel: TechnoInno, @techno-inno.
Owner confirmed OAuth type Web application and authorized root SSH at 203.161.61.3.
Deployment host: https://studio.technoinno.live. Instagram and TikTok are paused.
The project folder keeps its existing internal name; no public channel rename is planned.

## Installed and verified

Docker/Compose, Nginx and Certbot are installed at root@203.161.61.3. The release is
at /opt/technoinno with a separate root-only environment. API, PostgreSQL and Redis
are healthy. The application image built and all 25 installed runtime checks passed.
The exact Google callback and PKCE URL construction passed without contacting Google.
The owner subsequently granted Google consent; the encrypted grant, exact channel,
live refresh and authorized channel read are now verified. No paid request or upload
has been performed. See evidence/youtube-live-connection-2026-11-04.json.

Both authoritative servers and Google/Cloudflare resolve studio to 203.161.61.3.
The external ACME route returns 200. The owner personally accepted the certificate
agreement and authorized issuance. HTTPS is active, the certificate expires 2027-02-02,
and the same 25 checks pass over external TLS. Renewal with the reload hook passed a
dry run. Plain HTTP redirects to HTTPS. This Mac still caches an earlier DNS failure in
its system HTTP resolver; TLS checks retained normal hostname/certificate validation
while routing to the verified IP. Public DNS needs no further edit.

## Next steps

1. Hosting, certificate and Google channel connection are complete. Real token refresh
   and authorized channel reads pass. Do not repeat account/credential setup.
2. Implement the generation/quality pipeline using the configured economic candidates:
   Gemma 4 26B A4B, Gemini 3.1 Flash Lite, Veo 3.1 Lite. Refresh exact quotes before
   a paid request. The cheaper pilot is proposed in COST_ESTIMATE.md; obtain its
   explicit cap after adapters are ready. Credit purchases do not set that budget.
3. Implement resumable upload and processing/reconciliation. A private test requires
   authorization for the concrete video; public publishing remains disabled.
4. Address Google Testing-mode seven-day grant expiry before unattended operation,
   using the appropriate production/personal-use setup. Verify off-host backups/recovery.
5. After reviewed outputs and recovery tests, enable only the separately authorized
   daily budget and two YouTube Shorts/day schedule.

## Primary references

[YouTube authorization](https://developers.google.com/youtube/data/guides/authentication)
distinguishes public-data API keys from OAuth required for uploads and private data.
[Google web-server OAuth](https://developers.google.com/identity/protocols/oauth2/web-server)
documents web clients, exact redirects, owner consent and offline refresh-token access.
Neither credential presence nor a public domain proves that these steps are complete.
