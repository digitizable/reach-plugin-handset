"""Back-compat re-export — implementation lives in the keepstream package.

Install: pip install -e third_party/keepstream
Or vendor: third_party/keepstream (git submodule; ui.py adds src/ to path).
"""

from __future__ import annotations

from keepstream.client import KeepstreamClient
from keepstream.protocol import (
    TYPE_CTRL,
    TYPE_INPUT,
    TYPE_PING,
    TYPE_PONG,
    TYPE_VIDEO,
)

__all__ = [
    "KeepstreamClient",
    "TYPE_VIDEO",
    "TYPE_INPUT",
    "TYPE_CTRL",
    "TYPE_PING",
    "TYPE_PONG",
]
