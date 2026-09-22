#!/usr/bin/env bash
# Deploys the local Aleks/ tree to the VPS (alias: aleks-agent), installs
# main + dev dependencies, runs the test suite, and restarts the service.
#
# Rerun this instead of manually scp-ing individual files -- the dev deps
# step exists because the venv on the server silently drifted out of sync
# with pyproject.toml's dependency-groups.dev once already (2026-07-26),
# breaking `pytest` there until installed by hand.
set -euo pipefail

cd "$(dirname "$0")/.."
REMOTE_HOST="aleks-agent"
REMOTE_DIR="/root/projects/Aleks"
TARBALL="/tmp/aleks-agent-deploy.tar.gz"

echo "==> Packing local tree"
tar --exclude='.venv' --exclude='.git' --exclude='__pycache__' \
    --exclude='.pytest_cache' --exclude='.env' --exclude='state.db' \
    -czf "$TARBALL" .

echo "==> Uploading and extracting on $REMOTE_HOST"
scp "$TARBALL" "$REMOTE_HOST:/tmp/aleks-agent-deploy.tar.gz"
ssh "$REMOTE_HOST" "mkdir -p $REMOTE_DIR && tar -xzf /tmp/aleks-agent-deploy.tar.gz -C $REMOTE_DIR && rm /tmp/aleks-agent-deploy.tar.gz"
rm "$TARBALL"

echo "==> Installing dependencies (main + dev group) on $REMOTE_HOST"
ssh "$REMOTE_HOST" "cd $REMOTE_DIR && .venv/bin/python -m pip install --quiet -e . && .venv/bin/python -m pip install --quiet --group dev"

echo "==> Running test suite on $REMOTE_HOST"
ssh "$REMOTE_HOST" "cd $REMOTE_DIR && .venv/bin/python -m pytest -q"

echo "==> Restarting aleks-agent service"
ssh "$REMOTE_HOST" "systemctl restart aleks-agent && sleep 1 && systemctl status aleks-agent --no-pager -l | head -10"

echo "==> Done"
