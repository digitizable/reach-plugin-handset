# Malbork

<p align="center">
  <img src="icon.svg" alt="Malbork" width="128" height="128"/>
</p>

<p align="center">
  <strong>C2 for Reach</strong> — a well-defended operator desk.<br/>
  Named for <a href="https://en.wikipedia.org/wiki/Malbork_Castle">Malbork Castle</a> (Marienburg), the Teutonic Order’s brick fortress — largest of its kind in Europe.
</p>

<p align="center">
  channel · agents · plane · reverse · egress · playbooks
</p>

**Malbork** is the command-and-control plugin for [Reach](https://github.com/digitizable/reach): path-aware channel status, implant roster against your control plane, reverse listener notes, egress probing (direct vs SOCKS path), interactive console, and session playbooks.

Formerly **Handset** — same role, castle-grade name and mark.

## Install

In Reach → **Plugins** marketplace:

```text
digitizable/reach-plugin-malbork
```

If the GitHub repo still uses the old path, `digitizable/reach-plugin-malbork` may redirect until renamed.

Requires Reach ≥ 0.5 (plugin host, `reach-plugin.json` schema 1).

### Local dev

```bash
rsync -a --delete \
  --exclude .git --exclude __pycache__ \
  ./ ~/.local/share/reach/plugins/com__digitizable__malbork/
```

Restart Reach (or re-open the Malbork page) after changes. Disable/remove the old `com.digitizable.handset` install if both appear.

## Features

| Panel | What |
|-------|------|
| **Channel** | Live path hero, SOCKS / hops / fingerprint / plane |
| **Agents** | Fleet roster from `GET /api/v1/agents` |
| **Listener** | Accept host/port, transport, cover face, ops notes |
| **Egress** | TCP matrix direct vs path SOCKS |
| **Console** | Ops shell + ASCII keep splash |
| **Plane** | Control-plane URL + token + health |
| **Ops kit** | Reverse export, playbook JSON, data dir |
| **Session log** | Local activity trail |

## Control plane

Malbork does **not** host implants. Point **Plane** at your API:

| Endpoint | Role |
|----------|------|
| `GET /api/v1/health` | Connectivity |
| `GET /api/v1/agents` | Fleet roster |
| `GET /api/v1/events` | Console `pull` |
| `POST /api/v1/agents/{id}/tasks` | Tasking |

Full contract: [malbork/backend/CONTRACT.md](malbork/backend/CONTRACT.md).

Config:

```text
~/.local/share/reach/plugin-data/com__digitizable__malbork/plane.json
```

## Layout

```
ui.py                 # Reach entry (create_page)
malbork/
  page.py             # shell + wiring
  banner.py           # console ASCII
  theme.py / net.py / store.py / widgets.py
  backend/            # control-plane client + contract
  panels/             # Channel · Agents · Listener · …
```

## Purple stance

Operate the tasking loop **and** defend the keep — separate operator tokens from agent auth, honest listener state, path-aware egress. See research notes on [anguish.sh](https://anguish.sh/studies/malbork/notes) (corpus may still list as Handset until site deploy).

## License

GPL-3.0-or-later
