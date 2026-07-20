"""Control-plane credentials (operator-side only)."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class PlaneConfig:
    """base_url + api_token for the C2 control plane."""

    base_url: str = ""
    api_token: str = ""
    poll_interval_sec: float = 5.0
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def is_configured(self) -> bool:
        return bool(self.base_url.strip())


def load_plane_config(path: Path) -> PlaneConfig:
    if not path.is_file():
        return PlaneConfig()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return PlaneConfig()
    return PlaneConfig(
        base_url=str(raw.get("base_url", "") or ""),
        api_token=str(raw.get("api_token", "") or ""),
        poll_interval_sec=float(raw.get("poll_interval_sec", 5.0) or 5.0),
        extra=dict(raw.get("extra") or {}),
    )


def save_plane_config(path: Path, cfg: PlaneConfig) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(asdict(cfg), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
