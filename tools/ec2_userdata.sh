#!/bin/bash
# First-boot setup for the watermark-demo instance: swap for the Next.js build on 2 GB,
# Python, Node, git and the ngrok agent. The app itself is deployed over SSH afterwards.
set -euxo pipefail
fallocate -l 2G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab
dnf install -y git python3.11 python3.11-pip nodejs npm tar
curl -sSL https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-arm64.tgz | tar xz -C /usr/local/bin
touch /var/tmp/userdata-done
