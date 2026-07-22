# Hogwarts input provider (Windows)

**High integrity** helper for Keepstream / Control inject when the agent is Medium IL.

Not a UAC bypass. Install once elevated; daily start is silent via Task Scheduler.

## Why

UIPI blocks Medium agents from injecting into Task Manager and other High UI. Either:

1. Elevate the **whole agent** (`..\install-elevated-task.ps1`), or  
2. Keep the agent Medium and run **this** High helper; agent forwards INPUT over a named pipe.

## One-time install (one UAC Yes)

**Use a path with no spaces.** WinPS 5.1 `-File` breaks under profiles like `C:\Users\Paul Beck\…`. Recommended:

```powershell
mkdir C:\HogwartsInputProvider -Force
copy <repo>\agent\windows\input-provider\* C:\HogwartsInputProvider\
cd C:\HogwartsInputProvider
# elevated once:
.\install-input-provider-task.ps1 -AtLogon
.\start-input-provider-silent.ps1
```

If the repo path has no spaces you can install in-tree instead.

Scripts are **ASCII-only** (avoid en-dashes in comments on WinPS 5.1).

## agent.json

```json
"input_provider": {
  "enabled": true,
  "kind": "pipe",
  "pipe": "\\\\.\\pipe\\hogwarts-input"
}
```

Requires agent **≥ 0.5.32-lab** for best native `kind=pipe` (CreateFile **WRITE then R|W**). Helper server is **In**-only.

**Supported / recommended on flaky hosts:** `kind=exec` + `pipe-bridge.ps1` (.NET `NamedPipeClientStream` forwarder) — proven green on DESKTOP-50LV16L while native pipe was unstable:

```json
"input_provider": {
  "enabled": true,
  "kind": "exec",
  "command": "powershell.exe",
  "args": [
    "-NoProfile", "-ExecutionPolicy", "Bypass",
    "-File", "C:\\HogwartsInputProvider\\pipe-bridge.ps1"
  ]
}
```

Helper process must still be listening on `\\.\pipe\hogwarts-input`.

Or Remote Viewer → Session → **Use provider** / **Default pipe**.

## Protocol

`hogwarts-input/1` (see CONTRACT / research notes):

```
Agent → Helper:  HELLO hogwarts-input/1 <session_id> <psk>\n
Helper → Agent:  HELLO_OK\n
Agent → Helper:  {"events":[{"type":"click","fx":0.5,"fy":0.5},…]}\n
Agent → Helper:  BYE\n
```

## Verify

```powershell
schtasks /Run /TN "HogwartsInputProvider"
Start-Sleep 2
$c = New-Object System.IO.Pipes.NamedPipeClientStream(".", "hogwarts-input", [IO.Pipes.PipeDirection]::Out)
$c.Connect(3000); $c.Dispose(); "pipe OK"
```

1. Helper running (task or `powershell -File HogwartsInputProvider.ps1`).  
2. Agent online; `session_start` includes `"input_provider":{"active":true,"kind":"pipe",…}`.  
3. Control / Session click on Task Manager should work if helper is **Highest** IL.

## Anti-patterns

| Action | Result |
|--------|--------|
| Point `exec` at a self-elevating script | UAC every Session |
| Helper not running when Session starts | provider connect fails → local inject |
| Install under a path with spaces | Task `-File` split; helper never listens |
| Agent already elevated | provider optional; local SendInput can hit High UI |
| Rely on CPython `open()` only (pre-0.5.30) | ENOENT while .NET Connect works |
