"""Listener notes panel."""

from __future__ import annotations

from typing import Any, Callable

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk  # noqa: E402

from hogwarts.widgets import field, scroll_panel, section_label

_PROTOS = ["TCP", "TLS / 443 face", "PRR / Mirage", "Other"]


class ListenerPanel(Gtk.Box):
    def __init__(
        self,
        meta: dict[str, Any],
        *,
        on_save: Callable,
        on_copy: Callable,
    ) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.set_hexpand(True)
        self.set_vexpand(True)

        body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        body.add_css_class("hogwarts-panel")

        intro = Gtk.Label(
            label=(
                "Document your accept / reverse face. These notes feed the "
                "playbook export and stay on this machine under plugin data."
            ),
            wrap=True,
            xalign=0,
        )
        intro.add_css_class("hogwarts-muted")
        body.append(intro)

        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        card.add_css_class("hogwarts-card")

        self.accept_host = Gtk.Entry()
        self.accept_host.set_placeholder_text("accept.example.net or IP")
        self.accept_host.set_text(str(meta.get("accept_host") or ""))
        card.append(field("Accept host", self.accept_host))

        port_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.accept_port = Gtk.Entry()
        self.accept_port.set_placeholder_text("18443")
        self.accept_port.set_text(str(meta.get("accept_port") or "18443"))
        self.accept_port.set_hexpand(True)
        port_row.append(field("Port", self.accept_port))
        self.proto = Gtk.DropDown.new_from_strings(_PROTOS)
        proto = str(meta.get("proto") or "TLS / 443 face")
        try:
            idx = _PROTOS.index(proto)
        except ValueError:
            idx = 1
        self.proto.set_selected(idx)
        self.proto.set_hexpand(True)
        port_row.append(field("Transport", self.proto))
        card.append(port_row)

        self.face = Gtk.Entry()
        self.face.set_placeholder_text("SNI / cover personality / REALITY dest")
        self.face.set_text(str(meta.get("face") or ""))
        card.append(field("Cover face", self.face))

        self.agent_id = Gtk.Entry()
        self.agent_id.set_placeholder_text("peer-1 · lab-vm · travel")
        self.agent_id.set_text(str(meta.get("agent_id") or ""))
        card.append(field("Agent / foothold id", self.agent_id))

        self.notes = Gtk.TextView()
        self.notes.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.notes.set_top_margin(8)
        self.notes.set_bottom_margin(8)
        self.notes.set_left_margin(10)
        self.notes.set_right_margin(10)
        self.notes.set_size_request(-1, 100)
        self.notes.get_buffer().set_text(str(meta.get("notes") or ""))
        card.append(field("Ops notes", self.notes))
        body.append(card)

        body.append(section_label("Quick fill"))
        presets = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        for name, host, port, face in (
            ("Lab accept", "127.0.0.1", "18443", "localhost PRR"),
            ("Cloud 443", "", "443", "TLS face / CDN"),
            ("Clear", "", "18443", ""),
        ):
            b = Gtk.Button(label=name)
            b.add_css_class("flat")
            b.connect(
                "clicked",
                lambda *_a, h=host, p=port, f=face: self.apply_preset(h, p, f),
            )
            presets.append(b)
        body.append(presets)

        save_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        save_row.set_margin_top(4)
        save_b = Gtk.Button(label="Save listener")
        save_b.add_css_class("suggested-action")
        save_b.connect("clicked", lambda *_: on_save(quiet=False))
        save_row.append(save_b)
        copy_b = Gtk.Button(label="Copy listener line")
        copy_b.add_css_class("flat")
        copy_b.connect("clicked", on_copy)
        save_row.append(copy_b)
        body.append(save_row)

        self.append(scroll_panel(body))

    def apply_preset(self, host: str, port: str, face: str) -> None:
        self.accept_host.set_text(host)
        self.accept_port.set_text(port)
        self.face.set_text(face)

    def notes_text(self) -> str:
        buf = self.notes.get_buffer()
        return buf.get_text(buf.get_start_iter(), buf.get_end_iter(), False)

    def proto_str(self) -> str:
        i = int(self.proto.get_selected())
        return _PROTOS[max(0, min(i, len(_PROTOS) - 1))]

    def snapshot(self) -> dict[str, str]:
        return {
            "accept_host": self.accept_host.get_text().strip(),
            "accept_port": self.accept_port.get_text().strip(),
            "face": self.face.get_text().strip(),
            "agent_id": self.agent_id.get_text().strip(),
            "proto": self.proto_str(),
            "notes": self.notes_text().strip(),
        }

    def listener_line(self) -> str:
        host = self.accept_host.get_text().strip() or "?"
        port = self.accept_port.get_text().strip() or "?"
        face = self.face.get_text().strip() or "—"
        return f"{host}:{port} · {self.proto_str()} · {face}"
