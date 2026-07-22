#!/usr/bin/env bash
# Build hogwarts-agent one-file binary for the *current* Linux host (PyInstaller).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="${OUT_DIR:-$ROOT/dist/agent}"
NAME="${AGENT_NAME:-hogwarts-agent}"
mkdir -p "$OUT"
cd "$ROOT"

if ! command -v python3 >/dev/null; then
  echo "python3 required" >&2
  exit 1
fi

python3 -m pip install --user -q 'pyinstaller>=6.0' 2>/dev/null \
  || python3 -m pip install -q 'pyinstaller>=6.0'

python3 -m PyInstaller \
  --onefile \
  --clean \
  --noconfirm \
  --name "$NAME" \
  --distpath "$OUT" \
  --workpath "$OUT/build" \
  --specpath "$OUT" \
  "$ROOT/agent/agent.py"

echo "Built: $OUT/$NAME"
ls -la "$OUT/$NAME"
