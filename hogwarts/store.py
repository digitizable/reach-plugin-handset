"""Local JSON persistence under plugin data."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class MetaStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> dict[str, Any]:
        if not self.path.is_file():
            return {}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}

    def save(self, data: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    def update(self, **kwargs: Any) -> dict[str, Any]:
        data = self.load()
        data.update(kwargs)
        self.save(data)
        return data
