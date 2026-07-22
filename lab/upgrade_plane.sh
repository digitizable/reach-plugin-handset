#!/usr/bin/env bash
# Upgrade the personal lab plane container to the current plane/server.py
# without wiping the SQLite fleet (preserves agents, packages, canaries).
#
# Usage:
#   ./lab/upgrade_plane.sh
#   PLANE_OPERATOR_TOKEN=dev ./lab/upgrade_plane.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

NET=hogwarts-lab
PLANE_IMG=hogwarts-plane:lab
TOKEN="${PLANE_OPERATOR_TOKEN:-dev}"
PLUGIN_DATA="${XDG_DATA_HOME:-$HOME/.local/share}/reach/plugin-data/com__digitizable__hogwarts"
PERSONAL="$PLUGIN_DATA/personal"
PLANE_DB_HOST="${PLANE_DB_HOST:-$PERSONAL/plane.db}"
HOST_PLANE="${HOST_PLANE:-http://127.0.0.1:8080}"

mkdir -p "$PERSONAL"

echo "==> export DB from running container (if any)"
if docker ps --format '{{.Names}}' | grep -qx hogwarts-plane; then
  if [ ! -s "$PLANE_DB_HOST" ]; then
    docker cp hogwarts-plane:/data/plane.db "$PLANE_DB_HOST"
    echo "    copied to $PLANE_DB_HOST"
  else
    # Prefer live container state
    docker cp hogwarts-plane:/data/plane.db "$PLANE_DB_HOST"
    echo "    refreshed $PLANE_DB_HOST from container"
  fi
elif [ ! -s "$PLANE_DB_HOST" ] && [ -f "$HOME/.local/share/hogwarts-plane/plane.db" ]; then
  cp -a "$HOME/.local/share/hogwarts-plane/plane.db" "$PLANE_DB_HOST"
  echo "    seeded from ~/.local/share/hogwarts-plane/plane.db"
fi

echo "==> build $PLANE_IMG"
docker build -t "$PLANE_IMG" -f lab/Dockerfile.plane . -q

echo "==> recreate plane with volume"
docker network create "$NET" >/dev/null 2>&1 || true
docker rm -f hogwarts-plane 2>/dev/null || true
# Ensure host file exists (docker will create a directory if missing path is wrong)
if [ ! -f "$PLANE_DB_HOST" ]; then
  touch "$PLANE_DB_HOST"
fi
docker run -d --name hogwarts-plane --network "$NET" \
  -e PLANE_OPERATOR_TOKEN="$TOKEN" \
  -e PLANE_HTTP_ADDR=0.0.0.0:8080 \
  -e PLANE_DB=/data/plane.db \
  -v "$PLANE_DB_HOST:/data/plane.db" \
  -p 8080:8080 \
  "$PLANE_IMG" >/dev/null

echo "==> wait for health"
for i in $(seq 1 40); do
  if curl -sf "$HOST_PLANE/api/v1/health" >/dev/null; then break; fi
  sleep 0.4
done
curl -sf "$HOST_PLANE/api/v1/health" | python3 -m json.tool
echo
echo "Plane upgraded. DB: $PLANE_DB_HOST"
echo "Re-attach mock agents if needed: re-run lab/personal_setup.sh (or restart agent containers)."
