"""Session log panel."""

from __future__ import annotations

from typing import Callable

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk  # noqa: E402


class LogPanel(Gtk.Box):
    def __init__(self, *, on_clear: Callable) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.add_css_class("hogwarts-panel")
        self.set_hexpand(True)
        self.set_vexpand(True)

        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        lab = Gtk.Label(label="Session log", xalign=0)
        lab.add_css_class("hogwarts-section")
        lab.set_hexpand(True)
        bar.append(lab)
        clr = Gtk.Button(label="Clear")
        clr.add_css_class("flat")
        clr.connect("clicked", on_clear)
        bar.append(clr)
        self.append(bar)

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll.set_hexpand(True)
        scroll.set_vexpand(True)
        scroll.set_halign(Gtk.Align.FILL)
        scroll.set_valign(Gtk.Align.FILL)
        try:
            scroll.set_propagate_natural_height(False)
        except Exception:
            pass
        scroll.set_min_content_height(160)
        self.view = Gtk.TextView()
        self.view.set_editable(False)
        self.view.set_cursor_visible(False)
        self.view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.view.set_top_margin(10)
        self.view.set_bottom_margin(10)
        self.view.set_left_margin(12)
        self.view.set_right_margin(12)
        self.view.add_css_class("hogwarts-log")
        scroll.set_child(self.view)
        self.append(scroll)

    def set_text(self, text: str) -> None:
        self.view.get_buffer().set_text(text)
