#!/bin/bash
set -e

APP_DIR="/opt/tradingalert"

# Ensure we are root
if [ "$EUID" -ne 0 ]; then 
  echo "Please run as root"
  exit 1
fi

echo "Installing system dependencies..."
apt-get update
# Check for python3-venv presence, install if missing
if ! dpkg -s python3-venv >/dev/null 2>&1; then
    apt-get install -y python3-venv
fi

echo "Stopping existing service..."
systemctl stop tradingalert || true

echo "Cleaning up previous installation..."
if [ -d "$APP_DIR" ]; then
    rm -rf "$APP_DIR"
fi

echo "Creating app directory at $APP_DIR..."
mkdir -p "$APP_DIR"

echo "Copying files..."
# Assumes script is run from the source directory containing the files
cp -r ./* "$APP_DIR/"

echo "Setting up virtual environment..."
cd "$APP_DIR"
python3 -m venv venv

echo "Installing Python requirements..."
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt

echo "Installing systemd service..."
cp tradingalert.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable tradingalert
systemctl restart tradingalert

echo "Installation complete."
echo "Service status:"
systemctl status tradingalert --no-pager
