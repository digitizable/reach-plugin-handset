# Assets

| File | Notes |
|------|--------|
| `icon.png` | Marketplace & README — from operator art (`hogwarts-app-icon.jpg`): white bg removed, 512×512 full-bleed RGBA |
| `icon-symbolic.svg` | **Left rail only** — white multi-tower keep + pennants on transparent (matches Reach monochrome rail marks such as `globe.svg`) |
| `icon.svg` | Legacy vector (unused when `icon.png` is the marketplace file) |

## Rail mark lineage

Symbolic castle silhouette for the sidebar: original monochrome mark (white fill, transparent plate) in the same spirit as free castle/keep iconography used on open icon sets. Not a licensed Harry Potter franchise asset.

## Console art (`hogwarts/banner.py`)

| Piece | Source |
|-------|--------|
| **High-detail keep** | Pure ASCII multi-tower splash; flags as `\|>>>` on the **same lines** as towers (so they cannot detach). Expanded from classic pure-ASCII castle patterns in the [asciiart.eu castles gallery](https://www.asciiart.eu/buildings-and-places/castles) (community / unknown artists). |
| **Why not braille** | Braille/block art + `WORD_CHAR` wrap and mixed glyph widths made pennants appear to “float” off the roof. Pure ASCII + `wrap_mode=NONE` keeps flags attached. |

**Name:** Hogwarts — castle keep metaphor. Unofficial fan naming; not affiliated with Warner Bros. or the Harry Potter franchise.
