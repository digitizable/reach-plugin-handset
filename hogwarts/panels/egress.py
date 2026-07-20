"""Egress probe matrix panel."""

from __future__ import annotations

from typing import Any, Callable

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk  # noqa: E402

from hogwarts.widgets import scroll_panel, section_label


class EgressPanel(Gtk.Box):
    def __init__(
        self,
        *,
        on_run: Callable,
        on_custom: Callable,
        last_rows: list[dict[str, Any]] | None = None,
        last_ts: str = "",
    ) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.set_hexpand(True)
        self.set_vexpand(True)

        body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        body.add_css_class("hogwarts-panel")

        intro = Gtk.Label(
            label=(
                "Probe which callback classes answer from this host — direct "
                "clearnet vs through the live Spectre SOCKS path."
            ),
            wrap=True,
            xalign=0,
        )
        intro.add_css_class("hogwarts-muted")
        body.append(intro)

        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.probe_btn = Gtk.Button(label="Run egress matrix")
        self.probe_btn.add_css_class("suggested-action")
        self.probe_btn.connect("clicked", lambda *_: on_run())
        bar.append(self.probe_btn)
        self.probe_status = Gtk.Label(label="", xalign=0)
        self.probe_status.add_css_class("hogwarts-muted")
        self.probe_status.set_hexpand(True)
        bar.append(self.probe_status)
        body.append(bar)

        self.probe_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.probe_box.add_css_class("hogwarts-card")
        self._empty = Gtk.Label(
            label="No results yet — run the matrix to compare direct vs path.",
            xalign=0,
            wrap=True,
        )
        self._empty.add_css_class("hogwarts-muted")
        self._empty.set_margin_top(4)
        self._empty.set_margin_bottom(4)
        self.probe_box.append(self._empty)
        body.append(self.probe_box)

        body.append(section_label("Custom target"))
        custom = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.custom_host = Gtk.Entry()
        self.custom_host.set_placeholder_text("host")
        self.custom_host.set_hexpand(True)
        custom.append(self.custom_host)
        self.custom_port = Gtk.Entry()
        self.custom_port.set_placeholder_text("443")
        self.custom_port.set_width_chars(6)
        self.custom_port.set_text("443")
        custom.append(self.custom_port)
        cust_b = Gtk.Button(label="Probe")
        cust_b.add_css_class("flat")
        cust_b.connect("clicked", lambda *_: on_custom())
        custom.append(cust_b)
        body.append(custom)

        self.append(scroll_panel(body))
        if last_rows:
            self.render_rows(last_rows, ts=last_ts)

    def set_busy(self, busy: bool, status: str = "") -> None:
        self.probe_btn.set_sensitive(not busy)
        if status:
            self.probe_status.set_text(status)

    def render_rows(self, rows: list[dict[str, Any]], *, ts: str = "") -> None:
        while child := self.probe_box.get_first_child():
            self.probe_box.remove(child)
        if ts:
            self.probe_status.set_text(f"Last run · {ts[:19].replace('T', ' ')}Z")
        if not rows:
            self.probe_box.append(self._empty)
            return
        for row in rows:
            self.probe_box.append(self._row_widget(row))

    @staticmethod
    def _row_widget(row: dict[str, Any]) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box.add_css_class("hogwarts-probe-row")
        top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        lab = Gtk.Label(label=str(row.get("label") or "Probe"), xalign=0)
        lab.add_css_class("hogwarts-probe-label")
        lab.set_hexpand(True)
        top.append(lab)
        tgt = Gtk.Label(
            label=f"{row.get('host')}:{row.get('port')}",
            xalign=1,
        )
        tgt.add_css_class("hogwarts-probe-target")
        top.append(tgt)
        box.append(top)

        stats = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        d_ok = bool(row.get("direct_ok"))
        d_lab = Gtk.Label(
            label=f"direct  {'OK' if d_ok else 'FAIL'}  {row.get('direct_ms', 0):.0f}ms",
            xalign=0,
        )
        d_lab.add_css_class("hogwarts-ok" if d_ok else "hogwarts-fail")
        stats.append(d_lab)
        if "path_ok" in row:
            p_ok = bool(row.get("path_ok"))
            p_lab = Gtk.Label(
                label=f"path  {'OK' if p_ok else 'FAIL'}  {row.get('path_ms', 0):.0f}ms",
                xalign=0,
            )
            p_lab.add_css_class("hogwarts-ok" if p_ok else "hogwarts-fail")
            stats.append(p_lab)
        else:
            n = Gtk.Label(label="path  —  (no SOCKS)", xalign=0)
            n.add_css_class("hogwarts-muted")
            stats.append(n)
        box.append(stats)
        return box
