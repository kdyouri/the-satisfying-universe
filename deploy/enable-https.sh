#!/usr/bin/env bash
# Run only after the owner has personally accepted the CA terms and a certificate exists.
set -euo pipefail
test "$(id -u)" -eq 0
cd /opt/technoinno
certificate=/etc/letsencrypt/live/studio.technoinno.live/fullchain.pem
test -s "$certificate"
test -s /etc/letsencrypt/live/studio.technoinno.live/privkey.pem
openssl x509 -in "$certificate" -noout -checkhost studio.technoinno.live
openssl x509 -in "$certificate" -noout -checkend 604800

site=/etc/nginx/sites-available/technoinno-studio
cp -a "$site" deploy/nginx-studio.before-https
install -m 0644 deploy/studio-https.conf "$site"
if ! nginx -t; then
  cp -a deploy/nginx-studio.before-https "$site"
  exit 1
fi
if ! systemctl reload nginx; then
  cp -a deploy/nginx-studio.before-https "$site"
  nginx -t
  systemctl reload nginx
  exit 1
fi

install -d -m 0755 /etc/letsencrypt/renewal-hooks/deploy
cat > /etc/letsencrypt/renewal-hooks/deploy/technoinno-reload-nginx <<'HOOK'
#!/bin/sh
set -eu
/usr/sbin/nginx -t
/bin/systemctl reload nginx
HOOK
chmod 0755 /etc/letsencrypt/renewal-hooks/deploy/technoinno-reload-nginx
systemctl enable --now certbot.timer
curl --retry 3 --retry-connrefused --retry-delay 1 --connect-timeout 5 --max-time 15 \
  --resolve studio.technoinno.live:443:127.0.0.1 -fsS \
  https://studio.technoinno.live/health/live
