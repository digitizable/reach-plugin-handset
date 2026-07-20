"""Ops kit — export folder, playbooks, data dir."""

from __future__ import annotations

from typing import Callable

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk  # noqa: E402

from hogwarts.widgets import scroll_panel, section_label


class OpsPanel(Gtk.Box):
    def __init__(
        self,
        data_dir: str,
        *,
        on_open_export: Callable,
        on_export_playbook: Callable,
        on_open_data: Callable,
    ) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.set_hexpand(True)
        self.set_vexpand(True)

        body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        body.add_css_class("hogwarts-panel")

        body.append(section_label("Agent package"))
        card1 = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        card1.add_css_class("hogwarts-card")
        c1t = Gtk.Label(
            label=(
                "Open Reach’s reverse export folder for Inverse Snowflake / "
                "dial-out agent packages and peer drops."
            ),
            wrap=True,
            xalign=0,
        )
        c1t.add_css_class("hogwarts-muted")
        card1.append(c1t)
        open_exp = Gtk.Button(label="Open export folder")
        open_exp.add_css_class("suggested-action")
        open_exp.set_halign(Gtk.Align.START)
        open_exp.connect("clicked", on_open_export)
        card1.append(open_exp)
        body.append(card1)

        body.append(section_label("Playbook"))
        card2 = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        card2.add_css_class("hogwarts-card")
        c2t = Gtk.Label(
            label=(
                "Export a JSON snapshot: listener notes, path state, plane "
                "config summary, and last egress results."
            ),
            wrap=True,
            xalign=0,
        )
        c2t.add_css_class("hogwarts-muted")
        card2.append(c2t)
        exp = Gtk.Button(label="Export playbook JSON")
        exp.add_css_class("suggested-action")
        exp.set_halign(Gtk.Align.START)
        exp.connect("clicked", on_export_playbook)
        card2.append(exp)
        self.playbook_path = Gtk.Label(label="", xalign=0, wrap=True, selectable=True)
        self.playbook_path.add_css_class("hogwarts-kv-val")
        card2.append(self.playbook_path)
        body.append(card2)

        body.append(section_label("Data"))
        card3 = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        card3.add_css_class("hogwarts-card")
        self.data_lab = Gtk.Label(xalign=0, wrap=True, selectable=True)
        self.data_lab.add_css_class("hogwarts-kv-val")
        self.data_lab.set_text(data_dir)
        card3.append(self.data_lab)
        open_data = Gtk.Button(label="Open plugin data folder")
        open_data.add_css_class("flat")
        open_data.set_halign(Gtk.Align.START)
        open_data.connect("clicked", on_open_data)
        card3.append(open_data)
        body.append(card3)

        self.append(scroll_panel(body))
