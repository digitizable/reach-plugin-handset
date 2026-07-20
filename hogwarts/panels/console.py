"""Interactive operator console."""

from __future__ import annotations

import shlex
from datetime import datetime, timezone
from typing import Any, Callable

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk  # noqa: E402

from hogwarts.banner import banner, banner_short

_HELP = """Commands:
  help              Show this help
  banner            Show Hogwarts ASCII splash
  clear             Clear the console (reprints short mark)
  echo <text>       Print text
  time              Local + UTC time
  status            Path + plane summary
  plane             Show control-plane URL (no token)
  pull              Fetch events from the API
  agents            Refresh agent count
  socks             Print live SOCKS URL
  # anything else   Logged as an operator note
"""


class ConsolePanel(Gtk.Box):
    def __init__(
        self,
        *,
        on_command: Callable[[str], str | None],
    ) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.add_css_class("hogwarts-panel")
        self.set_hexpand(True)
        self.set_vexpand(True)
        self._on_command = on_command
        self._history: list[str] = []

        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        lab = Gtk.Label(label="Console", xalign=0)
        lab.add_css_class("hogwarts-section")
        lab.set_hexpand(True)
        bar.append(lab)
        help_b = Gtk.Button(label="Help")
        help_b.add_css_class("flat")
        help_b.connect("clicked", lambda *_: self._run("help"))
        bar.append(help_b)
        clr = Gtk.Button(label="Clear")
        clr.add_css_class("flat")
        clr.connect("clicked", lambda *_: self._run("clear"))
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
        self.view.set_monospace(True)
        self.view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.view.set_top_margin(10)
        self.view.set_bottom_margin(10)
        self.view.set_left_margin(12)
        self.view.set_right_margin(12)
        self.view.add_css_class("hogwarts-log")
        scroll.set_child(self.view)
        self.append(scroll)

        entry_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        entry_row.set_margin_top(8)
        prompt = Gtk.Label(label="›")
        prompt.add_css_class("hogwarts-ok")
        entry_row.append(prompt)
        self.entry = Gtk.Entry()
        self.entry.add_css_class("hogwarts-console-input")
        self.entry.set_hexpand(True)
        self.entry.set_placeholder_text("help · status · pull · agents…")
        self.entry.connect("activate", self._on_activate)
        entry_row.append(self.entry)
        go = Gtk.Button(label="Run")
        go.add_css_class("flat")
        go.connect("clicked", self._on_activate)
        entry_row.append(go)
        self.append(entry_row)

        self._show_boot_banner()

    def _show_boot_banner(self) -> None:
        self.append_out(banner())

    def append_out(self, text: str) -> None:
        buf = self.view.get_buffer()
        end = buf.get_end_iter()
        if buf.get_char_count() > 0:
            buf.insert(end, "\n")
            end = buf.get_end_iter()
        buf.insert(end, text)
        # keep last ~20k chars
        if buf.get_char_count() > 20000:
            start = buf.get_start_iter()
            cut = buf.get_iter_at_offset(buf.get_char_count() - 16000)
            buf.delete(start, cut)
        mark = buf.create_mark(None, buf.get_end_iter(), False)
        self.view.scroll_to_mark(mark, 0.0, False, 0.0, 1.0)

    def _on_activate(self, *_a: Any) -> None:
        line = self.entry.get_text().strip()
        self.entry.set_text("")
        if not line:
            return
        self._run(line)

    def _run(self, line: str) -> None:
        self.append_out(f"› {line}")
        self._history.append(line)
        cmd, *rest = shlex.split(line) if line else [""]
        cmd = (cmd or "").lower()

        if cmd == "help":
            self.append_out(_HELP.strip())
            return
        if cmd in ("banner", "splash", "logo"):
            self.append_out(banner())
            return
        if cmd == "clear":
            self.view.get_buffer().set_text("")
            self.append_out(banner_short())
            return
        if cmd == "echo":
            self.append_out(" ".join(rest))
            return
        if cmd == "time":
            now = datetime.now().astimezone()
            utc = datetime.now(timezone.utc)
            self.append_out(f"local {now.isoformat()}\nutc   {utc.isoformat()}")
            return

        # Delegate remaining commands to host
        out = self._on_command(line)
        if out:
            self.append_out(out)
