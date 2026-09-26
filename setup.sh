#!/usr/bin/env bash
# System and Python dependencies for the Shorts factory (Debian/Ubuntu).
set -euo pipefail
cd "$(dirname "$0")"

sudo apt-get update
sudo apt-get install -y ffmpeg fonts-dejavu-core python3-venv

python3 -m venv .venv
.venv/bin/pip install --upgrade pip setuptools wheel
.venv/bin/pip install -r requirements.txt
