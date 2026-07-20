# Assets

| File | Notes |
|------|--------|
| `icon.png` | Marketplace & README — from operator art (`hogwarts-app-icon.jpg`): white bg removed, 512×512 full-bleed RGBA |
| `icon-symbolic.svg` | **Left rail only** — solid white castle silhouette on transparent, traced from `for-grok/hogwarts-ascii.txt` braille art (not glyph-look) |
| `icon.svg` | Legacy vector (unused when `icon.png` is the marketplace file) |

## Rail mark lineage

`icon-symbolic.svg` is a **solid silhouette** converted from the braille castle in `~/Downloads/for-grok/hogwarts-ascii.txt`:

1. Decode Unicode braille cells → bitmap (2×4 dots per character).
2. Morphological close so towers read as continuous mass, not dots.
3. Run-length rects → single filled path, scaled into a 24×24 viewBox (`fill="#ffffff"`).

Matches Reach monochrome rail marks such as `globe.svg`. Not a licensed Harry Potter franchise asset.

**GdkPixbuf note:** Keep long XML comments *inside* the root `<svg>` element. Comments (or other preamble) longer than ~200 bytes *before* `<svg` cause `Couldn't recognize the image file format` — the loader only sniffs a short prefix for the root tag.

## Console (`hogwarts/banner.py`)

Short status lines only (no ASCII splash). Boot and `banner` / `clear` print a one-line ready message.

**Name:** Hogwarts — castle keep metaphor. Unofficial fan naming; not affiliated with Warner Bros. or the Harry Potter franchise.
