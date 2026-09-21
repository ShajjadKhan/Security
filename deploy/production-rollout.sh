#!/bin/bash
set -e

# ==============================================================================
# Antigravity Security Suite - Production Rollout & SSL Automation
# Target: Ubuntu Production Server (135.181.39.96)
# Domains: security.shajjadkhan.com, security.tawreedflow.com
# Port: 127.0.0.1:8001
# ==============================================================================

PROJECT_DIR="/home/shajjad/security_dept"
VENV_DIR="/home/shajjad/security_venv"
NGINX_AVAILABLE="/etc/nginx/sites-available/security"
NGINX_ENABLED="/etc/nginx/sites-enabled/security"
SYSTEMD_UNIT="/etc/systemd/system/security_dept.service"
ADMIN_EMAIL="shajjadkhan.me@gmail.com"

echo "========================================================"
echo "🚀 Deploying Antigravity Security Suite to Production..."
echo "========================================================"

cd "$PROJECT_DIR"
mkdir -p "$PROJECT_DIR/logs" "$PROJECT_DIR/media" "$PROJECT_DIR/staticfiles"

# 1. Gather static files
echo "📦 Collecting static files..."
"$VENV_DIR/bin/python" manage.py collectstatic --noinput

# 2. Verify database & migrations
echo "🗄️ Checking database migrations..."
"$VENV_DIR/bin/python" manage.py migrate --noinput

# 3. Install Systemd Service
echo "⚙️ Installing systemd service unit..."
sudo cp "$PROJECT_DIR/deploy/security_dept.service" "$SYSTEMD_UNIT"
sudo chmod 0644 "$SYSTEMD_UNIT"
sudo systemctl daemon-reload
sudo systemctl enable --now security_dept.service
sudo systemctl restart security_dept.service

# 4. Install Nginx Configuration
echo "🌐 Installing Nginx configuration..."
sudo cp "$PROJECT_DIR/deploy/nginx-security.conf" "$NGINX_AVAILABLE"
sudo chmod 0644 "$NGINX_AVAILABLE"
sudo ln -sf "$NGINX_AVAILABLE" "$NGINX_ENABLED"

echo "🔍 Validating Nginx configuration syntax..."
sudo nginx -t
sudo systemctl reload nginx

# 5. Provision SSL Certificates via Certbot
echo "🔒 Requesting / renewing SSL certificate for security.shajjadkhan.com & security.tawreedflow.com..."
if command -v certbot >/dev/null 2>&1; then
    sudo certbot --nginx \
        -d security.shajjadkhan.com \
        -d security.tawreedflow.com \
        --non-interactive \
        --agree-tos \
        --email "$ADMIN_EMAIL" \
        --redirect \
        --expand || echo "⚠️ Certbot completed with warnings. Nginx is serving on HTTP; retry SSL when ready."
    sudo systemctl reload nginx
else
    echo "⚠️ certbot not found. Skipping automatic SSL provisioning."
fi

# 6. Verify Service Status
echo "🩺 Verifying internal Gunicorn daemon (127.0.0.1:8001)..."
sleep 2
if curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8001/login/ | grep -E "200|302" >/dev/null; then
    echo "✅ Gunicorn daemon is healthy and responding on 127.0.0.1:8001"
else
    echo "⚠️ Warning: Gunicorn check did not return 200/302. Checking logs..."
    tail -n 25 "$PROJECT_DIR/logs/gunicorn_error.log" 2>/dev/null || true
fi

echo "========================================================"
echo "🎉 Deployment Complete!"
echo "Public URLs:"
echo "👉 https://security.shajjadkhan.com"
echo "👉 https://security.tawreedflow.com"
echo "========================================================"
