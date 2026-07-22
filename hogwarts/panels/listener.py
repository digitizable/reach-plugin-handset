"""Listener jobs — battlements as first-class operational objects (Havoc lesson).

Honest LED: green only when state=deployed AND evidence ∈
{tcp_ok, process_ok, plane_managed}. No invented “listening.”
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Callable

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk  # noqa: E402

from hogwarts.widgets import field, scroll_panel, section_label

# Transport face (legacy + display) — kind is the job taxonomy
_PROTOS = ["TCP", "TLS / 443 face", "PRR / Mirage", "Other"]
_STATES = ["planned", "deployed", "disabled", "burned"]
_EVIDENCE = ["none", "tcp_ok", "process_ok", "plane_managed", "unknown"]

# Job kinds (Havoc-class listener objects — no SMB/External in plane)
_KINDS: list[tuple[str, str]] = [
    ("reverse_tls", "reverse_tls"),
    ("reverse_tcp", "reverse_tcp"),
    ("path_wrapped", "path_wrapped"),
    ("http_plane", "http_plane"),
    ("note", "note (docs only)"),
    ("other", "other"),
]
_KIND_IDS = [k for k, _ in _KINDS]
_KIND_LABELS = [lab for _, lab in _KINDS]

_KIND_TO_PROTO = {
    "reverse_tls": "TLS / 443 face",
    "reverse_tcp": "TCP",
    "path_wrapped": "PRR / Mirage",
    "http_plane": "Other",
    "note": "Other",
    "other": "Other",
}


def _new_id() -> str:
    return f"lst_{uuid.uuid4().hex[:10]}"


def _utc_now() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _is_green(state: str, evidence: str) -> bool:
    return state == "deployed" and evidence in (
        "tcp_ok",
        "process_ok",
        "plane_managed",
    )


def _infer_kind(lst: dict[str, Any]) -> str:
    kind = str(lst.get("kind") or "").strip().lower()
    if kind in _KIND_IDS:
        return kind
    proto = str(lst.get("proto") or "").lower()
    if "tls" in proto or "443" in proto:
        return "reverse_tls"
    if "tcp" in proto and "tls" not in proto:
        return "reverse_tcp"
    if "path" in proto or "mirage" in proto or "prr" in proto:
        return "path_wrapped"
    return "other"


def _bind_str(lst: dict[str, Any]) -> str:
    host = str(lst.get("accept_host") or "?").strip() or "?"
    port = str(lst.get("accept_port") or "?").strip() or "?"
    return f"{host}:{port}"


class ListenerPanel(Gtk.Box):
    """Listener jobs — CRUD + lifecycle + evidence-gated LED."""

    def __init__(
        self,
        meta: dict[str, Any],
        *,
        on_save: Callable,
        on_copy: Callable,
        on_probe: Callable[[dict[str, Any]], None] | None = None,
        on_plane_pull: Callable[[], None] | None = None,
        on_plane_push: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.set_hexpand(True)
        self.set_vexpand(True)
        self._on_save = on_save
        self._on_copy = on_copy
        self._on_probe = on_probe
        self._on_plane_pull = on_plane_pull
        self._on_plane_push = on_plane_push
        self._listeners: list[dict[str, Any]] = []
        self._selected_id: str | None = None
        self._list_btns: dict[str, Gtk.Button] = {}
        self._list_labs: dict[str, Gtk.Label] = {}

        # Migrate legacy single-listener meta → list
        raw = meta.get("listeners")
        if isinstance(raw, list) and raw:
            self._listeners = [dict(x) for x in raw if isinstance(x, dict)]
        elif meta.get("accept_host") or meta.get("accept_port"):
            self._listeners = [
                {
                    "id": _new_id(),
                    "name": "primary",
                    "accept_host": str(meta.get("accept_host") or ""),
                    "accept_port": str(meta.get("accept_port") or "18443"),
                    "proto": str(meta.get("proto") or "TLS / 443 face"),
                    "face": str(meta.get("face") or ""),
                    "agent_id": str(meta.get("agent_id") or ""),
                    "state": "planned",
                    "evidence": "none",
                    "notes": str(meta.get("notes") or ""),
                    "kind": "reverse_tls",
                    "role": "",
                    "last_probe_at": "",
                    "last_probe_vantage": "",
                }
            ]
        for lst in self._listeners:
            if not lst.get("kind"):
                lst["kind"] = _infer_kind(lst)

        body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        body.add_css_class("hogwarts-panel")

        intro = Gtk.Label(
            label=(
                "Listener jobs (Havoc-class objects): bind + kind + state + evidence. "
                "Green LED only when state=deployed and evidence is tcp_ok / process_ok / "
                "plane_managed — never invent “listening.” "
                "Non-goal: no SMB / External listeners in the plane (use Reach path). "
                "Local plugin data + optional plane sync."
            ),
            wrap=True,
            xalign=0,
        )
        intro.add_css_class("hogwarts-muted")
        body.append(intro)

        self.summary = Gtk.Label(label="", xalign=0)
        self.summary.add_css_class("hogwarts-agent-meta")
        body.append(self.summary)

        split = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        split.set_hexpand(True)

        # List
        left = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        left.set_size_request(240, -1)
        left.append(section_label("Jobs"))
        self.list_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        left.append(self.list_box)
        list_btns = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        add_b = Gtk.Button(label="Add job")
        add_b.add_css_class("suggested-action")
        add_b.connect("clicked", lambda *_: self._add_new())
        list_btns.append(add_b)
        del_b = Gtk.Button(label="Delete")
        del_b.add_css_class("flat")
        del_b.connect("clicked", lambda *_: self._delete_selected())
        list_btns.append(del_b)
        left.append(list_btns)
        split.append(left)

        # Editor
        right = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        right.set_hexpand(True)
        right.append(section_label("Job"))
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        card.add_css_class("hogwarts-card")

        self.name = Gtk.Entry()
        self.name.set_placeholder_text("edge-1 · lab-accept")
        card.append(field("Name", self.name))

        kind_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.kind = Gtk.DropDown.new_from_strings(_KIND_LABELS)
        self.kind.set_selected(0)
        self.kind.set_hexpand(True)
        self.kind.set_tooltip_text(
            "Job kind — reverse_* for accept faces; path_wrapped docs Reach path; "
            "http_plane is plane face note (not reverse); note = docs only"
        )
        self.kind.connect("notify::selected", lambda *_: self._on_kind_changed())
        kind_row.append(field("Kind", self.kind))
        self.role = Gtk.Entry()
        self.role.set_placeholder_text("role · e.g. agent reverse · session face")
        self.role.set_hexpand(True)
        kind_row.append(field("Role", self.role))
        card.append(kind_row)

        self.accept_host = Gtk.Entry()
        self.accept_host.set_placeholder_text("accept.example.net or IP")
        card.append(field("Bind host", self.accept_host))

        port_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.accept_port = Gtk.Entry()
        self.accept_port.set_placeholder_text("18443")
        self.accept_port.set_hexpand(True)
        port_row.append(field("Bind port", self.accept_port))
        self.proto = Gtk.DropDown.new_from_strings(_PROTOS)
        self.proto.set_hexpand(True)
        self.proto.set_tooltip_text("Transport face label (synced from kind when possible)")
        port_row.append(field("Transport", self.proto))
        card.append(port_row)

        self.face = Gtk.Entry()
        self.face.set_placeholder_text("SNI / cover personality")
        card.append(field("Cover face", self.face))

        self.agent_id = Gtk.Entry()
        self.agent_id.set_placeholder_text("linked foothold id (optional)")
        card.append(field("Agent / foothold id", self.agent_id))

        # Lifecycle strip (job language)
        life = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        life.add_css_class("hogwarts-action-strip")
        for st, label, tip in (
            ("planned", "Plan", "Mark planned — LED off"),
            ("deployed", "Deploy", "Mark deployed — green only if evidence ok"),
            ("disabled", "Disable", "Take offline without burn"),
            ("burned", "Burn", "Burn face — clear evidence"),
        ):
            b = Gtk.Button(label=label)
            b.add_css_class("flat")
            b.set_tooltip_text(tip)
            b.connect("clicked", lambda *_a, s=st: self._set_lifecycle(s))
            life.append(b)
        card.append(field("Lifecycle", life))

        st_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.state = Gtk.DropDown.new_from_strings(_STATES)
        self.state.set_hexpand(True)
        self.state.connect("notify::selected", lambda *_: self._update_led())
        st_row.append(field("State", self.state))
        self.evidence = Gtk.DropDown.new_from_strings(_EVIDENCE)
        self.evidence.set_hexpand(True)
        self.evidence.set_tooltip_text(
            "Honest evidence only — Probe TCP sets tcp_ok from this desk"
        )
        self.evidence.connect("notify::selected", lambda *_: self._update_led())
        st_row.append(field("Evidence", self.evidence))
        card.append(st_row)

        self.led = Gtk.Label(label="LED · off", xalign=0)
        self.led.add_css_class("hogwarts-muted")
        card.append(self.led)

        self.probe_meta = Gtk.Label(label="Last probe  —", xalign=0, wrap=True)
        self.probe_meta.add_css_class("hogwarts-agent-meta")
        card.append(self.probe_meta)

        self.job_id_lab = Gtk.Label(label="job_id  —", xalign=0, selectable=True)
        self.job_id_lab.add_css_class("hogwarts-agent-meta")
        card.append(self.job_id_lab)

        self.notes = Gtk.TextView()
        self.notes.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.notes.set_top_margin(8)
        self.notes.set_bottom_margin(8)
        self.notes.set_left_margin(10)
        self.notes.set_right_margin(10)
        self.notes.set_size_request(-1, 72)
        card.append(field("Ops notes", self.notes))
        right.append(card)

        save_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        save_b = Gtk.Button(label="Save job")
        save_b.add_css_class("suggested-action")
        save_b.connect("clicked", lambda *_: self._save_editor())
        save_row.append(save_b)
        copy_b = Gtk.Button(label="Copy job line")
        copy_b.add_css_class("flat")
        copy_b.connect("clicked", self._copy)
        save_row.append(copy_b)
        probe_b = Gtk.Button(label="Probe TCP")
        probe_b.add_css_class("flat")
        probe_b.set_tooltip_text(
            "TCP connect from this desk (vantage=desk); sets evidence tcp_ok/none"
        )
        probe_b.connect("clicked", lambda *_: self._probe())
        save_row.append(probe_b)
        right.append(save_row)

        plane_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        pull_b = Gtk.Button(label="Pull from plane")
        pull_b.add_css_class("flat")
        pull_b.set_tooltip_text("Replace local jobs with GET /api/v1/listeners")
        pull_b.connect(
            "clicked",
            lambda *_: self._on_plane_pull() if self._on_plane_pull else None,
        )
        plane_row.append(pull_b)
        push_b = Gtk.Button(label="Push to plane")
        push_b.add_css_class("flat")
        push_b.set_tooltip_text("Upsert all local jobs to the plane")
        push_b.connect(
            "clicked",
            lambda *_: self._on_plane_push() if self._on_plane_push else None,
        )
        plane_row.append(push_b)
        right.append(plane_row)

        self.status = Gtk.Label(label="", xalign=0, wrap=True)
        self.status.add_css_class("hogwarts-muted")
        right.append(self.status)

        split.append(right)
        body.append(split)
        self.append(scroll_panel(body))

        if self._listeners:
            self._select(self._listeners[0]["id"])
        else:
            self._rebuild_list()
            self._clear_editor()
        self._update_summary()

    # ── List / rows ────────────────────────────────────────────

    @staticmethod
    def _row_label_text(lst: dict[str, Any]) -> str:
        green = _is_green(
            str(lst.get("state") or ""), str(lst.get("evidence") or "")
        )
        title = str(lst.get("name") or lst.get("id") or "?")
        kind = _infer_kind(lst)
        bind = _bind_str(lst)
        st = str(lst.get("state") or "?")
        ev = str(lst.get("evidence") or "none")
        led = "●" if green else "○"
        return f"{led} {title}\n{kind} · {bind} · {st}/{ev}"

    def _update_summary(self) -> None:
        n = len(self._listeners)
        green = sum(
            1
            for lst in self._listeners
            if _is_green(str(lst.get("state") or ""), str(lst.get("evidence") or ""))
        )
        planned = sum(
            1 for lst in self._listeners if str(lst.get("state") or "") == "planned"
        )
        burned = sum(
            1 for lst in self._listeners if str(lst.get("state") or "") == "burned"
        )
        parts = [f"{n} job" + ("s" if n != 1 else "")]
        if green:
            parts.append(f"{green} green")
        if planned:
            parts.append(f"{planned} planned")
        if burned:
            parts.append(f"{burned} burned")
        want = " · ".join(parts) if n else "No jobs — Add one"
        if self.summary.get_text() != want:
            self.summary.set_text(want)

    def _rebuild_list(self) -> None:
        while child := self.list_box.get_first_child():
            self.list_box.remove(child)
        self._list_btns = {}
        self._list_labs: dict[str, Gtk.Label] = {}
        if not self._listeners:
            empty = Gtk.Label(label="No jobs — Add one.", xalign=0)
            empty.add_css_class("hogwarts-muted")
            self.list_box.append(empty)
            self._update_summary()
            return
        for lst in self._listeners:
            btn = Gtk.Button()
            btn.add_css_class("flat")
            btn.add_css_class("hogwarts-fleet-btn")
            btn.set_hexpand(True)
            green = _is_green(
                str(lst.get("state") or ""), str(lst.get("evidence") or "")
            )
            lab = Gtk.Label(label=self._row_label_text(lst), xalign=0)
            lab.add_css_class("hogwarts-agent-meta")
            lab.set_can_target(False)
            if green:
                lab.add_css_class("hogwarts-ok")
            btn.set_child(lab)
            lid = str(lst.get("id") or "")
            btn.connect("clicked", lambda *_a, i=lid: self._select(i))
            if lid and lid == self._selected_id:
                btn.add_css_class("hogwarts-fleet-btn-selected")
            self.list_box.append(btn)
            if lid:
                self._list_btns[lid] = btn
                self._list_labs[lid] = lab
        self._update_summary()

    def _mark_selected(self, lid: str | None) -> None:
        btns = getattr(self, "_list_btns", None) or {}
        for bid, btn in btns.items():
            if lid and bid == lid:
                btn.add_css_class("hogwarts-fleet-btn-selected")
            else:
                btn.remove_css_class("hogwarts-fleet-btn-selected")

    def _soft_refresh_rows(self) -> None:
        labs = getattr(self, "_list_labs", None) or {}
        btns = getattr(self, "_list_btns", None) or {}
        ids = {str(lst.get("id") or "") for lst in self._listeners if lst.get("id")}
        if set(btns.keys()) != ids or not btns:
            self._rebuild_list()
            self._mark_selected(self._selected_id)
            return
        by_id = {str(lst.get("id") or ""): lst for lst in self._listeners}
        for lid, lab in labs.items():
            lst = by_id.get(lid)
            if not lst:
                continue
            want = self._row_label_text(lst)
            if lab.get_text() != want:
                lab.set_text(want)
            green = _is_green(
                str(lst.get("state") or ""), str(lst.get("evidence") or "")
            )
            if green:
                lab.add_css_class("hogwarts-ok")
            else:
                lab.remove_css_class("hogwarts-ok")
        self._mark_selected(self._selected_id)
        self._update_summary()

    # ── Editor ─────────────────────────────────────────────────

    def _clear_editor(self) -> None:
        self._selected_id = None
        self.name.set_text("")
        self.accept_host.set_text("")
        self.accept_port.set_text("18443")
        self.proto.set_selected(1)
        self.kind.set_selected(0)
        self.role.set_text("")
        self.face.set_text("")
        self.agent_id.set_text("")
        self.state.set_selected(0)
        self.evidence.set_selected(0)
        self.notes.get_buffer().set_text("")
        self.probe_meta.set_text("Last probe  —")
        self.job_id_lab.set_text("job_id  —")
        self._update_led()

    def _select(self, lid: str) -> None:
        self._flush_editor_to_model()
        lst = next((x for x in self._listeners if x.get("id") == lid), None)
        if not lst:
            return
        self._selected_id = lid
        self.name.set_text(str(lst.get("name") or ""))
        self.accept_host.set_text(str(lst.get("accept_host") or ""))
        self.accept_port.set_text(str(lst.get("accept_port") or "18443"))
        kind = _infer_kind(lst)
        try:
            self.kind.set_selected(_KIND_IDS.index(kind))
        except ValueError:
            self.kind.set_selected(len(_KIND_IDS) - 1)
        self.role.set_text(str(lst.get("role") or ""))
        proto = str(lst.get("proto") or _KIND_TO_PROTO.get(kind, "Other"))
        try:
            self.proto.set_selected(_PROTOS.index(proto))
        except ValueError:
            self.proto.set_selected(1)
        self.face.set_text(str(lst.get("face") or ""))
        self.agent_id.set_text(str(lst.get("agent_id") or ""))
        st = str(lst.get("state") or "planned")
        try:
            self.state.set_selected(_STATES.index(st))
        except ValueError:
            self.state.set_selected(0)
        ev = str(lst.get("evidence") or "none")
        try:
            self.evidence.set_selected(_EVIDENCE.index(ev))
        except ValueError:
            self.evidence.set_selected(0)
        self.notes.get_buffer().set_text(str(lst.get("notes") or ""))
        at = str(lst.get("last_probe_at") or "")
        vant = str(lst.get("last_probe_vantage") or "")
        if at:
            self.probe_meta.set_text(
                f"Last probe  {at}" + (f" · vantage {vant}" if vant else "")
            )
        else:
            self.probe_meta.set_text("Last probe  — (Probe TCP from this desk)")
        self.job_id_lab.set_text(f"job_id  {lid}")
        self._update_led()
        if not getattr(self, "_list_btns", None):
            self._rebuild_list()
        else:
            self._mark_selected(lid)

    def _selected_kind_id(self) -> str:
        i = int(self.kind.get_selected())
        if i < 0 or i >= len(_KIND_IDS):
            return "other"
        return _KIND_IDS[i]

    def _on_kind_changed(self) -> None:
        kind = self._selected_kind_id()
        want_proto = _KIND_TO_PROTO.get(kind, "Other")
        try:
            self.proto.set_selected(_PROTOS.index(want_proto))
        except ValueError:
            pass
        self._update_led()

    def _update_led(self) -> None:
        st = _STATES[int(self.state.get_selected())]
        ev = _EVIDENCE[int(self.evidence.get_selected())]
        kind = self._selected_kind_id()
        if _is_green(st, ev):
            self.led.set_text(f"LED · GREEN  (deployed + {ev} · {kind})")
            self.led.remove_css_class("hogwarts-muted")
            self.led.add_css_class("hogwarts-ok")
        elif st == "deployed" and ev not in (
            "tcp_ok",
            "process_ok",
            "plane_managed",
        ):
            self.led.set_text(
                f"LED · off  (deployed but no evidence — Probe or set process_ok)"
            )
            self.led.remove_css_class("hogwarts-ok")
            self.led.add_css_class("hogwarts-muted")
        else:
            self.led.set_text(f"LED · off  ({st} / {ev} · {kind})")
            self.led.remove_css_class("hogwarts-ok")
            self.led.add_css_class("hogwarts-muted")

    def _editor_snapshot(self) -> dict[str, Any]:
        buf = self.notes.get_buffer()
        notes = buf.get_text(buf.get_start_iter(), buf.get_end_iter(), False)
        kind = self._selected_kind_id()
        # Preserve probe meta from model if present
        prev = next(
            (x for x in self._listeners if x.get("id") == self._selected_id),
            {},
        )
        return {
            "id": self._selected_id or _new_id(),
            "name": self.name.get_text().strip() or "listener",
            "accept_host": self.accept_host.get_text().strip(),
            "accept_port": self.accept_port.get_text().strip() or "18443",
            "proto": _PROTOS[int(self.proto.get_selected())],
            "face": self.face.get_text().strip(),
            "agent_id": self.agent_id.get_text().strip(),
            "state": _STATES[int(self.state.get_selected())],
            "evidence": _EVIDENCE[int(self.evidence.get_selected())],
            "notes": notes.strip(),
            "kind": kind,
            "role": self.role.get_text().strip(),
            "last_probe_at": str(prev.get("last_probe_at") or ""),
            "last_probe_vantage": str(prev.get("last_probe_vantage") or ""),
        }

    def _flush_editor_to_model(self) -> None:
        if not self._selected_id:
            return
        snap = self._editor_snapshot()
        snap["id"] = self._selected_id
        for i, lst in enumerate(self._listeners):
            if lst.get("id") == self._selected_id:
                self._listeners[i] = snap
                break

    def _set_lifecycle(self, state: str) -> None:
        """Job lifecycle action — honest evidence rules preserved."""
        if state not in _STATES:
            return
        if not self._selected_id:
            self.status.set_text("Select or Add a job first")
            return
        try:
            self.state.set_selected(_STATES.index(state))
        except ValueError:
            return
        if state == "burned":
            # Burn clears live evidence — face is gone
            self.evidence.set_selected(_EVIDENCE.index("none"))
        self._update_led()
        self._flush_editor_to_model()
        self._soft_refresh_rows()
        st = state
        ev = _EVIDENCE[int(self.evidence.get_selected())]
        if st == "deployed" and not _is_green(st, ev):
            self.status.set_text(
                "Deployed without evidence — LED stays off until Probe / process_ok"
            )
        elif st == "burned":
            self.status.set_text("Burned — evidence cleared; LED off")
        else:
            self.status.set_text(f"Lifecycle → {st}")
        self._on_save(quiet=True)

    def _add_new(self) -> None:
        self._flush_editor_to_model()
        lid = _new_id()
        self._listeners.append(
            {
                "id": lid,
                "name": f"job-{len(self._listeners)+1}",
                "accept_host": "127.0.0.1",
                "accept_port": "18443",
                "proto": "TLS / 443 face",
                "face": "",
                "agent_id": "",
                "state": "planned",
                "evidence": "none",
                "notes": "",
                "kind": "reverse_tls",
                "role": "",
                "last_probe_at": "",
                "last_probe_vantage": "",
            }
        )
        self._rebuild_list()
        self._select(lid)
        self.status.set_text("Added job (Save to persist)")

    def _delete_selected(self) -> None:
        if not self._selected_id:
            return
        self._listeners = [
            x for x in self._listeners if x.get("id") != self._selected_id
        ]
        self._selected_id = None
        self._rebuild_list()
        if self._listeners:
            self._select(str(self._listeners[0]["id"]))
        else:
            self._clear_editor()
        self._on_save(quiet=False)
        self.status.set_text("Deleted job")

    def _save_editor(self) -> None:
        if not self._selected_id:
            self._add_new()
            return
        self._flush_editor_to_model()
        self._update_led()
        self._soft_refresh_rows()
        self._on_save(quiet=False)
        snap = self._editor_snapshot()
        self.status.set_text(
            f"Saved job {snap.get('id')} · {_infer_kind(snap)} · {_bind_str(snap)}"
        )

    def _copy(self, *_a) -> None:
        self._flush_editor_to_model()
        self._on_copy()

    def _probe(self) -> None:
        self._flush_editor_to_model()
        snap = self._editor_snapshot()
        if self._on_probe:
            self._on_probe(snap)
        else:
            self.status.set_text("Probe not wired")

    def replace_listeners(self, rows: list[dict[str, Any]]) -> None:
        """Replace local list (e.g. after plane pull)."""
        self._listeners = [dict(x) for x in rows if isinstance(x, dict)]
        for lst in self._listeners:
            if not lst.get("id"):
                lst["id"] = _new_id()
            if not lst.get("kind"):
                lst["kind"] = _infer_kind(lst)
        if self._listeners:
            self._select(str(self._listeners[0]["id"]))
        else:
            self._clear_editor()
            self._rebuild_list()
        self._update_summary()

    def set_probe_result(
        self, listener_id: str, *, ok: bool, detail: str = ""
    ) -> None:
        now = _utc_now()
        for i, lst in enumerate(self._listeners):
            if lst.get("id") == listener_id:
                lst["evidence"] = "tcp_ok" if ok else "none"
                lst["last_probe_at"] = now
                lst["last_probe_vantage"] = "desk"
                # Auto-promote planned → deployed only on successful probe
                if ok and lst.get("state") == "planned":
                    lst["state"] = "deployed"
                self._listeners[i] = lst
                if self._selected_id == listener_id:
                    self._select(listener_id)
                break
        self._soft_refresh_rows()
        self.status.set_text(
            f"Probe {'ok' if ok else 'fail'} (vantage=desk): {detail}"
            if detail
            else ("Probe ok · vantage=desk" if ok else "Probe fail · vantage=desk")
        )
        self._on_save(quiet=True)

    # ── Host compatibility (page.py) ──────────────────────────

    def snapshot(self) -> dict[str, Any]:
        """Persist list + legacy primary fields for older exports."""
        self._flush_editor_to_model()
        primary = self._listeners[0] if self._listeners else {}
        return {
            "listeners": list(self._listeners),
            "accept_host": str(primary.get("accept_host") or ""),
            "accept_port": str(primary.get("accept_port") or ""),
            "face": str(primary.get("face") or ""),
            "agent_id": str(primary.get("agent_id") or ""),
            "proto": str(primary.get("proto") or ""),
            "notes": str(primary.get("notes") or ""),
        }

    def listener_line(self) -> str:
        """One-line job summary for clipboard / session log."""
        self._flush_editor_to_model()
        if self._selected_id:
            lst = next(
                (x for x in self._listeners if x.get("id") == self._selected_id),
                None,
            )
        else:
            lst = self._listeners[0] if self._listeners else None
        if not lst:
            return "(no listener job)"
        jid = str(lst.get("id") or "?")
        kind = _infer_kind(lst)
        bind = _bind_str(lst)
        face = str(lst.get("face") or "—")
        role = str(lst.get("role") or "")
        st = str(lst.get("state") or "?")
        ev = str(lst.get("evidence") or "?")
        led = "GREEN" if _is_green(st, ev) else "off"
        probe = str(lst.get("last_probe_at") or "")
        vant = str(lst.get("last_probe_vantage") or "")
        bits = [
            f"job {jid}",
            kind,
            f"bind {bind}",
            f"{st}/{ev}",
            f"LED {led}",
        ]
        if role:
            bits.append(f"role {role}")
        if face and face != "—":
            bits.append(f"face {face}")
        if probe:
            bits.append(f"probe {probe}" + (f"@{vant}" if vant else ""))
        return " · ".join(bits)
