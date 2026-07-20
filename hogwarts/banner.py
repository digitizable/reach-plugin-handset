"""ASCII marks for the Hogwarts operator console."""

from __future__ import annotations

from hogwarts import __version__

_WORDMARK = r"""
 _   _                                  _
| | | | ___   __ _ _ __   ____  _ _ __ | |_ ___
| |_| |/ _ \ / _` | '_ \ / _  \| '__| __/ __|
|  _  | (_) | (_| | | | | (_| | |  | |_\__ \
|_| |_|\___/ \__, |_| |_|\__,_|_|   \__|___/
             |___/
""".strip(
    "\n"
)

# Great hall / four towers silhouette (desk splash).
_GLYPH = r"""
              /\
       /\    /  \    /\
      /  \__/ || \__/  \
     |  []    ||    []  |
     |______  ||  ______|
    /  ___  \ || /  ___  \
   |  |   |  ||||  |   |  |
   |__|___|__||||__|___|__|
        C2 desk for Reach
   channel · agents · plane · keep
""".strip(
    "\n"
)


def banner(*, version: str | None = None) -> str:
    """Full splash for console boot / `banner` command."""
    ver = version if version is not None else __version__
    lines = [
        _WORDMARK,
        "",
        _GLYPH,
        "",
        f"  Hogwarts v{ver}  ·  type help",
    ]
    return "\n".join(lines)


def banner_short() -> str:
    """One-shot compact mark (e.g. after clear)."""
    return (
        "  ┌─────────── HOGWARTS ───────────┐\n"
        "  │  ⚔  keep  ·  C2 desk for Reach │\n"
        "  └────────────────────────────────┘"
    )
