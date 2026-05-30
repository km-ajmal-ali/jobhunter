#!/usr/bin/env bash
# =============================================================================
# VPS Setup Script for JobHunter
#
# Run this ONCE on a fresh VPS to install Docker, Docker Compose,
# and prepare the deployment directory.
#
# Usage:
#   ssh root@your-server-ip
#   curl -fsSL https://raw.githubusercontent.com/YOUR_USER/jobhunter/main/scripts/setup-vps.sh | bash
#
# Or download and run manually:
#   bash scripts/setup-vps.sh
# =============================================================================

set -euo pipefail

echo "🚀 JobHunter VPS Setup"
echo "======================"

# ── 1. System updates ─────────────────────────────────────────────────
echo "[1/6] Updating system packages..."
apt-get update -qq
apt-get upgrade -y -qq

# ── 2. Install Docker ────────────────────────────────────────────────
echo "[2/6] Installing Docker..."
if ! command -v docker &>/dev/null; then
  curl -fsSL https://get.docker.com | bash
  systemctl enable docker
  systemctl start docker
  echo "  Docker installed: $(docker --version)"
else
  echo "  Docker already installed: $(docker --version)"
fi

# ── 3. Install Docker Compose plugin ─────────────────────────────────
echo "[3/6] Installing Docker Compose..."
if ! docker compose version &>/dev/null; then
  apt-get install -y -qq docker-compose-plugin
  echo "  Docker Compose installed: $(docker compose version)"
else
  echo "  Docker Compose already installed: $(docker compose version)"
fi

# ── 4. Create deployment directory ───────────────────────────────────
echo "[4/6] Creating deployment directory..."
mkdir -p /opt/jobhunter
cd /opt/jobhunter

# ── 5. Create .env file (placeholder) ────────────────────────────────
echo "[5/6] Creating .env file..."
if [ ! -f .env ]; then
  cat > .env << 'EOF'
# JobHunter Environment Configuration
# Edit this file with your production values
DB_USER=jobuser
DB_PASSWORD=$(openssl rand -base64 32)
DB_NAME=jobhunter
DEBUG=false
CORS_ORIGINS=http://localhost
GHCR_OWNER=your-github-username
EOF
  echo "  .env file created. Edit it with: nano /opt/jobhunter/.env"
else
  echo "  .env already exists"
fi

# ── 6. Download docker-compose.yml ───────────────────────────────────
echo "[6/6] Downloading docker-compose.yml..."
if [ ! -f docker-compose.yml ]; then
  cat > docker-compose.yml << 'EOF'
version: "3.9"
services:
  db:
    image: postgres:16-alpine
    container_name: jobhunter-db
    restart: unless-stopped
    volumes:
      - pgdata:/var/lib/postgresql/data
    env_file: .env
    environment:
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: ${DB_NAME}
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER} -d ${DB_NAME}"]
      interval: 10s
      timeout: 5s
      retries: 5

  backend:
    image: ghcr.io/${GHCR_OWNER}/jobhunter-backend:latest
    container_name: jobhunter-backend
    restart: unless-stopped
    depends_on:
      db:
        condition: service_healthy
    env_file: .env
    environment:
      DATABASE_URL: postgresql+asyncpg://${DB_USER}:${DB_PASSWORD}@db:5432/${DB_NAME}

  frontend:
    image: ghcr.io/${GHCR_OWNER}/jobhunter-frontend:latest
    container_name: jobhunter-frontend
    restart: unless-stopped
    depends_on:
      - backend
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - /etc/letsencrypt:/etc/letsencrypt:ro

volumes:
  pgdata:
    driver: local
EOF
  echo "  docker-compose.yml created"
else
  echo "  docker-compose.yml already exists"
fi

# ── Done ──────────────────────────────────────────────────────────────
echo ""
echo "✅ VPS setup complete!"
echo ""
echo "Next steps:"
echo "  1. Edit /opt/jobhunter/.env with your actual values"
echo "  2. Set up GitHub secrets in your repo:"
echo "     - GHCR_TOKEN (GitHub PAT with write:packages)"
echo "     - SSH_PRIVATE_KEY (your VPS private key)"
echo "     - SSH_HOST (your VPS IP)"
echo "     - SSH_USER (root)"
echo "  3. Push to main branch → auto-deploys via GitHub Actions"
echo "  4. To deploy manually:"
echo "     docker login ghcr.io"
echo "     docker compose pull"
echo "     docker compose up -d"
echo "     docker compose exec backend alembic upgrade head"
echo ""
