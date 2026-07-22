# Hogwarts

<p align="center">
  <img src="https://raw.githubusercontent.com/digitizable/reach-plugin-hogwarts/main/hogwarts.png?v=3" alt="Hogwarts" width="128"/>
</p>

**Hogwarts** is an optional [Reach](https://github.com/digitizable/reach) plugin for **command-and-control** work: agent tasking, control-plane configuration, listeners, egress checks, and operator playbooks.

It does not replace Reach’s path engine ([Spectre](https://github.com/digitizable/spectre)). Hogwarts talks to a **control plane** you host; the desk UI runs inside Reach.

> Unofficial name. Not affiliated with Warner Bros., J.K. Rowling, or the Harry Potter franchise.

**Requires Reach ≥ 0.5** · Plugin id `com.digitizable.hogwarts` · Version 0.5.44

---

## What it is

| Part | Role |
|------|------|
| **Reach plugin UI** | GTK pages under Operate (channel, agents, plane, …) |
| **Plane client** | HTTPS (or localhost) operator API — see [CONTRACT.md](hogwarts/backend/CONTRACT.md) |
| **Lab plane** | Optional stdlib mock control plane for development (`plane/server.py`) |
| **Reference agent** | Optional enroll/check-in agent for labs (`agent/agent.py`) |

Hogwarts does **not** embed a production implant server. Point **Plane** at your API and store connection settings under:

```text
~/.local/share/reach/plugin-data/com__digitizable__hogwarts/plane.json
```

### Path requirement

By default Reach requires an **active path** (Connect) before opening Operate plugins, including Hogwarts. That reduces clearnet exposure of agent traffic. Override only via **Reach → Settings → Privacy** (confirmation required).

---

## Install

In Reach: **Operate → Plugins** (marketplace):

```text
digitizable/reach-plugin-hogwarts
```

Enable **Operate** under **Settings → Plugins** if the marketplace rail is hidden.

### Local development

```bash
rsync -a --delete \
  --exclude .git --exclude __pycache__ \
  ./ ~/.local/share/reach/plugins/com__digitizable__hogwarts/
```

Restart Reach after syncing.

---

## UI panels

| Panel | Purpose |
|-------|---------|
| **Channel** | Path status, SOCKS, hops, plane summary |
| **Agents** | Roster, tasking, shell/FS; remote viewer for screenshot / live / control |
| **Listener** | Listener records, probes, plane sync |
| **Egress** | Connectivity matrix (direct vs path SOCKS) |
| **Console** | Operator shell and task helpers |
| **Plane** | Control-plane URL, token, poll interval, health; start local lab plane |
| **Ops kit** | Playbooks, drills, agent package export |
| **Session log** | Local activity trail |

---

## Control plane (lab)

For development only (`PLANE_OPERATOR_TOKEN=dev` is a lab default, not for production):

```bash
# terminal 1 — mock plane
PLANE_OPERATOR_TOKEN=dev PLANE_HTTP_ADDR=127.0.0.1:8080 python3 plane/server.py

# mint enroll secret
curl -s -X POST http://127.0.0.1:8080/api/v1/operator/enroll-secrets \
  -H "Authorization: Bearer dev" -H "Content-Type: application/json" \
  -d '{"max_uses":1}'

# terminal 2 — reference agent (after writing enroll_secret into agent.json)
python3 agent/agent.py once -c agent.json
```

In Hogwarts **Plane**: base URL `http://127.0.0.1:8080`, token `dev`, then use **Agents**.

### Lab helpers

```bash
bash lab/personal_setup.sh   # plane config, Docker mock agents, host agent pack
cd lab && ./run_lab.sh       # build images, smoke enroll/shell, leave containers up
```

`personal_setup.sh` writes lab `plane.json` and may set a guest plane URL of
`http://192.168.122.1:8080` (default libvirt NAT gateway). Adjust for your network.

API contract: [hogwarts/backend/CONTRACT.md](hogwarts/backend/CONTRACT.md).

---

## Repository layout

```text
ui.py                 # plugin entry
hogwarts/             # Reach plugin UI + operator client
plane/server.py       # lab control plane
agent/agent.py        # reference agent
lab/                  # Docker / smoke helpers
```

---

## Security

- Install only from sources you trust. Plugins run in-process with Reach.
- Use for systems and engagements you are authorized to control.
- Prefer an active Reach path before agent work (see path gate above).
- Lab tokens (`dev`) and open enroll secrets are for local testing only.

---

## Related

- [Reach](https://github.com/digitizable/reach) — desktop UI and plugin host  
- [Spectre](https://github.com/digitizable/spectre) — path engine  
- Study notes: [anguish.sh — Hogwarts](https://anguish.sh/studies/hogwarts)

## License

[GNU General Public License v3.0 or later](LICENSE) (`GPL-3.0-or-later`).
