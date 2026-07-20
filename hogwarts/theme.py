"""Inline CSS for Hogwarts (plugin-local; does not depend on Reach CSS)."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gdk, Gtk  # noqa: E402

HOGWARTS_CSS = b"""
.hogwarts-page {
  background-color: #111111;
  color: #e8e8e8;
}
.hogwarts-header {
  background-color: #0d0d0d;
  border-bottom: 1px solid #222222;
  padding: 10px 16px;
  min-height: 44px;
}
.hogwarts-title {
  font-size: 1.05rem;
  font-weight: 700;
  color: #f0f0f0;
}
.hogwarts-sub {
  font-size: 0.82rem;
  color: #8a8a8a;
}
.hogwarts-banner {
  background-color: #1a1814;
  border: 1px solid #3d3520;
  border-radius: 10px;
  padding: 10px 12px;
  color: #c9b27a;
  font-size: 0.82rem;
}
.hogwarts-split {
  min-height: 0;
}
.hogwarts-sidebar {
  background-color: #0f0f0f;
  border-right: 1px solid #222;
  min-width: 200px;
  padding: 12px 10px;
}
.hogwarts-stack {
  min-height: 0;
  min-width: 0;
}
.hogwarts-nav-btn {
  border-radius: 10px;
  min-height: 40px;
  padding: 0 12px;
  margin: 2px 0;
  background: transparent;
  color: #a0a0a0;
  border: 1px solid transparent;
}
.hogwarts-nav-btn:hover {
  background-color: #161616;
  color: #e0e0e0;
}
.hogwarts-nav-btn:checked,
.hogwarts-nav-btn:active {
  background-color: #1a1a1c;
  color: #e8e8e8;
  border-color: #2a2a2e;
}
.hogwarts-main {
  background-color: #111111;
  min-width: 0;
  min-height: 0;
}
.hogwarts-panel {
  padding: 20px 24px 28px 24px;
}
.hogwarts-hero {
  background: linear-gradient(145deg, #161a22 0%, #12141a 55%, #0e1014 100%);
  border: 1px solid #2a3140;
  border-radius: 14px;
  padding: 16px 18px;
}
.hogwarts-hero-title {
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #6a7a94;
}
.hogwarts-hero-state {
  font-size: 1.4rem;
  font-weight: 700;
  color: #f2f2f2;
}
.hogwarts-hero-meta {
  font-size: 0.88rem;
  color: #a8b0c0;
  font-family: monospace;
}
.hogwarts-dot {
  min-width: 10px;
  min-height: 10px;
  border-radius: 99px;
  background-color: #555;
}
.hogwarts-dot-live {
  background-color: #5fbf70;
  box-shadow: 0 0 8px rgba(95, 191, 112, 0.45);
}
.hogwarts-dot-idle {
  background-color: #707070;
}
.hogwarts-dot-busy {
  background-color: #6aa3e8;
  box-shadow: 0 0 8px rgba(106, 163, 232, 0.4);
}
.hogwarts-dot-off {
  background-color: #e86a6a;
}
.hogwarts-card {
  background-color: #161616;
  border: 1px solid #262626;
  border-radius: 12px;
  padding: 14px 16px;
}
.hogwarts-card-title {
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: #707070;
  margin-bottom: 2px;
}
.hogwarts-kv-key {
  font-size: 0.75rem;
  color: #666;
  font-weight: 600;
  min-width: 72px;
}
.hogwarts-kv-val {
  font-size: 0.88rem;
  color: #d4d4d4;
  font-family: monospace;
}
.hogwarts-field-label {
  font-size: 0.78rem;
  font-weight: 600;
  color: #8a8a8a;
}
.hogwarts-section {
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.07em;
  text-transform: uppercase;
  color: #5a5a5a;
}
.hogwarts-muted {
  color: #8a8a8a;
  font-size: 0.85rem;
}
.hogwarts-probe-row {
  background-color: #141414;
  border: 1px solid #222;
  border-radius: 10px;
  padding: 10px 12px;
  margin: 4px 0;
}
.hogwarts-probe-label {
  font-weight: 600;
  font-size: 0.9rem;
  color: #e0e0e0;
}
.hogwarts-probe-target {
  font-size: 0.78rem;
  color: #707070;
  font-family: monospace;
}
.hogwarts-ok {
  color: #8fd19e;
  font-weight: 700;
  font-size: 0.8rem;
}
.hogwarts-fail {
  color: #e89a9a;
  font-weight: 700;
  font-size: 0.8rem;
}
.hogwarts-log {
  font-family: "DejaVu Sans Mono", "Noto Sans Mono", "Liberation Mono",
    "Ubuntu Mono", monospace;
  font-size: 0.78rem;
  color: #b0b8c8;
  background-color: #0c0c0c;
  border: 1px solid #222;
  border-radius: 10px;
  padding: 10px 12px;
}
.hogwarts-chip {
  font-size: 0.7rem;
  font-weight: 700;
  border-radius: 999px;
  padding: 2px 8px;
  background-color: #222;
  color: #9a9a9a;
}
.hogwarts-chip-live {
  background-color: #1a2a1c;
  color: #8fd19e;
}
.hogwarts-chip-plane {
  background-color: #1a2230;
  color: #8ab4f8;
}
.hogwarts-action-grid {
  margin-top: 4px;
}
.hogwarts-agent-row {
  background-color: #141414;
  border: 1px solid #222;
  border-radius: 12px;
  padding: 12px 14px;
  margin: 4px 0;
}
.hogwarts-agent-row:hover {
  border-color: #333;
  background-color: #161616;
}
.hogwarts-agent-host {
  font-size: 0.98rem;
  font-weight: 700;
  color: #f0f0f0;
}
.hogwarts-agent-meta {
  font-size: 0.8rem;
  color: #8a8a8a;
  font-family: monospace;
}
.hogwarts-status-online { color: #8fd19e; font-weight: 700; font-size: 0.78rem; }
.hogwarts-status-idle { color: #c9b27a; font-weight: 700; font-size: 0.78rem; }
.hogwarts-status-offline { color: #e89a9a; font-weight: 700; font-size: 0.78rem; }
.hogwarts-status-unknown { color: #8a8a8a; font-weight: 700; font-size: 0.78rem; }
.hogwarts-console-input {
  font-family: monospace;
  font-size: 0.9rem;
}
"""


def apply_css(widget: Gtk.Widget) -> None:
    try:
        provider = Gtk.CssProvider()
        provider.load_from_data(HOGWARTS_CSS)
        display = Gdk.Display.get_default()
        if display is not None:
            Gtk.StyleContext.add_provider_for_display(
                display,
                provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
            )
    except Exception:
        pass
