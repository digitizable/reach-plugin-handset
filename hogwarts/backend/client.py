"""HTTP client for the Hogwarts control plane (stdlib only)."""

from __future__ import annotations

import http.client
import json
import ssl
import threading
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from urllib.parse import quote, urljoin, urlparse

from hogwarts.backend.config import PlaneConfig


@dataclass
class AgentDTO:
    id: str
    hostname: str
    username: str
    os: str
    status: str
    last_seen: datetime | None
    external_ip: str
    internal_ip: str = ""
    group: str = ""
    tags: list[str] | None = None
    arch: str = ""
    sleep: float | None = None
    jitter: float | None = None
    # async = beacon-class check-in; interactive = session-class / turbo sleep
    presence: str = "async"
    package_id: str = ""


@dataclass
class EventDTO:
    ts: datetime
    level: str
    channel: str
    message: str
    agent_id: str | None = None


@dataclass
class TaskDTO:
    id: str
    type: str
    status: str
    created: datetime | None
    updated: datetime | None
    payload: dict[str, Any] | None = None
    result: dict[str, Any] | None = None
    agent_id: str | None = None


class C2Client:
    """Thin HTTP client with connection keep-alive — no extra pip deps.

    Thread-safe: Live/Control/poll/task workers share one desk client; all
    request I/O is serialized on ``_lock`` (http.client is not re-entrant).
    """

    def __init__(self, config: PlaneConfig) -> None:
        self.config = config
        self._conn: http.client.HTTPConnection | http.client.HTTPSConnection | None = None
        self._conn_key: tuple[str, str, int] | None = None
        self._lock = threading.RLock()

    def close(self) -> None:
        with self._lock:
            if self._conn is not None:
                try:
                    self._conn.close()
                except Exception:
                    pass
            self._conn = None
            self._conn_key = None

    def _url(self, path: str) -> str:
        base = self.config.base_url.rstrip("/") + "/"
        return urljoin(base, path.lstrip("/"))

    def _ensure_conn(self, timeout: float) -> tuple[http.client.HTTPConnection, str]:
        if not self.config.is_configured:
            raise ConnectionError("Control plane not configured — set URL in Plane")
        parsed = urlparse(self.config.base_url if "://" in self.config.base_url else "http://" + self.config.base_url)
        scheme = (parsed.scheme or "http").lower()
        host = parsed.hostname or "127.0.0.1"
        port = int(parsed.port or (443 if scheme == "https" else 80))
        key = (scheme, host, port)
        if self._conn is None or self._conn_key != key:
            if self._conn is not None:
                try:
                    self._conn.close()
                except Exception:
                    pass
            if scheme == "https":
                ctx = ssl.create_default_context()
                self._conn = http.client.HTTPSConnection(
                    host, port, timeout=timeout, context=ctx
                )
            else:
                self._conn = http.client.HTTPConnection(host, port, timeout=timeout)
            self._conn_key = key
        else:
            try:
                self._conn.timeout = timeout  # type: ignore[assignment]
            except Exception:
                pass
        # path+query absolute from base
        return self._conn, scheme

    def _request(
        self,
        method: str,
        path: str,
        *,
        body: dict[str, Any] | None = None,
        timeout: float = 5.0,
    ) -> Any:
        with self._lock:
            return self._request_locked(method, path, body=body, timeout=timeout)

    def _request_locked(
        self,
        method: str,
        path: str,
        *,
        body: dict[str, Any] | None = None,
        timeout: float = 5.0,
    ) -> Any:
        conn, _scheme = self._ensure_conn(timeout)
        full = self._url(path)
        parsed = urlparse(full)
        req_path = parsed.path or "/"
        if parsed.query:
            req_path = f"{req_path}?{parsed.query}"

        headers = {
            "Accept": "application/json",
            "User-Agent": "hogwarts/0.5.44",
            "Connection": "keep-alive",
        }
        if self.config.api_token:
            headers["Authorization"] = f"Bearer {self.config.api_token}"
        raw_body: bytes | None = None
        if body is not None:
            raw_body = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
            headers["Content-Length"] = str(len(raw_body))

        try:
            conn.request(method, req_path, body=raw_body, headers=headers)
            resp = conn.getresponse()
            raw = resp.read().decode("utf-8", errors="replace")
            if resp.status >= 400:
                raise ConnectionError(f"HTTP {resp.status}: {raw or resp.reason}")
            return json.loads(raw) if raw.strip() else {}
        except (http.client.HTTPException, OSError, TimeoutError) as exc:
            # Drop dead keep-alive socket and retry once
            if self._conn is not None:
                try:
                    self._conn.close()
                except Exception:
                    pass
            self._conn = None
            self._conn_key = None
            try:
                conn, _ = self._ensure_conn(timeout)
                conn.request(method, req_path, body=raw_body, headers=headers)
                resp = conn.getresponse()
                raw = resp.read().decode("utf-8", errors="replace")
                if resp.status >= 400:
                    raise ConnectionError(f"HTTP {resp.status}: {raw or resp.reason}")
                return json.loads(raw) if raw.strip() else {}
            except ConnectionError:
                raise
            except Exception as exc2:
                if self._conn is not None:
                    try:
                        self._conn.close()
                    except Exception:
                        pass
                self._conn = None
                self._conn_key = None
                raise ConnectionError(f"Unreachable: {exc2}") from exc2
        except ConnectionError:
            if self._conn is not None:
                try:
                    self._conn.close()
                except Exception:
                    pass
            self._conn = None
            self._conn_key = None
            raise
        except Exception as exc:
            if self._conn is not None:
                try:
                    self._conn.close()
                except Exception:
                    pass
            self._conn = None
            self._conn_key = None
            raise ConnectionError(f"Unreachable: {exc}") from exc

    def health(self) -> dict[str, Any]:
        return self._request("GET", "/api/v1/health", timeout=3.0)

    def list_agents(
        self,
        *,
        status: str | None = None,
        q: str | None = None,
        limit: int = 200,
    ) -> list[AgentDTO]:
        qs = [f"limit={limit}"]
        if status:
            qs.append(f"status={quote(status)}")
        if q:
            qs.append(f"q={quote(q)}")
        payload = self._request("GET", "/api/v1/agents?" + "&".join(qs), timeout=4.0)
        return [_parse_agent(a) for a in payload.get("agents") or []]

    def get_agent(self, agent_id: str) -> AgentDTO | None:
        payload = self._request("GET", f"/api/v1/agents/{agent_id}")
        agent = payload.get("agent")
        return _parse_agent(agent) if agent else None

    def create_task(
        self,
        agent_id: str,
        *,
        type_: str,
        payload: dict[str, Any] | None = None,
        client_request_id: str | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"type": type_, "payload": payload or {}}
        if client_request_id:
            body["client_request_id"] = client_request_id
        return self._request(
            "POST", f"/api/v1/agents/{agent_id}/tasks", body=body, timeout=5.0
        )

    def list_tasks(self, agent_id: str, *, limit: int = 50) -> list[TaskDTO]:
        # compact listing by default (no screenshot base64) — plane omits heavy fields
        payload = self._request(
            "GET",
            f"/api/v1/agents/{agent_id}/tasks?limit={int(limit)}",
            timeout=4.0,
        )
        return [_parse_task(t) for t in payload.get("tasks") or []]

    def get_task(self, task_id: str) -> TaskDTO | None:
        # Full result body (needed after wait for screenshot data)
        payload = self._request("GET", f"/api/v1/tasks/{task_id}", timeout=3.0)
        task = payload.get("task")
        return _parse_task(task) if task else None

    def cancel_task(self, task_id: str) -> TaskDTO | None:
        payload = self._request("POST", f"/api/v1/tasks/{task_id}/cancel", timeout=4.0)
        task = payload.get("task")
        return _parse_task(task) if task else None

    def mint_enroll_secret(
        self,
        *,
        max_uses: int = 1,
        ttl_sec: int = 3600,
        label: str | None = None,
        package_id: str | None = None,
        canary_label: str | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"max_uses": max_uses, "ttl_sec": ttl_sec}
        if label:
            body["label"] = label
        if package_id:
            body["package_id"] = package_id
        if canary_label:
            body["canary_label"] = canary_label
        return self._request(
            "POST",
            "/api/v1/operator/enroll-secrets",
            body=body,
        )

    def list_canaries(self, *, limit: int = 50) -> list[dict[str, Any]]:
        payload = self._request(
            "GET",
            f"/api/v1/operator/canaries?limit={int(limit)}",
            timeout=4.0,
        )
        return list(payload.get("canaries") or [])

    def list_listeners(self) -> list[dict[str, Any]]:
        payload = self._request("GET", "/api/v1/listeners")
        return list(payload.get("listeners") or [])

    def upsert_listener(self, body: dict[str, Any]) -> dict[str, Any]:
        lid = str(body.get("id") or "").strip()
        if lid:
            payload = self._request("PUT", f"/api/v1/listeners/{lid}", body=body)
        else:
            payload = self._request("POST", "/api/v1/listeners", body=body)
        return dict(payload.get("listener") or payload)

    def delete_listener(self, listener_id: str) -> None:
        self._request("DELETE", f"/api/v1/listeners/{listener_id}")

    def poll_events(self, *, since: str | None = None, limit: int = 100) -> list[EventDTO]:
        qs = [f"limit={limit}"]
        if since:
            qs.append(f"since={quote(since)}")
        payload = self._request(
            "GET", "/api/v1/events?" + "&".join(qs), timeout=4.0
        )
        return [_parse_event(e) for e in payload.get("events") or []]

    def open_event_stream(
        self,
        *,
        since: str | None = None,
        stop_flag: threading.Event | None = None,
        max_sec: int = 0,
    ):
        """Yield (kind, payload) from GET /api/v1/events/stream (SSE).

        kind is ``hello`` | ``plane`` | ``bye`` | ``raw``. Uses a **dedicated**
        connection so keep-alive poll traffic is not blocked. Caller runs this
        in a worker thread. Raises on connect/auth failure; yields until stop
        or disconnect.
        """
        if not self.config.is_configured:
            raise ConnectionError("Control plane not configured")
        parsed = urlparse(
            self.config.base_url
            if "://" in self.config.base_url
            else "http://" + self.config.base_url
        )
        scheme = (parsed.scheme or "http").lower()
        host = parsed.hostname or "127.0.0.1"
        port = int(parsed.port or (443 if scheme == "https" else 80))
        qs = []
        if since:
            qs.append(f"since={quote(since)}")
        if max_sec > 0:
            qs.append(f"max_sec={int(max_sec)}")
        path = "/api/v1/events/stream"
        if qs:
            path = path + "?" + "&".join(qs)
        headers = {
            "Accept": "text/event-stream",
            "Cache-Control": "no-cache",
            "User-Agent": "hogwarts/0.5.56",
            "Connection": "keep-alive",
        }
        if self.config.api_token:
            headers["Authorization"] = f"Bearer {self.config.api_token}"
        if scheme == "https":
            ctx = ssl.create_default_context()
            conn: http.client.HTTPConnection = http.client.HTTPSConnection(
                host, port, timeout=60, context=ctx
            )
        else:
            conn = http.client.HTTPConnection(host, port, timeout=60)
        try:
            conn.request("GET", path, headers=headers)
            resp = conn.getresponse()
            if resp.status >= 400:
                body = resp.read().decode("utf-8", errors="replace")
                raise ConnectionError(f"SSE HTTP {resp.status}: {body or resp.reason}")
            event_name = "message"
            data_lines: list[str] = []
            while True:
                if stop_flag is not None and stop_flag.is_set():
                    break
                # readline with socket timeout — heartbeats arrive ~12s
                line_b = resp.readline()
                if not line_b:
                    break
                line = line_b.decode("utf-8", errors="replace").rstrip("\r\n")
                if line == "":
                    if data_lines:
                        raw = "\n".join(data_lines)
                        data_lines = []
                        try:
                            payload = json.loads(raw)
                        except json.JSONDecodeError:
                            yield ("raw", raw)
                        else:
                            yield (event_name or "message", payload)
                        event_name = "message"
                    continue
                if line.startswith(":"):
                    # comment / heartbeat
                    continue
                if line.startswith("event:"):
                    event_name = line[6:].strip() or "message"
                    continue
                if line.startswith("data:"):
                    data_lines.append(line[5:].lstrip())
                    continue
                # ignore id: and other fields
        finally:
            try:
                conn.close()
            except Exception:
                pass


