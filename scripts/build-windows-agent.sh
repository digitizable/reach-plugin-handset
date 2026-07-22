#!/usr/bin/env bash
# Windows agent binary from Linux — orchestration helper.
#
# PyInstaller does **not** cross-compile Linux→Windows natively. Supported paths:
#   1) GitHub Actions  windows-latest  (preferred CI) — see .github/workflows/windows-agent.yml
#   2) Wine + Windows Python + PyInstaller on this machine (optional)
#   3) Native Windows: agent/windows/build-windows.ps1
#
# Usage:
#   ./scripts/build-windows-agent.sh            # print plan + check tools
#   ./scripts/build-windows-agent.sh --wine     # attempt wine build if available
#   ./scripts/build-windows-agent.sh --ci-hint  # print gh workflow dispatch tip
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MODE="${1:-}"

echo "=== Hogwarts Windows agent build (from Linux) ==="
echo "Repo: $ROOT"
echo
echo "Truth: PyInstaller embeds the *host* Python runtime."
echo "  Cross-compile is Wine or a Windows runner — not a single Linux flag."
echo

have() { command -v "$1" >/dev/null 2>&1; }

case "$MODE" in
  --ci-hint|"")
    echo "Preferred CI:"
    echo "  git push  →  workflow 'Windows agent' builds hogwarts-agent.exe artifact"
    echo "  Or: gh workflow run windows-agent.yml"
    echo
    echo "Local Linux one-file (not .exe):"
    echo "  ./scripts/build-agent-linux.sh"
    echo
    echo "Native Windows (on a Win peer):"
    echo "  pwsh -File agent/windows/build-windows.ps1"
    if [[ "$MODE" == "--ci-hint" ]]; then
      exit 0
    fi
    ;;
esac

if [[ "$MODE" == "--wine" ]]; then
  if ! have wine && ! have wine64; then
    echo "Wine not installed. On Debian/Ubuntu:" >&2
    echo "  sudo apt install wine64 wine64-tools" >&2
    echo "Then install Windows Python under Wine and re-run." >&2
    exit 2
  fi
  WINE=$(command -v wine64 || command -v wine)
  echo "Using: $WINE"
  # Best-effort: expect Wine Python at a common path or PYTHON_WINE env
  PYWINE="${PYTHON_WINE:-}"
  if [[ -z "$PYWINE" ]]; then
    for c in \
      "$HOME/.wine/drive_c/Python312/python.exe" \
      "$HOME/.wine/drive_c/Python311/python.exe" \
      "$HOME/.wine/drive_c/Python310/python.exe"
    do
      if [[ -f "$c" ]]; then PYWINE=$c; break; fi
    done
  fi
  if [[ -z "${PYWINE:-}" ]]; then
    echo "No Windows Python found under Wine." >&2
    echo "Install Python 3.11+ (windows) into Wine, or set PYTHON_WINE=/path/to/python.exe" >&2
    exit 2
  fi
  OUT="$ROOT/dist/agent-windows"
  mkdir -p "$OUT"
  echo "Wine Python: $PYWINE"
  $WINE "$PYWINE" -m pip install -q pyinstaller
  $WINE "$PYWINE" -m PyInstaller \
    --onefile --clean --noconfirm \
    --name hogwarts-agent \
    --distpath "Z:$OUT" \
    --workpath "Z:$OUT/build" \
    --specpath "Z:$OUT" \
    "Z:$ROOT/agent/agent.py" || {
      # Wine path mapping varies — fall back to running from agent dir with wine cwd
      echo "Retrying with wine start /d …" >&2
      cd "$ROOT/agent"
      $WINE "$PYWINE" -m PyInstaller --onefile --name hogwarts-agent agent.py
      mkdir -p "$OUT"
      mv -f dist/hogwarts-agent.exe "$OUT/" 2>/dev/null || mv -f dist/hogwarts-agent "$OUT/" || true
    }
  echo "Artifacts under $OUT"
  ls -la "$OUT" || true
  exit 0
fi

echo "Tooling on this host:"
have python3 && python3 --version || echo "  python3: missing"
have wine64 && wine64 --version || have wine && wine --version || echo "  wine: missing (optional for --wine)"
have gh && gh --version | head -1 || echo "  gh: missing (optional for CI dispatch)"
echo
echo "Run with --wine or push to trigger GitHub Actions."
