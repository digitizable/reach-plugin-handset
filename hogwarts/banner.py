"""Short console status lines for Hogwarts (no ASCII art)."""

from __future__ import annotations

from hogwarts import __version__


def banner(*, version: str | None = None) -> str:
    """Boot / splash line for the operator console."""
    ver = version if version is not None else __version__
    return f"Hogwarts v{ver} — C2 keep ready. Type help."


def banner_short() -> str:
    """Compact line after `clear`."""
    return f"Hogwarts v{__version__} — type help."
