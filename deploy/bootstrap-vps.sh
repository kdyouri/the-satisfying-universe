#!/usr/bin/env bash
set -euo pipefail

# Run only on the owner-authorized fresh Ubuntu VPS, after inspecting existing services.
test "$(id -u)" -eq 0
. /etc/os-release
test "$ID" = ubuntu
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y --no-install-recommends ca-certificates curl nginx certbot
install -m 0755 -d /etc/apt/keyrings
if [ ! -f /etc/apt/keyrings/docker.asc ]; then
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
  chmod a+r /etc/apt/keyrings/docker.asc
fi
cat > /etc/apt/sources.list.d/docker.sources <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: ${UBUNTU_CODENAME}
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc
EOF
apt-get update -qq
apt-get install -y --no-install-recommends docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
systemctl enable --now docker
install -d -m 0700 /opt/technoinno
install -d -m 0755 /var/www/technoinno-acme
# Certificate issuance is intentionally separate: the owner must accept ACME terms.
docker version --format 'Docker server {{.Server.Version}}'
docker compose version --short
