"""Control-plane settings panel."""

from __future__ import annotations

from typing import Callable

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk  # noqa: E402

from hogwarts.backend.config import PlaneConfig
from hogwarts.widgets import field, scroll_panel, section_label


class PlanePanel(Gtk.Box):
    def __init__(
        self,
        cfg: PlaneConfig,
        *,
        on_save: Callable,
        on_test: Callable,
    ) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.set_hexpand(True)
        self.set_vexpand(True)

        body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        body.add_css_class("hogwarts-panel")

        intro = Gtk.Label(
            label=(
                "Point Hogwarts at your C2 control plane. Only operator credentials "
                "live here — never implant secrets. See hogwarts/backend/CONTRACT.md."
            ),
            wrap=True,
            xalign=0,
        )
        intro.add_css_class("hogwarts-muted")
        body.append(intro)

        body.append(section_label("Connection"))
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        card.add_css_class("hogwarts-card")

        self.base_url = Gtk.Entry()
        self.base_url.set_placeholder_text("https://c2.example.internal")
        self.base_url.set_text(cfg.base_url)
        card.append(field("Base URL", self.base_url))

        # Gtk.PasswordEntry has no set_placeholder_text (only a GObject prop);
        # Entry + visibility=False is portable and supports placeholders.
        self.api_token = Gtk.Entry()
        self.api_token.set_visibility(False)
        self.api_token.set_input_purpose(Gtk.InputPurpose.PASSWORD)
        self.api_token.set_placeholder_text("Bearer token (optional if open API)")
        self.api_token.set_text(cfg.api_token)
        card.append(field("API token", self.api_token))

        self.poll = Gtk.Entry()
        self.poll.set_placeholder_text("5")
        self.poll.set_text(str(cfg.poll_interval_sec))
        self.poll.set_width_chars(6)
        card.append(field("Poll interval (sec)", self.poll))
        body.append(card)

        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        save = Gtk.Button(label="Save plane")
        save.add_css_class("suggested-action")
        save.connect("clicked", lambda *_: on_save())
        row.append(save)
        test = Gtk.Button(label="Test health")
        test.add_css_class("flat")
        test.connect("clicked", lambda *_: on_test())
        row.append(test)
        body.append(row)

        self.result = Gtk.Label(label="", xalign=0, wrap=True, selectable=True)
        self.result.add_css_class("hogwarts-kv-val")
        body.append(self.result)

        body.append(section_label("API surface"))
        api = Gtk.Label(
            label=(
                "GET /api/v1/health\n"
                "GET /api/v1/agents\n"
                "GET /api/v1/events\n"
                "POST /api/v1/agents/{id}/tasks  (future interact)"
            ),
            xalign=0,
        )
        api.add_css_class("hogwarts-agent-meta")
        body.append(api)

        self.append(scroll_panel(body))

    def read_config(self) -> PlaneConfig:
        try:
            poll = float(self.poll.get_text().strip() or "5")
        except ValueError:
            poll = 5.0
        return PlaneConfig(
            base_url=self.base_url.get_text().strip(),
            api_token=self.api_token.get_text().strip(),
            poll_interval_sec=max(1.0, poll),
        )

    def set_result(self, text: str, *, ok: bool | None = None) -> None:
        self.result.set_text(text)
        self.result.remove_css_class("hogwarts-ok")
        self.result.remove_css_class("hogwarts-fail")
        if ok is True:
            self.result.add_css_class("hogwarts-ok")
        elif ok is False:
            self.result.add_css_class("hogwarts-fail")
