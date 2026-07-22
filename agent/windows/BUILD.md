# Windows agent build

## Goal

One-file **`hogwarts-agent.exe`** for lab export / eng, plus **ffmpeg on PATH** for Keepstream 60 fps (`gdigrab` → MJPEG).

PyInstaller embeds the **host** interpreter. There is no supported pure-Linux “emit PE” flag.

| Where you are | How |
|---------------|-----|
| **Windows peer** | `pwsh -File agent/windows/build-windows.ps1` |
| **GitHub Actions** | workflow `windows-agent.yml` → artifact `hogwarts-agent.exe` |
| **Linux + Wine** | `./scripts/build-windows-agent.sh --wine` (optional; flaky) |
| **Linux only** | `./scripts/build-agent-linux.sh` → ELF, not `.exe` |

## Native Windows (preferred)

```powershell
cd <hogwarts-repo>
pwsh -File agent/windows/build-windows.ps1
# → dist\agent-windows\hogwarts-agent.exe
```

Requirements: Python 3.10+ on PATH (`py` launcher OK).

### Keepstream 60 fps

```powershell
winget install Gyan.FFmpeg
ffmpeg -version
# agent log should say: keepstream capture ffmpeg-gdigrab-mjpeg …
# without ffmpeg: pil-fallback (much slower)
```

## From Linux

```bash
# Plan + tool check
./scripts/build-windows-agent.sh

# Optional Wine attempt
./scripts/build-windows-agent.sh --wine

# Or trigger CI
gh workflow run windows-agent.yml
```

Prefer the **Windows Grok** peer or GH Actions over Wine for ship artifacts.

## Smoke

```text
hogwarts-agent.exe once -c agent.json
hogwarts-agent.exe loop -c agent.json
```

Desk: Agents → Desktop → Remote Viewer → Session / Keepstream.

Path SOCKS (Spike 2): Connect Reach path first; Session dial notes **via path SOCKS**.

## Related

- Elevated / silent helpers: `install-elevated-task.ps1`, `start-agent-silent.ps1`
- Privilege research: `privilege-engine/`
- Keepstream wire: Anguish notes `research/keepstream-v0`