def _parse_dt(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    s = str(value).replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def _parse_agent(raw: dict[str, Any] | None) -> AgentDTO:
    if not raw:
        return AgentDTO(
            id="",
            hostname="",
            username="",
            os="",
            status="unknown",
            last_seen=None,
            external_ip="",
        )
    tags = raw.get("tags") or []
    if not isinstance(tags, list):
        tags = []
    sleep = raw.get("sleep")
    jitter = raw.get("jitter")
    try:
        sleep_f = float(sleep) if sleep is not None else None
    except (TypeError, ValueError):
        sleep_f = None
    try:
        jitter_f = float(jitter) if jitter is not None else None
    except (TypeError, ValueError):
        jitter_f = None
    presence = str(raw.get("presence") or "").strip().lower()
    if presence not in ("async", "interactive"):
        # Desk-side fallback if older plane omits presence
        if sleep_f is not None and sleep_f <= 0.4:
            presence = "interactive"
        else:
            presence = "async"
    return AgentDTO(
        id=str(raw.get("id") or ""),
        hostname=str(raw.get("hostname") or ""),
        username=str(raw.get("username") or ""),
        os=str(raw.get("os") or ""),
        status=str(raw.get("status") or "unknown"),
        last_seen=_parse_dt(raw.get("last_seen")),
        external_ip=str(raw.get("external_ip") or ""),
        internal_ip=str(raw.get("internal_ip") or ""),
        group=str(raw.get("group") or ""),
        tags=[str(t) for t in tags],
        arch=str(raw.get("arch") or ""),
        sleep=sleep_f,
        jitter=jitter_f,
        presence=presence,
        package_id=str(raw.get("package_id") or ""),
    )


def _parse_event(raw: dict[str, Any]) -> EventDTO:
    return EventDTO(
        ts=_parse_dt(raw.get("ts")) or datetime.now(),
        level=str(raw.get("level") or "info"),
        channel=str(raw.get("channel") or "system"),
        message=str(raw.get("message") or ""),
        agent_id=str(raw.get("agent_id")) if raw.get("agent_id") else None,
    )


def _parse_task(raw: dict[str, Any] | None) -> TaskDTO:
    if not raw:
        return TaskDTO(
            id="",
            type="",
            status="",
            created=None,
            updated=None,
        )
    payload = raw.get("payload")
    if not isinstance(payload, dict):
        payload = None
    result = raw.get("result")
    if not isinstance(result, dict):
        result = None
    return TaskDTO(
        id=str(raw.get("id") or ""),
        type=str(raw.get("type") or ""),
        status=str(raw.get("status") or ""),
        created=_parse_dt(raw.get("created")),
        updated=_parse_dt(raw.get("updated")),
        payload=payload,
        result=result,
        agent_id=str(raw.get("agent_id")) if raw.get("agent_id") else None,
    )
