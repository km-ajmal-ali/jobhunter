#!/usr/bin/env bash
# =============================================================================
# Domain Setup Script for JobHunter
#
# Run this AFTER you have bought a domain and pointed its DNS A record
# to your VPS IP address.
#
# This script:
#   1. Verifies DNS resolves to this server
#   2. Installs Certbot
#   3. Stops frontend container, obtains SSL cert via standalone mode
#   4. Creates an SSL nginx config and updates docker-compose.yml
#   5. Restarts frontend with HTTPS enabled
#   6. Sets up auto-renewal
#
# Usage:
#   bash scripts/deploy-domain.sh your-domain.com
# =============================================================================

set -euo pipefail

DOMAIN="$1"

NGINX_DIR="/opt/jobhunter/nginx"
SSL_CONF="$NGINX_DIR/ssl-nginx.conf"
COMPOSE_FILE="/opt/jobhunter/docker-compose.yml"

echo "Setting up domain: $DOMAIN"
echo "=============================="

# ── 1. Verify DNS resolution ────────────────────────────────────────
echo "[1/6] Checking DNS resolution..."
SERVER_IP=$(curl -fsSL ifconfig.me 2>/dev/null || curl -fsSL icanhazip.com 2>/dev/null)
DOMAIN_IP=$(dig +short "$DOMAIN" 2>/dev/null || host "$DOMAIN" 2>/dev/null | grep -oE '[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+' | head -1 || echo "")
if [ -z "$DOMAIN_IP" ]; then
  echo "  Could not resolve $DOMAIN. Make sure the DNS A record points to this server."
  echo "  Expected: $SERVER_IP — continuing anyway..."
elif [ "$DOMAIN_IP" != "$SERVER_IP" ]; then
  echo "  $DOMAIN resolves to $DOMAIN_IP, but this server is $SERVER_IP"
  echo "  Update your DNS A record to point to $SERVER_IP"
  exit 1
else
  echo "  DNS resolves correctly to $SERVER_IP"
fi

# ── 2. Install Certbot ──────────────────────────────────────────────
echo "[2/6] Installing Certbot..."
if ! command -v certbot &>/dev/null; then
  apt-get update -qq
  apt-get install -y -qq certbot
fi
echo "  Certbot ready: $(certbot --version 2>/dev/null)"

# ── 3. Stop frontend, get SSL cert ─────────────────────────────────
echo "[3/6] Obtaining SSL certificate (this validates domain ownership)..."
docker compose -f "$COMPOSE_FILE" stop frontend 2>/dev/null || true

certbot certonly --standalone \
  --domain "$DOMAIN" \
  --non-interactive \
  --agree-tos \
  --email "admin@$DOMAIN" \
  --keep-until-expiring

echo "  Certificate obtained"

# ── 4. Create SSL nginx config ──────────────────────────────────────
echo "[4/6] Creating SSL nginx config..."
mkdir -p "$NGINX_DIR"

cat > "$SSL_CONF" <<NGINXEOF
upstream backend {
    server backend:8000;
}

server {
    listen 443 ssl http2;
    server_name $DOMAIN;

    ssl_certificate /etc/letsencrypt/live/$DOMAIN/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/$DOMAIN/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    root /usr/share/nginx/html;
    index index.html;

    location /assets/ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    location / {
        try_files \$uri \$uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_connect_timeout 60s;
        proxy_read_timeout 60s;
        proxy_send_timeout 60s;
    }

    location /health {
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
    }

    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml text/javascript image/svg+xml;
    gzip_min_length 1000;
    gzip_comp_level 6;

    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
}

server {
    listen 80;
    server_name $DOMAIN;
    return 301 https://\$server_name\$request_uri;
}
NGINXEOF

echo "  SSL nginx config created at $SSL_CONF"

# ── 5. Update docker-compose.yml ────────────────────────────────────
echo "[5/6] Updating docker-compose.yml for HTTPS..."
# Add port 443 under frontend.ports if not present
if ! grep -q '"0.0.0.0:443:443"' "$COMPOSE_FILE"; then
  sed -i '/- "0.0.0.0:80:80"/a\      - "0.0.0.0:443:443"' "$COMPOSE_FILE"
  echo "  Port 443 added"
fi
# Add volumes under frontend (after the ports block)
if ! grep -q 'letsencrypt' "$COMPOSE_FILE"; then
  sed -i '/- "0.0.0.0:443:443"/a\    volumes:\n      - /etc/letsencrypt:/etc/letsencrypt:ro\n      - /opt/jobhunter/nginx/ssl-nginx.conf:/etc/nginx/conf.d/default.conf:ro' "$COMPOSE_FILE"
  echo "  Volume mounts added"
fi

# ── 6. Restart frontend with HTTPS ──────────────────────────────────
echo "[6/6] Restarting frontend with HTTPS..."
docker compose -f "$COMPOSE_FILE" up -d frontend

echo ""
echo "Domain setup complete!"
echo "  https://$DOMAIN"
echo ""
echo "Auto-renewal is configured via certbot timer."
echo "To test: sudo certbot renew --dry-run"
echo ""
echo "NOTE: If you later rebuild the frontend Docker image,"
echo "the baked-in nginx.conf only has HTTP. This script's"
echo "override at $SSL_CONF is what enables HTTPS."
echo "Re-run this script if you need to re-apply after rebuilds."
