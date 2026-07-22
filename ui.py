"""Hogwarts plugin entry — Reach loads create_page(ctx)."""

from __future__ import annotations

import sys
from pathlib import Path


def create_page(ctx):
    """Install plugin root + vendored keepstream on sys.path."""
    root = Path(ctx.plugin_dir).resolve()
    root_s = str(root)
    if root_s not in sys.path:
        sys.path.insert(0, root_s)
    # Keepstream desk dependency (git submodule third_party/keepstream)
    ks_src = root / "third_party" / "keepstream" / "src"
    if ks_src.is_dir():
        ks_s = str(ks_src)
        if ks_s not in sys.path:
            sys.path.insert(0, ks_s)
    from hogwarts.page import HogwartsPage

    return HogwartsPage(ctx)
