#!/bin/bash
set -e

APP_DIR="/opt/tradingalert"
DOMAIN="crypto.aralbruehl.de"
EMAIL="info@aralbruehl.de"

# Ensure we are root
if [ "$EUID" -ne 0 ]; then 
  echo "Please run as root"
  exit 1
fi

echo "Stopping existing service..."
systemctl stop tradingalert || true

echo "Installing system dependencies..."
apt-get update
# Install Nginx, Certbot, and Python venv
apt-get install -y python3-venv nginx certbot python3-certbot-nginx

echo "Cleaning up previous installation (preserving state if possible)..."
# We might want to preserve state.json if it exists, to avoid losing historical data/assets
if [ -f "$APP_DIR/state.json" ]; then
    echo "Backing up state.json..."
    cp "$APP_DIR/state.json" /tmp/tradingalert_state.json
fi

if [ -d "$APP_DIR" ]; then
    rm -rf "$APP_DIR"
fi

echo "Creating app directory at $APP_DIR..."
mkdir -p "$APP_DIR"

echo "Copying files..."
cp -r ./* "$APP_DIR/"

# Restore state
if [ -f "/tmp/tradingalert_state.json" ]; then
    echo "Restoring state.json..."
    mv /tmp/tradingalert_state.json "$APP_DIR/state.json"
fi

echo "Setting up virtual environment..."
cd "$APP_DIR"
python3 -m venv venv

echo "Installing Python requirements..."
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt

echo "Configuring Nginx..."
# Copy nginx config
cp nginx_app.conf /etc/nginx/sites-available/$DOMAIN
# Remove default if exists (optional, might conflict)
rm -f /etc/nginx/sites-enabled/default

# Enable site
ln -sf /etc/nginx/sites-available/$DOMAIN /etc/nginx/sites-enabled/

# Test Nginx config
nginx -t

# Reload Nginx
systemctl reload nginx

echo "Obtaining SSL Certificate..."
# Run certbot non-interactively
# --nginx: use nginx plugin
# --non-interactive: don't ask questions
# --agree-tos: agree to terms
# -m: email
# -d: domain
certbot --nginx --non-interactive --agree-tos -m $EMAIL -d $DOMAIN || echo "Certbot failed, please run manually: certbot --nginx -d $DOMAIN"

echo "Installing systemd service..."
# Check if service file needs update (it executes gunicorn now)
# We need to make sure tradingalert.service in the repo is updated too!
# Updating it right here via cat if not already updated in source
cat > /etc/systemd/system/tradingalert.service <<EOF
[Unit]
Description=Trading Alert Web Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$APP_DIR
# bind to localhost:5000, Nginx proxies to it
ExecStart=$APP_DIR/venv/bin/gunicorn --workers 1 --bind 127.0.0.1:5000 "webapp:create_app()"
Restart=always
RestartSec=60
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable tradingalert
systemctl restart tradingalert

echo "Installation complete."
echo "Service status:"
systemctl status tradingalert --no-pager
