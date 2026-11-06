# Owner login and YouTube OAuth contract

Target: https://studio.technoinno.live. Owner destination: @techno-inno,
channel ID UC8DbuevZRxVTWxltG9oDFRw (resolved from the public channel page).

Existing bearer access remains supported. Browser owner sessions are opaque random
tokens stored only as hashes in PostgreSQL, expire after eight hours, and use Secure,
HttpOnly, host-only, SameSite=Lax cookies. Cookie-authenticated writes require CSRF.
No admin password, token, Google code or refresh token is placed in application logs.

HTML form pages use `Referrer-Policy: strict-origin`: browsers retain the genuine
HTTPS `Origin` on native form submissions without sending paths or query strings
as referrers. The OAuth callback keeps `no-referrer` to suppress its code-bearing URL.
Origin checks remain exact; foreign and literal `null` origins are rejected, and
cookie-authenticated writes still require the CSRF token.

| Route | Access and behavior |
|---|---|
| GET / | Redirect to owner login |
| GET /login | Public owner login form, fresh anti-CSRF cookie and hidden field |
| GET /admin | Protected; unauthenticated HTML navigation redirects to /login; API/invalid Bearer requests still return 401 |
| POST /login | Verify login CSRF + admin password, create session, redirect to /admin |
| POST /logout | Owner + CSRF; delete session and expire cookie |
| POST /auth/youtube/start | Owner + CSRF; persist ten-minute state/PKCE intent, redirect to Google |
| GET /auth/youtube/callback | Requires the same owner session and matching unconsumed state; exchange code once and verify channel |
| GET /api/youtube/status | Protected connection metadata only; no credentials or implicit live calls |

New OAuth connections request upload + read-only + youtube.force-ssl scopes and
offline access, with include_granted_scopes=true. The edit scope is required by
videos.update for the owner-authorized multilingual/public update. Existing upload/read
grants remain usable until the owner personally grants this additional access. `login_hint`
suggests the intended email but does not establish ownership. The live authorized
`channels.list(mine=true)` result must include the configured unique channel ID.
Reject unexpected channels, missing requested scopes (including edit on reconnect),
missing refresh token, old
or replayed state, and cross-browser callbacks. Store token material only after those
checks, using authenticated encryption and an out-of-database key.

Callback failures leave no usable new credential. Existing credentials are preserved
if a reconnect fails. OAuth code exchange is never automatically retried after an
ambiguous failure. No upload occurs during connection. Social-account approval and
all automatic publishing/generation gates remain disabled. Connecting alone never
makes a video public; the fixed-video publication API is a separate explicit action.

Reference contracts: Google web-server OAuth and channels.list official documentation.
Testing separates local security tests, HTTP simulations, VPS deployment checks and
the final real consent flow. Only the owner may complete Google's consent screen.
