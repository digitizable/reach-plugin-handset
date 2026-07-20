# Hogwarts — Control plane contract

Hogwarts is the **operator desk** inside Reach. Live fleet data comes from a C2
**control-plane API** you host. Until that API is configured, Agents stays empty
and local tools (channel, egress, listener notes, playbooks) still work.

Config is stored under Reach plugin data:
`~/.local/share/reach/plugin-data/com__digitizable__hogwarts/plane.json`

---

## Base

| Item | Requirement |
|------|-------------|
| Transport | HTTPS (HTTP only on localhost/dev) |
| Format | JSON, UTF-8 |
| Auth | `Authorization: Bearer <token>` |
| Time | ISO-8601 UTC |
| Errors | `{ "error": { "code": "…", "message": "…" } }` + HTTP status |

---

## Health

```
GET /api/v1/health
→ 200 { "status": "ok", "version": "…", "time": "…" }
```

---

## Agents

```
GET /api/v1/agents?status=online|idle|offline&q=<search>&limit=200
→ 200 {
  "agents": [
    {
      "id": "agt_…",
      "hostname": "wkstn-04",
      "username": "jdoe",
      "os": "Windows 11",
      "arch": "x64",
      "status": "online",
      "last_seen": "…Z",
      "external_ip": "203.0.113.1",
      "internal_ip": "10.0.0.12",
      "group": "red-team",
      "tags": ["vip"],
      "sleep": 5,
      "jitter": 0.2
    }
  ],
  "next_cursor": null
}
```

```
GET /api/v1/agents/{id}
→ 200 { "agent": { … } }
```

```
POST /api/v1/agents/{id}/tasks
Body: {
  "type": "shell|ping|note|…",
  "payload": { … },
  "client_request_id": "uuid-optional"
}
→ 202 { "task_id": "tsk_…", "status": "queued", "created": "…Z" }
```

Minimal `type` values for v1: `shell`, `ping`, `note`. Prefer async queue + result events over interactive PTY.

```
GET /api/v1/agents/{id}/tasks?limit=50
→ 200 { "tasks": [ { "id", "type", "status", "created", "updated", "result"? } ] }

GET /api/v1/tasks/{task_id}
→ 200 { "task": { … } }
```

Task `status`: `queued` | `assigned` | `running` | `succeeded` | `failed` | `cancelled`.

---

## Events

```
GET /api/v1/events?since=<iso>&limit=100
→ 200 {
  "events": [
    {
      "ts": "…Z",
      "level": "info|ok|warn|error",
      "channel": "agent|listener|task|system",
      "message": "…",
      "agent_id": "…?"
    }
  ]
}
```

Optional later: WebSocket `/api/v1/events/ws`.
