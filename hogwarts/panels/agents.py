"""Agents roster — live fleet from the control plane."""

from __future__ import annotations

from typing import Callable

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk  # noqa: E402

from hogwarts.backend.client import AgentDTO
from hogwarts.widgets import scroll_panel, section_label

_STATUS_FILTERS = ["All", "online", "idle", "offline"]


class AgentsPanel(Gtk.Box):
    def __init__(self, *, on_refresh: Callable) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.set_hexpand(True)
        self.set_vexpand(True)
        self._on_refresh = on_refresh
        self._agents: list[AgentDTO] = []
        self._selected: AgentDTO | None = None

        body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        body.add_css_class("hogwarts-panel")

        intro = Gtk.Label(
            label=(
                "Implant roster from your control plane. Configure Plane first; "
                "empty list means no check-ins yet — not demo data."
            ),
            wrap=True,
            xalign=0,
        )
        intro.add_css_class("hogwarts-muted")
        body.append(intro)

        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.search = Gtk.Entry()
        self.search.set_placeholder_text("Search hostname, user, id…")
        self.search.set_hexpand(True)
        self.search.connect("activate", lambda *_: on_refresh())
        bar.append(self.search)

        self.status_filter = Gtk.DropDown.new_from_strings(_STATUS_FILTERS)
        self.status_filter.set_selected(0)
        bar.append(self.status_filter)

        refresh = Gtk.Button(label="Refresh")
        refresh.add_css_class("suggested-action")
        refresh.connect("clicked", lambda *_: on_refresh())
        bar.append(refresh)
        body.append(bar)

        self.status_lab = Gtk.Label(label="", xalign=0)
        self.status_lab.add_css_class("hogwarts-muted")
        body.append(self.status_lab)

        split = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        split.set_hexpand(True)
        split.set_vexpand(True)

        left = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        left.set_hexpand(True)
        left.set_vexpand(True)
        left.append(section_label("Fleet"))
        self.list_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.list_box.set_hexpand(True)
        left.append(self.list_box)
        split.append(left)

        right = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        right.set_size_request(260, -1)
        right.append(section_label("Detail"))
        detail = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        detail.add_css_class("hogwarts-card")
        self.detail_host = Gtk.Label(label="Select an agent", xalign=0)
        self.detail_host.add_css_class("hogwarts-agent-host")
        detail.append(self.detail_host)
        self.detail_body = Gtk.Label(label="", xalign=0, wrap=True, selectable=True)
        self.detail_body.add_css_class("hogwarts-agent-meta")
        detail.append(self.detail_body)
        right.append(detail)
        split.append(right)

        body.append(split)
        self.append(scroll_panel(body))
        self.show_empty("Configure the control plane under Plane, then Refresh.")

    def filter_status(self) -> str | None:
        i = int(self.status_filter.get_selected())
        if i <= 0:
            return None
        return _STATUS_FILTERS[i]

    def query(self) -> str:
        return self.search.get_text().strip()

    def show_error(self, msg: str) -> None:
        self.status_lab.set_text(msg)
        self._clear_list()
        empty = Gtk.Label(label=msg, xalign=0, wrap=True)
        empty.add_css_class("hogwarts-fail")
        self.list_box.append(empty)

    def show_empty(self, msg: str) -> None:
        self.status_lab.set_text(msg)
        self._clear_list()
        empty = Gtk.Label(label=msg, xalign=0, wrap=True)
        empty.add_css_class("hogwarts-muted")
        self.list_box.append(empty)
        self._selected = None
        self.detail_host.set_text("No agent selected")
        self.detail_body.set_text("")

    def set_agents(self, agents: list[AgentDTO], *, note: str = "") -> None:
        self._agents = agents
        self._clear_list()
        if not agents:
            self.show_empty(note or "No agents reported by the control plane.")
            return
        counts: dict[str, int] = {}
        for a in agents:
            counts[a.status] = counts.get(a.status, 0) + 1
        parts = [f"{len(agents)} agent" + ("s" if len(agents) != 1 else "")]
        for st in ("online", "idle", "offline"):
            if st in counts:
                parts.append(f"{counts[st]} {st}")
        self.status_lab.set_text(" · ".join(parts) + (f" — {note}" if note else ""))
        for agent in agents:
            self.list_box.append(self._row(agent))
        if self._selected:
            match = next((a for a in agents if a.id == self._selected.id), None)
            if match:
                self._show_detail(match)
            else:
                self._show_detail(agents[0])
        else:
            self._show_detail(agents[0])

    def _clear_list(self) -> None:
        while child := self.list_box.get_first_child():
            self.list_box.remove(child)

    def _row(self, agent: AgentDTO) -> Gtk.Widget:
        btn = Gtk.Button()
        btn.add_css_class("flat")
        btn.set_hexpand(True)
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        outer.add_css_class("hogwarts-agent-row")

        top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        dot = Gtk.Box()
        dot.add_css_class("hogwarts-dot")
        status = (agent.status or "unknown").lower()
        if status == "online":
            dot.add_css_class("hogwarts-dot-live")
        elif status == "idle":
            dot.add_css_class("hogwarts-dot-busy")
        elif status == "offline":
            dot.add_css_class("hogwarts-dot-off")
        else:
            dot.add_css_class("hogwarts-dot-idle")
        dot.set_valign(Gtk.Align.CENTER)
        top.append(dot)

        host = Gtk.Label(label=agent.hostname or agent.id or "?", xalign=0)
        host.add_css_class("hogwarts-agent-host")
        host.set_hexpand(True)
        top.append(host)

        st = Gtk.Label(label=status.upper(), xalign=1)
        st.add_css_class(f"hogwarts-status-{status if status in ('online','idle','offline') else 'unknown'}")
        top.append(st)
        outer.append(top)

        meta_bits = [
            agent.username,
            agent.os,
            agent.external_ip,
            agent.group,
        ]
        meta = " · ".join(b for b in meta_bits if b) or agent.id
        mlab = Gtk.Label(label=meta, xalign=0)
        mlab.add_css_class("hogwarts-agent-meta")
        outer.append(mlab)

        btn.set_child(outer)
        btn.connect("clicked", lambda *_a, a=agent: self._show_detail(a))
        return btn

    def _show_detail(self, agent: AgentDTO) -> None:
        self._selected = agent
        self.detail_host.set_text(agent.hostname or agent.id or "Agent")
        lines = [
            f"id        {agent.id}",
            f"status    {agent.status}",
            f"user      {agent.username or '—'}",
            f"os        {agent.os or '—'} {agent.arch or ''}".rstrip(),
            f"external  {agent.external_ip or '—'}",
            f"internal  {agent.internal_ip or '—'}",
            f"group     {agent.group or '—'}",
            f"last_seen {agent.last_seen.isoformat() if agent.last_seen else '—'}",
        ]
        if agent.tags:
            lines.append(f"tags      {', '.join(str(t) for t in agent.tags)}")
        if agent.sleep is not None:
            lines.append(f"sleep     {agent.sleep}s  jitter {agent.jitter or 0}")
        self.detail_body.set_text("\n".join(lines))
