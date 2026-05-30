#!/usr/bin/env bash
# =============================================================================
# Domain Setup Script for JobHunter
#
# Run this AFTER you have bought a domain and pointed its DNS A record
# to your VPS IP address.
#
# This script:
#   1. Updates the Nginx config with your domain
#   2. Obtains SSL certificates via Let's Encrypt (Certbot)
#   3. Reloads Nginx with HTTPS enabled
#
# Usage:
#   bash scripts/deploy-domain.sh your-domain.com
#
# Example:
#   bash scripts/deploy-domain.sh jobhunter.example.com
# =============================================================================

set -euo pipefail

# ── Validate arguments ──────────────────────────────────────────────
if [ $# -lt 1 ]; then
  echo "❌ Usage: $0 your-domain.com"
  echo "   Example: $0 jobhunter.example.com"
  exit 1
fi

DOMAIN="$1"
NGINX_CONF="/opt/jobhunter/nginx/nginx.conf"

echo "🌐 Setting up domain: $DOMAIN"
echo "=============================="

# ── 1. Verify DNS resolution ────────────────────────────────────────
echo "[1/5] Checking DNS resolution..."
SERVER_IP=$(curl -fsSL ifconfig.me 2>/dev/null || curl -fsSL icanhazip.com 2>/dev/null)
DOMAIN_IP=$(dig +short "$DOMAIN" 2>/dev/null || host "$DOMAIN" 2>/dev/null | grep -oE '[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+' | head -1 || echo "")

if [ -z "$DOMAIN_IP" ]; then
  echo "  ⚠️  Could not resolve $DOMAIN. Make sure the DNS A record points to your server."
  echo "  Expected: $SERVER_IP"
  echo "  Continuing anyway (Certbot will validate)..."
elif [ "$DOMAIN_IP" != "$SERVER_IP" ]; then
  echo "  ⚠️  $DOMAIN resolves to $DOMAIN_IP, but this server is $SERVER_IP"
  echo "  Update your DNS A record to point to $SERVER_IP"
  echo "  Continuing anyway (may fail)..."
else
  echo "  ✅ DNS resolves correctly to $SERVER_IP"
fi

# ── 2. Install Certbot ──────────────────────────────────────────────
echo "[2/5] Installing Certbot..."
if ! command -v certbot &>/dev/null; then
  apt-get update -qq
  apt-get install -y -qq certbot python3-certbot-nginx
  echo "  Certbot installed"
else
  echo "  Certbot already installed: $(certbot --version)"
fi

# ── 3. Update Nginx config with domain ──────────────────────────────
echo "[3/5] Updating Nginx config..."
if [ -f "$NGINX_CONF" ]; then
  # Replace server_name _ with the actual domain
  sed -i "s/server_name _;/server_name $DOMAIN;/g" "$NGINX_CONF"
  echo "  Nginx config updated with domain: $DOMAIN"
else
  echo "  ⚠️  Nginx config not found at $NGINX_CONF"
  echo "  Make sure the deployment directory exists."
fi

# ── 4. Obtain SSL certificate ───────────────────────────────────────
echo "[4/5] Obtaining SSL certificate..."
# Stop frontend container temporarily so Certbot can bind port 80
docker compose -f /opt/jobhunter/docker-compose.yml stop frontend 2>/dev/null || true

certbot --nginx \
  --domain "$DOMAIN" \
  --non-interactive \
  --agree-tos \
  --email "admin@$DOMAIN" \
  --redirect \
  --keep-until-expiring

# Restart frontend
docker compose -f /opt/jobhunter/docker-compose.yml up -d frontend

echo "  ✅ SSL certificate obtained for $DOMAIN"

# ── 5. Set up auto-renewal ──────────────────────────────────────────
echo "[5/5] Setting up auto-renewal..."
# Certbot installs a systemd timer by default
systemctl enable certbot.timer 2>/dev/null || true
systemctl start certbot.timer 2>/dev/null || true

echo ""
echo "✅ Domain setup complete!"
echo ""
echo "Your site should now be accessible at:"
echo "  https://$DOMAIN"
echo ""
echo "Auto-renewal is configured via systemd timer."
echo "To test renewal manually: certbot renew --dry-run"
echo ""
