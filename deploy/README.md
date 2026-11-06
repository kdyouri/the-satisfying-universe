# Owner-authorized VPS deployment

Verified server: root@203.161.61.3, Ubuntu 24.04.5, one CPU, about 1 GB RAM,
20 GB disk with 16 GB free. Inspection found only SSH listening; no Docker/web server.
Host: studio.technoinno.live. Authoritative DNS now points both studio and the root
domain to this VPS; this deployment makes no DNS changes.

Automatic approval review rejected the bootstrap invocation because installing packages
and enabling services are persistent root-level changes with network exposure. No bootstrap
commands ran at that time. On 2026-11-04 the owner explicitly instructed:
"now, please go for install over ssh". This authorizes the reviewed installation
and deployment below. Certificate terms and Google consent remain owner actions.

## Reviewable change set

- Install free Docker Engine/Compose from Docker's official Ubuntu repository and
  Ubuntu's Nginx/Certbot packages. Enable Docker and the web server. No subscriptions.
- Install this app under /opt/technoinno, keeping SSH configuration unchanged.
- Transfer only the app's required credentials through encrypted SSH and store the
  server environment file with owner-only permissions; no credentials in logs or Git.
- Start PostgreSQL, Redis and the API in containers. Only the API binds a loopback
  port. PostgreSQL/Redis remain private. Worker/scheduler stay off during onboarding.
- Expose HTTP port 80 for certificate validation and HTTPS port 443 for the password-
  protected studio. No change to the main domain or any YouTube content.
- Keep all paid generation, public publishing and scheduled production disabled.

Files: bootstrap-vps.sh, studio-http.conf, studio-https.conf, ../compose.vps.yaml.
Application code and migrations are included in the prepared release archive.

## Execution procedure (installation and HTTPS completed)

1. Run bootstrap-vps.sh. Copy code and protected runtime configuration to the server.
2. Validate merged Compose config; build the image and start the API/dependencies.
3. Apply the ACME-only HTTP config. Verify the challenge route and DNS.
4. Owner accepts the certificate provider's terms personally using the prepared
   interactive command below. Do not add automated agreement flags without explicit
   owner acceptance. The owner accepted the agreement in chat and issuance completed.
5. Apply HTTPS config, check Nginx syntax, enable certificate renewal reload hook,
   then verify HTTPS, login, protected API and absence of public DB/Redis ports.
6. Owner adds the exact Google OAuth redirect
   `https://studio.technoinno.live/auth/youtube/callback` and personally grants consent
   through the studio. If the Google app is in testing, add the owner as a test user.

The bootstrap completed on 2026-11-04: Docker 29.9.3, Compose 5.7.0, Nginx and
Certbot are installed. Code and a separate root-only environment file were transferred
via SSH. The image build, migration and startup succeeded. API, PostgreSQL and Redis are
healthy; all 25 installed runtime checks passed. Worker/Beat remain off. Authoritative and Google/Cloudflare DNS
checks pass. The public ACME route returns 200. After the owner's personal agreement acceptance,
the certificate was issued (expires 2027-02-02), HTTPS enabled and all 25 external TLS
runtime checks passed. Automatic renewal and the Nginx reload hook passed a Certbot
dry run. Plain HTTP now redirects to HTTPS.

Local tests alone do not establish a live Google grant, upload or paid generation.

Interactive certificate command, retained for operations reference (issuance completed):

```sh
certbot certonly --webroot -w /var/www/technoinno-acme -d studio.technoinno.live --email admin.technoinno@gmail.com
```


After certificate issuance, run `bash deploy/enable-https.sh` from `/opt/technoinno`.
It validates the certificate hostname/expiry, checks Nginx configuration before reload,
and enables the certificate timer with a reload hook. It does not issue a certificate
or accept terms.

Runtime verification from `/opt/technoinno`:

```sh
docker compose -f compose.yaml -f compose.vps.yaml exec -T api python - < deploy/verify-runtime.py
```

The verifier uses the actual deployed HTTP API and owner configuration without printing
secrets. It checks authentication, CSRF, migrations, zero spending caps, disabled work,
and the Google redirect/PKCE construction. It creates then logs out a temporary owner
session, cleaning its OAuth state. It does not contact Google or generate/upload videos.
