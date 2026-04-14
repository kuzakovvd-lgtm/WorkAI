#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
  echo "Run as root (sudo)." >&2
  exit 1
fi

SSH_PORT="${SSH_PORT:-22}"
PERMIT_ROOT_LOGIN="${PERMIT_ROOT_LOGIN:-no}" # use 'prohibit-password' if passwordless root key login is required
API_UNIT_PATH="${API_UNIT_PATH:-/etc/systemd/system/workai-api.service}"
ALLOW_TCP_PORTS="${ALLOW_TCP_PORTS:-80 443}"

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Missing required command: $1" >&2
    exit 1
  }
}

need_cmd sed
need_cmd awk
need_cmd ss

export DEBIAN_FRONTEND=noninteractive

if command -v apt-get >/dev/null 2>&1; then
  apt-get update -y
  apt-get install -y --no-install-recommends fail2ban ufw
fi

if [[ -f /etc/ssh/sshd_config ]]; then
  cp /etc/ssh/sshd_config "/etc/ssh/sshd_config.bak.$(date +%Y%m%d%H%M%S)"

  if grep -qE '^\s*#?\s*PasswordAuthentication\s+' /etc/ssh/sshd_config; then
    sed -i -E 's/^\s*#?\s*PasswordAuthentication\s+.*/PasswordAuthentication no/' /etc/ssh/sshd_config
  else
    printf '\nPasswordAuthentication no\n' >> /etc/ssh/sshd_config
  fi

  if grep -qE '^\s*#?\s*PermitRootLogin\s+' /etc/ssh/sshd_config; then
    sed -i -E "s/^\s*#?\s*PermitRootLogin\s+.*/PermitRootLogin ${PERMIT_ROOT_LOGIN}/" /etc/ssh/sshd_config
  else
    printf '\nPermitRootLogin %s\n' "$PERMIT_ROOT_LOGIN" >> /etc/ssh/sshd_config
  fi

  if command -v sshd >/dev/null 2>&1; then
    sshd -t
  fi

  systemctl reload sshd 2>/dev/null || systemctl reload ssh 2>/dev/null || true
fi

mkdir -p /etc/fail2ban/jail.d
cat > /etc/fail2ban/jail.d/sshd.local <<'JAIL'
[sshd]
enabled = true
port = ssh
backend = systemd
findtime = 10m
maxretry = 5
bantime = 1h
JAIL

systemctl enable --now fail2ban
systemctl restart fail2ban

ufw --force reset
ufw default deny incoming
ufw default allow outgoing
ufw allow "${SSH_PORT}/tcp"

for p in ${ALLOW_TCP_PORTS}; do
  ufw allow "${p}/tcp"
done

# Explicitly close public API port.
ufw deny 8000/tcp
ufw --force enable

# Ensure API is not bound publicly when systemd unit exists.
if [[ -f "$API_UNIT_PATH" ]]; then
  cp "$API_UNIT_PATH" "${API_UNIT_PATH}.bak.$(date +%Y%m%d%H%M%S)"
  sed -i -E 's/(--host\s+)0\.0\.0\.0/\1127.0.0.1/' "$API_UNIT_PATH"
  systemctl daemon-reload
  systemctl restart "$(basename "$API_UNIT_PATH" .service)" || true
fi

# Disable cloudflared quick tunnel in production unless explicitly needed.
if systemctl list-unit-files | awk '{print $1}' | grep -qx 'cloudflared.service'; then
  systemctl disable --now cloudflared || true
fi

if pgrep -fa cloudflared >/dev/null 2>&1; then
  pkill -f 'cloudflared.*trycloudflare.com' || true
fi

echo
echo "Hardening summary"
echo "================"
echo "1) SSH settings:"
sshd -T 2>/dev/null | awk '/passwordauthentication|permitrootlogin/' || true
echo

echo "2) fail2ban:"
fail2ban-client status 2>/dev/null || true
fail2ban-client status sshd 2>/dev/null || true
echo

echo "3) Firewall:"
ufw status verbose || true
echo

echo "4) Port 8000 listeners:"
ss -ltnp | awk '$4 ~ /:8000$/ {print}' || true
