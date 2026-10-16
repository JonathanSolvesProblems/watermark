#!/bin/bash
# Installs the judged demo as three systemd services on the watermark-demo instance:
# the API in read-only replay mode, the web app, and the ngrok tunnel on the public
# domain. Each restarts on failure and starts on boot. Usage: bash ec2_services.sh <domain>
set -euo pipefail
DOMAIN="$1"
APP=/home/ec2-user/watermark

sudo tee /etc/systemd/system/watermark-server.service >/dev/null <<EOF
[Unit]
Description=Watermark API (read-only replay of recorded Ring Playground runs)
After=network-online.target
[Service]
User=ec2-user
WorkingDirectory=$APP/server
Environment=MODE=playground
Environment=REPLAY=1
Environment=DATA_DIR=data/replay
Environment=BLOB_BACKEND=local
Environment=PUBLIC_BASE_URL=https://$DOMAIN
ExecStart=$APP/.venv/bin/python -m uvicorn watermark.main:app --host 127.0.0.1 --port 8765
Restart=always
RestartSec=5
[Install]
WantedBy=multi-user.target
EOF

sudo tee /etc/systemd/system/watermark-web.service >/dev/null <<EOF
[Unit]
Description=Watermark web app
After=watermark-server.service
[Service]
User=ec2-user
WorkingDirectory=$APP/web
Environment=NODE_ENV=production
Environment=PORT=3000
ExecStart=/usr/bin/npm start
Restart=always
RestartSec=5
[Install]
WantedBy=multi-user.target
EOF

sudo tee /etc/systemd/system/watermark-tunnel.service >/dev/null <<EOF
[Unit]
Description=Watermark public link (ngrok)
After=watermark-web.service network-online.target
[Service]
User=ec2-user
ExecStart=/usr/local/bin/ngrok http 3000 --url=$DOMAIN --log=stdout
Restart=always
RestartSec=5
[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now watermark-server watermark-web
# The tunnel is enabled but started only at cutover, once the laptop's agent is stopped:
# the domain can be served by one agent at a time.
sudo systemctl enable watermark-tunnel
systemctl is-active watermark-server watermark-web
