"""HTTP client for the Hogwarts control plane (stdlib only)."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from urllib.parse import quote, urljoin

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


@dataclass
class EventDTO:
    ts: datetime
    level: str
    channel: str
    message: str
    agent_id: str | None = None


class C2Client:
    """Thin urllib client — no extra pip deps."""

    def __init__(self, config: PlaneConfig) -> None:
        self.config = config

    def _url(self, path: str) -> str:
        base = self.config.base_url.rstrip("/") + "/"
        return urljoin(base, path.lstrip("/"))

    def _request(
        self,
        method: str,
        path: str,
        *,
        body: dict[str, Any] | None = None,
        timeout: float = 10.0,
    ) -> Any:
        if not self.config.is_configured:
            raise ConnectionError("Control plane not configured — set URL in Plane")
        data = None
        headers = {
            "Accept": "application/json",
            "User-Agent": "hogwarts/0.3",
        }
        if self.config.api_token:
            headers["Authorization"] = f"Bearer {self.config.api_token}"
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(
            self._url(path), data=data, headers=headers, method=method
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read().decode("utf-8")
                return json.loads(raw) if raw.strip() else {}
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise ConnectionError(f"HTTP {exc.code}: {detail or exc.reason}") from exc
        except urllib.error.URLError as exc:
            raise ConnectionError(f"Unreachable: {exc.reason}") from exc

    def health(self) -> dict[str, Any]:
        return self._request("GET", "/api/v1/health")

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
        payload = self._request("GET", "/api/v1/agents?" + "&".join(qs))
        return [_parse_agent(a) for a in payload.get("agents") or []]

    def get_agent(self, agent_id: str) -> AgentDTO | None:
        payload = self._request("GET", f"/api/v1/agents/{agent_id}")
        agent = payload.get("agent")
        return _parse_agent(agent) if agent else None

    def poll_events(self, *, since: str | None = None, limit: int = 100) -> list[EventDTO]:
        qs = [f"limit={limit}"]
        if since:
            qs.append(f"since={quote(since)}")
        payload = self._request("GET", "/api/v1/events?" + "&".join(qs))
        return [_parse_event(e) for e in payload.get("events") or []]


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
            hostname="?",
            username="",
            os="",
            status="unknown",
            last_seen=None,
            external_ip="",
        )
    tags = raw.get("tags")
    return AgentDTO(
        id=str(raw.get("id") or ""),
        hostname=str(raw.get("hostname") or raw.get("name") or "?"),
        username=str(raw.get("username") or ""),
        os=str(raw.get("os") or ""),
        status=str(raw.get("status") or "unknown").lower(),
        last_seen=_parse_dt(raw.get("last_seen")),
        external_ip=str(raw.get("external_ip") or ""),
        internal_ip=str(raw.get("internal_ip") or ""),
        group=str(raw.get("group") or ""),
        tags=list(tags) if isinstance(tags, list) else None,
        arch=str(raw.get("arch") or ""),
        sleep=float(raw["sleep"]) if raw.get("sleep") is not None else None,
        jitter=float(raw["jitter"]) if raw.get("jitter") is not None else None,
    )


def _parse_event(raw: dict[str, Any]) -> EventDTO:
    return EventDTO(
        ts=_parse_dt(raw.get("ts")) or datetime.now(),
        level=str(raw.get("level") or "info"),
        channel=str(raw.get("channel") or "system"),
        message=str(raw.get("message") or ""),
        agent_id=str(raw["agent_id"]) if raw.get("agent_id") else None,
    )
