# Handset — Reach plugin

**C2-esque operator desk** for [Reach](https://github.com/digitizable/reach): path-aware reachback notes, quick egress probes, and agent package shortcuts.

> **Authorized use only** — your lab, contracts, and infrastructure you control.  
> Not a remote-access crime kit. Mechanisms for purple-team / restricted-network ops.

## Install

In Reach → **Plugins** marketplace:

```
digitizable/reach-plugin-handset
```

Or:

```bash
# via Reach plugin host
# owner/repo → Install from GitHub
```

Requires Reach ≥ 0.5 with plugin host (`reach-plugin.json` schema 1).

## Features

| Surface | Role |
|---------|------|
| Path status | Live Spectre hop summary + SOCKS URL |
| Listener notes | Accept host/port/face notes saved under plugin data |
| Egress probes | TCP reachability checks (direct + via path SOCKS when up) |
| Agent package | Open Reach reverse export folder |
| Playbook JSON | Export a simple session snapshot for ops notes |

## Manifest

See [Reach PLUGIN_SPEC](https://github.com/digitizable/reach/blob/main/docs/PLUGIN_SPEC.md).

## License

GPL-3.0-or-later
