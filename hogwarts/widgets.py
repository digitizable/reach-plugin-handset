"""Shared GTK helpers."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk  # noqa: E402


def section_label(title: str) -> Gtk.Widget:
    lab = Gtk.Label(label=title, xalign=0)
    lab.add_css_class("hogwarts-section")
    lab.set_margin_top(4)
    return lab


def field(title: str, child: Gtk.Widget) -> Gtk.Widget:
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
    lab = Gtk.Label(label=title, xalign=0)
    lab.add_css_class("hogwarts-field-label")
    box.append(lab)
    box.append(child)
    return box


def kv_row(key: str) -> tuple[Gtk.Widget, Gtk.Label]:
    row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
    k = Gtk.Label(label=key, xalign=0)
    k.add_css_class("hogwarts-kv-key")
    k.set_size_request(88, -1)
    row.append(k)
    v = Gtk.Label(label="—", xalign=0, wrap=True, selectable=True)
    v.add_css_class("hogwarts-kv-val")
    v.set_hexpand(True)
    row.append(v)
    return row, v


def scroll_panel(body: Gtk.Widget) -> Gtk.ScrolledWindow:
    """Full-bleed panel scroller — must expand or GTK allocates a tiny viewport."""
    scroll = Gtk.ScrolledWindow()
    scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
    scroll.set_hexpand(True)
    scroll.set_vexpand(True)
    scroll.set_halign(Gtk.Align.FILL)
    scroll.set_valign(Gtk.Align.FILL)
    # Use the stack allocation; do not size to full content height (clips parent).
    try:
        scroll.set_propagate_natural_height(False)
        scroll.set_propagate_natural_width(False)
    except Exception:
        pass
    # Floor so a glitchy parent still shows more than a few pixels.
    try:
        scroll.set_min_content_height(200)
    except Exception:
        pass
    if hasattr(body, "set_hexpand"):
        body.set_hexpand(True)
    scroll.set_child(body)
    return scroll
