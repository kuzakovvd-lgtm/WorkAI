#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
  echo "Run as root (sudo)." >&2
  exit 1
fi

PROJECT_DIR="${WORKAI_PROJECT_DIR:-/opt/workai}"
NGINX_CONF_SRC="${NGINX_CONF_SRC:-$PROJECT_DIR/deploy/nginx/workai.conf}"
NGINX_SITE_NAME="${NGINX_SITE_NAME:-workai.conf}"

if [[ ! -f "$NGINX_CONF_SRC" ]]; then
  echo "Missing nginx config template: $NGINX_CONF_SRC" >&2
  exit 2
fi

export DEBIAN_FRONTEND=noninteractive
if command -v apt-get >/dev/null 2>&1; then
  apt-get update -y
  apt-get install -y --no-install-recommends nginx
fi

install -m 0644 "$NGINX_CONF_SRC" "/etc/nginx/sites-available/$NGINX_SITE_NAME"
ln -sfn "/etc/nginx/sites-available/$NGINX_SITE_NAME" "/etc/nginx/sites-enabled/$NGINX_SITE_NAME"
rm -f /etc/nginx/sites-enabled/default

nginx -t
systemctl enable --now nginx
systemctl reload nginx

echo "nginx reverse proxy is active."
echo "Next step for TLS: certbot --nginx -d <your-domain>"
