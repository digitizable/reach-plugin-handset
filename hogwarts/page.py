"""Hogwarts main page — two-pane C2 desk shell."""

from __future__ import annotations

import json
import subprocess
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gdk, GLib, Gtk  # noqa: E402

from hogwarts import __version__
from hogwarts.backend.client import C2Client
from hogwarts.backend.config import PlaneConfig, load_plane_config, save_plane_config
from hogwarts.net import socks_tcp_probe, tcp_probe
from hogwarts.panels.agents import AgentsPanel
from hogwarts.panels.channel import ChannelPanel
from hogwarts.panels.console import ConsolePanel
from hogwarts.panels.egress import EgressPanel
from hogwarts.panels.listener import ListenerPanel
from hogwarts.panels.log import LogPanel
from hogwarts.panels.ops import OpsPanel
from hogwarts.panels.plane import PlanePanel
from hogwarts.store import MetaStore
from hogwarts.theme import apply_css


class HogwartsPage(Gtk.Box):
    """Two-pane C2 desk: Channel · Agents · Listener · Egress · Console · Plane · Ops · Log."""

    def __init__(self, ctx) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.add_css_class("page")
        self.add_css_class("hogwarts-page")
        self.set_hexpand(True)
        self.set_vexpand(True)
        self._ctx = ctx
        self._probe_busy = False
        self._log_lines: list[str] = []
        self._store = MetaStore(ctx.data_path("hogwarts.json"))
        self._plane_path = ctx.data_path("plane.json")
        self._plane = load_plane_config(self._plane_path)
        apply_css(self)

        # Header
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        header.add_css_class("hogwarts-header")
        header.set_hexpand(True)
        titles = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        titles.set_hexpand(True)
        titles.set_valign(Gtk.Align.CENTER)
        t = Gtk.Label(label="Hogwarts", xalign=0)
        t.add_css_class("hogwarts-title")
        titles.append(t)
        s = Gtk.Label(label="C2 keep · channel · agents · plane", xalign=0)
        s.add_css_class("hogwarts-sub")
        titles.append(s)
        header.append(titles)

        self._chip = Gtk.Label(label="—")
        self._chip.add_css_class("hogwarts-chip")
        self._chip.set_valign(Gtk.Align.CENTER)
        header.append(self._chip)

        self._plane_chip = Gtk.Label(label="PLANE OFF")
        self._plane_chip.add_css_class("hogwarts-chip")
        self._plane_chip.set_valign(Gtk.Align.CENTER)
        header.append(self._plane_chip)

        refresh = Gtk.Button()
        refresh.set_icon_name("view-refresh-symbolic")
        refresh.add_css_class("flat")
        refresh.set_tooltip_text("Refresh channel + plane")
        refresh.set_valign(Gtk.Align.CENTER)
        refresh.connect("clicked", lambda *_: self._refresh_all())
        header.append(refresh)
        self.append(header)

        # Split body
        split = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        split.add_css_class("hogwarts-split")
        split.set_hexpand(True)
        split.set_vexpand(True)

        side = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        side.add_css_class("hogwarts-sidebar")
        side.set_vexpand(True)
        side.set_hexpand(False)
        side.set_size_request(210, -1)

        side_lab = Gtk.Label(label="Desk", xalign=0)
        side_lab.add_css_class("hogwarts-section")
        side_lab.set_margin_start(8)
        side_lab.set_margin_bottom(6)
        side.append(side_lab)

        self._stack = Gtk.Stack()
        self._stack.add_css_class("hogwarts-stack")
        self._stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self._stack.set_transition_duration(160)
        self._stack.set_hexpand(True)
        self._stack.set_vexpand(True)
        self._stack.set_halign(Gtk.Align.FILL)
        self._stack.set_valign(Gtk.Align.FILL)

        meta = self._store.load()
        self._channel = ChannelPanel(
            on_copy_socks=self._copy_socks,
            on_run_egress=lambda *_: self._run_probes(),
            on_open_export=self._open_export,
            on_save_listener=lambda *_: self._save_listener(quiet=False),
            on_export_playbook=self._export_playbook,
            on_marketplace=lambda *_: self._go_marketplace(),
        )
        self._agents = AgentsPanel(on_refresh=self._refresh_agents)
        self._listener = ListenerPanel(
            meta,
            on_save=self._save_listener,
            on_copy=self._copy_listener_line,
        )
        last_rows = meta.get("last_probe_rows")
        self._egress = EgressPanel(
            on_run=self._run_probes,
            on_custom=self._probe_custom,
            last_rows=last_rows if isinstance(last_rows, list) else None,
            last_ts=str(meta.get("last_probe_ts") or ""),
        )
        self._console = ConsolePanel(on_command=self._console_command)
        self._plane_panel = PlanePanel(
            self._plane,
            on_save=self._save_plane,
            on_test=self._test_plane,
        )
        self._ops = OpsPanel(
            str(self._ctx.data_path()),
            on_open_export=self._open_export,
            on_export_playbook=self._export_playbook,
            on_open_data=self._open_data,
        )
        self._log = LogPanel(on_clear=self._clear_log)

        nav_items = (
            ("channel", "Channel", "network-wired-symbolic", self._channel),
            ("agents", "Agents", "system-users-symbolic", self._agents),
            ("listener", "Listener", "network-server-symbolic", self._listener),
            ("egress", "Egress", "network-transmit-receive-symbolic", self._egress),
            ("console", "Console", "utilities-terminal-symbolic", self._console),
            ("plane", "Plane", "network-workgroup-symbolic", self._plane_panel),
            ("ops", "Ops kit", "folder-symbolic", self._ops),
            ("log", "Session log", "document-open-recent-symbolic", self._log),
        )

        self._nav_group: Gtk.ToggleButton | None = None
        for key, label, icon, widget in nav_items:
            widget.set_hexpand(True)
            widget.set_vexpand(True)
            widget.set_halign(Gtk.Align.FILL)
            widget.set_valign(Gtk.Align.FILL)
            self._stack.add_named(widget, key)
            btn = Gtk.ToggleButton()
            btn.add_css_class("hogwarts-nav-btn")
            btn.set_hexpand(True)
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            row.set_margin_start(4)
            ic = Gtk.Image.new_from_icon_name(icon)
            ic.set_pixel_size(16)
            row.append(ic)
            lab = Gtk.Label(label=label, xalign=0)
            lab.set_hexpand(True)
            row.append(lab)
            btn.set_child(row)
            if self._nav_group is None:
                self._nav_group = btn
                btn.set_active(True)
            else:
                btn.set_group(self._nav_group)
            btn.connect("toggled", self._on_nav, key)
            side.append(btn)

        spacer = Gtk.Box()
        spacer.set_vexpand(True)
        side.append(spacer)
        ver = Gtk.Label(label=f"v{__version__}", xalign=0.5)
        ver.add_css_class("hogwarts-muted")
        ver.set_margin_bottom(4)
        side.append(ver)

        split.append(side)
        main = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        main.add_css_class("hogwarts-main")
        main.set_hexpand(True)
        main.set_vexpand(True)
        main.append(self._stack)
        split.append(main)
        self.append(split)

        self._stack.set_visible_child_name("channel")
        self._refresh_all()
        self._log_msg("Hogwarts ready")

    def _on_nav(self, btn: Gtk.ToggleButton, key: str) -> None:
        if btn.get_active():
            self._stack.set_visible_child_name(key)

    def _client(self) -> C2Client:
        return C2Client(self._plane)

    def _refresh_all(self) -> None:
        self._refresh_status()
        if self._plane.is_configured:
            self._refresh_agents(quiet=True)

    def _refresh_status(self) -> None:
        state = "offline"
        state_label = "Core offline"
        path = "—"
        socks = "—"
        hops = "—"
        fp = "—"
        try:
            st = self._ctx.services.core.status(force=True)
            sv = getattr(getattr(st, "state", None), "value", str(getattr(st, "state", "")))
            path = str(getattr(st, "path_summary", None) or "—")
            socks = str(getattr(st, "local_proxy", None) or "").strip() or "—"
            hl = list(getattr(st, "hops", None) or [])
            hops = " → ".join(hl) if hl else "—"
            fp = str(getattr(st, "fingerprint_note", None) or "—").strip() or "—"
            if sv == "connected":
                state = "live"
                state_label = "Path up"
            elif sv == "connecting":
                state = "busy"
                state_label = "Connecting…"
            elif sv == "disconnected":
                state = "idle"
                state_label = "Not connected"
            else:
                state = "off"
                state_label = sv or "Unknown"
        except Exception as exc:
            state = "off"
            state_label = "Unavailable"
            path = str(exc)

        plane_txt = "not configured"
        if self._plane.is_configured:
            plane_txt = self._plane.base_url
            self._plane_chip.set_text("PLANE")
            self._plane_chip.add_css_class("hogwarts-chip-plane")
        else:
            self._plane_chip.set_text("PLANE OFF")
            self._plane_chip.remove_css_class("hogwarts-chip-plane")

        self._channel.set_path_status(
            state=state,
            state_label=state_label,
            path=path,
            socks=socks,
            hops=hops,
            fp=fp,
            plane=plane_txt,
        )
        self._chip.set_text(state_label.upper())
        self._chip.remove_css_class("hogwarts-chip-live")
        if state == "live":
            self._chip.add_css_class("hogwarts-chip-live")

    def _save_plane(self) -> None:
        cfg = self._plane_panel.read_config()
        save_plane_config(self._plane_path, cfg)
        self._plane = cfg
        self._log_msg(f"Plane saved → {cfg.base_url or '(empty)'}")
        self._refresh_status()
        if self._ctx.toast:
            self._ctx.toast("Plane config saved")

    def _test_plane(self) -> None:
        # Use form values without requiring save first
        cfg = self._plane_panel.read_config()
        if not cfg.is_configured:
            self._plane_panel.set_result("Set a base URL first", ok=False)
            return

        def work() -> None:
            try:
                client = C2Client(cfg)
                data = client.health()
                msg = json.dumps(data, indent=2) if isinstance(data, dict) else str(data)
                ok = True
            except Exception as exc:
                msg = str(exc)
                ok = False

            def done() -> bool:
                self._plane_panel.set_result(msg, ok=ok)
                self._log_msg("Plane health " + ("ok" if ok else "fail"))
                return False

            GLib.idle_add(done)

        threading.Thread(target=work, name="hogwarts-health", daemon=True).start()
        self._plane_panel.set_result("Testing…")

    def _refresh_agents(self, quiet: bool = False) -> None:
        if not self._plane.is_configured:
            self._agents.show_empty("Configure the control plane under Plane.")
            if not quiet and self._ctx.toast:
                self._ctx.toast("Plane not configured")
            return

        status = self._agents.filter_status()
        q = self._agents.query()

        def work() -> None:
            try:
                agents = self._client().list_agents(status=status, q=q or None)
                err = None
            except Exception as exc:
                agents = []
                err = str(exc)

            def done() -> bool:
                if err:
                    self._agents.show_error(err)
                    self._log_msg(f"Agents error: {err}")
                else:
                    self._agents.set_agents(agents)
                    self._log_msg(f"Agents refreshed ({len(agents)})")
                return False

            GLib.idle_add(done)

        threading.Thread(target=work, name="hogwarts-agents", daemon=True).start()
        if not quiet:
            self._agents.status_lab.set_text("Loading…")

    def _save_listener(self, quiet: bool = False) -> None:
        snap = self._listener.snapshot()
        snap["updated"] = datetime.now(timezone.utc).isoformat()
        data = self._store.load()
        data.update(snap)
        self._store.save(data)
        self._log_msg("Listener notes saved")
        if not quiet and self._ctx.toast:
            self._ctx.toast("Listener saved")

    def _copy_listener_line(self, *_a) -> None:
        line = self._listener.listener_line()
        self._clipboard_set(line)
        self._log_msg(f"Copied listener: {line}")
        if self._ctx.toast:
            self._ctx.toast("Listener line copied")

    def _targets(self) -> list[tuple[str, int, str]]:
        return [
            ("1.1.1.1", 443, "HTTPS · Cloudflare"),
            ("8.8.8.8", 443, "HTTPS · Google"),
            ("9.9.9.9", 853, "DoT · Quad9"),
            ("1.1.1.1", 53, "DNS TCP · CF"),
            ("cloudflare.com", 443, "HTTPS · SNI name"),
        ]

    def _socks_tuple(self) -> tuple[str, int] | None:
        try:
            st = self._ctx.services.core.status(force=True)
            proxy = (getattr(st, "local_proxy", None) or "").strip()
        except Exception:
            return None
        if not proxy:
            return None
        raw = proxy.split("://", 1)[-1].split("/")[0]
        if ":" not in raw:
            return None
        host, port_s = raw.rsplit(":", 1)
        try:
            return host, int(port_s)
        except ValueError:
            return None

    def _run_probes(self) -> None:
        if self._probe_busy:
            return
        self._probe_busy = True
        self._egress.set_busy(True, "Probing…")
        targets = self._targets()
        socks = self._socks_tuple()

        def work() -> None:
            rows: list[dict[str, Any]] = []
            for host, port, label in targets:
                d_ok, d_ms, d_err = tcp_probe(host, port, timeout=3.0)
                row: dict[str, Any] = {
                    "label": label,
                    "host": host,
                    "port": port,
                    "direct_ok": d_ok,
                    "direct_ms": round(d_ms, 1),
                    "direct_err": d_err,
                }
                if socks:
                    s_ok, s_ms, s_err = socks_tcp_probe(
                        socks[0], socks[1], host, port, timeout=8.0
                    )
                    row["path_ok"] = s_ok
                    row["path_ms"] = round(s_ms, 1)
                    row["path_err"] = s_err
                rows.append(row)

            ts = datetime.now(timezone.utc).isoformat()
            try:
                meta = self._store.load()
                meta["last_probe_rows"] = rows
                meta["last_probe_ts"] = ts
                meta["last_probe_socks"] = (
                    f"{socks[0]}:{socks[1]}" if socks else None
                )
                self._store.save(meta)
            except Exception:
                pass

            def done() -> bool:
                self._probe_busy = False
                self._egress.set_busy(False)
                self._egress.render_rows(rows, ts=ts)
                self._log_msg(f"Egress matrix complete ({len(rows)} targets)")
                if self._ctx.toast:
                    self._ctx.toast("Egress matrix complete")
                return False

            GLib.idle_add(done)

        threading.Thread(target=work, name="hogwarts-probe", daemon=True).start()

    def _probe_custom(self) -> None:
        host = self._egress.custom_host.get_text().strip()
        try:
            port = int(self._egress.custom_port.get_text().strip() or "443")
        except ValueError:
            if self._ctx.toast:
                self._ctx.toast("Invalid port")
            return
        if not host:
            if self._ctx.toast:
                self._ctx.toast("Enter a host")
            return
        if self._probe_busy:
            return
        self._probe_busy = True
        self._egress.set_busy(True, f"Probing {host}:{port}…")
        socks = self._socks_tuple()

        def work() -> None:
            d_ok, d_ms, d_err = tcp_probe(host, port, timeout=4.0)
            row: dict[str, Any] = {
                "label": "Custom",
                "host": host,
                "port": port,
                "direct_ok": d_ok,
                "direct_ms": round(d_ms, 1),
                "direct_err": d_err,
            }
            if socks:
                s_ok, s_ms, s_err = socks_tcp_probe(
                    socks[0], socks[1], host, port, timeout=10.0
                )
                row["path_ok"] = s_ok
                row["path_ms"] = round(s_ms, 1)
                row["path_err"] = s_err
            rows = [row]
            meta = self._store.load()
            prev = meta.get("last_probe_rows")
            if isinstance(prev, list):
                rows = [row] + [
                    r
                    for r in prev
                    if not (r.get("host") == host and r.get("port") == port)
                ][:12]
            ts = datetime.now(timezone.utc).isoformat()
            meta["last_probe_rows"] = rows
            meta["last_probe_ts"] = ts
            self._store.save(meta)

            def done() -> bool:
                self._probe_busy = False
                self._egress.set_busy(False)
                self._egress.render_rows(rows, ts=ts)
                self._log_msg(f"Custom probe {host}:{port}")
                return False

            GLib.idle_add(done)

        threading.Thread(target=work, name="hogwarts-custom", daemon=True).start()

    def _clipboard_set(self, text: str) -> None:
        try:
            display = Gdk.Display.get_default()
            if display is not None:
                display.get_clipboard().set(text)
        except Exception:
            pass

    def _copy_socks(self, *_a) -> None:
        try:
            st = self._ctx.services.core.status(force=True)
            proxy = (getattr(st, "local_proxy", None) or "").strip()
        except Exception:
            proxy = ""
        if not proxy:
            if self._ctx.toast:
                self._ctx.toast("No SOCKS — connect a path first")
            return
        if not proxy.startswith("socks"):
            proxy = f"socks5://{proxy}"
        self._clipboard_set(proxy)
        self._log_msg(f"Copied SOCKS {proxy}")
        if self._ctx.toast:
            self._ctx.toast("SOCKS copied")

    def _open_export(self, *_a) -> None:
        try:
            from app_config import user_data_dir

            path = Path(user_data_dir()) / "reverse"
        except Exception:
            path = Path.home() / ".local" / "share" / "reach" / "reverse"
        path.mkdir(parents=True, exist_ok=True)
        self._xdg_open(path)
        self._log_msg(f"Opened export {path}")

    def _open_data(self, *_a) -> None:
        p = self._ctx.data_path()
        p.mkdir(parents=True, exist_ok=True)
        self._xdg_open(p)

    def _xdg_open(self, path: Path) -> None:
        try:
            subprocess.Popen(
                ["xdg-open", str(path)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            if self._ctx.toast:
                self._ctx.toast(f"Opened {path.name}")
        except OSError as exc:
            if self._ctx.toast:
                self._ctx.toast(str(exc))

    def _go_marketplace(self) -> None:
        if self._ctx.navigate:
            self._ctx.navigate("marketplace")

    def _export_playbook(self, *_a) -> None:
        self._save_listener(quiet=True)
        meta = self._store.load()
        path_info: dict[str, Any] = {}
        try:
            st = self._ctx.services.core.status(force=True)
            path_info = {
                "state": getattr(getattr(st, "state", None), "value", ""),
                "path_summary": getattr(st, "path_summary", ""),
                "local_proxy": getattr(st, "local_proxy", ""),
                "hops": list(getattr(st, "hops", None) or []),
                "fingerprint_note": getattr(st, "fingerprint_note", ""),
            }
        except Exception as exc:
            path_info = {"error": str(exc)}

        playbook = {
            "hogwarts_version": __version__,
            "exported": datetime.now(timezone.utc).isoformat(),
            "listener": {
                "accept_host": meta.get("accept_host"),
                "accept_port": meta.get("accept_port"),
                "face": meta.get("face"),
                "agent_id": meta.get("agent_id"),
                "proto": meta.get("proto"),
            },
            "notes": meta.get("notes"),
            "path": path_info,
            "plane": {
                "configured": self._plane.is_configured,
                "base_url": self._plane.base_url if self._plane.is_configured else "",
            },
            "last_probe": {
                "ts": meta.get("last_probe_ts"),
                "socks": meta.get("last_probe_socks"),
                "rows": meta.get("last_probe_rows"),
            },
        }
        out = self._ctx.data_path(
            f"playbook-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
        )
        out.write_text(json.dumps(playbook, indent=2) + "\n", encoding="utf-8")
        self._ops.playbook_path.set_text(str(out))
        self._log_msg(f"Playbook → {out.name}")
        if self._ctx.toast:
            self._ctx.toast(f"Playbook → {out.name}")

    def _console_command(self, line: str) -> str | None:
        import shlex

        parts = shlex.split(line)
        if not parts:
            return None
        cmd = parts[0].lower()
        if cmd == "status":
            self._refresh_status()
            plane = self._plane.base_url if self._plane.is_configured else "off"
            return f"path chip={self._chip.get_text()}  plane={plane}"
        if cmd == "plane":
            if not self._plane.is_configured:
                return "plane not configured"
            return f"url={self._plane.base_url}  token={'set' if self._plane.api_token else 'none'}"
        if cmd == "socks":
            s = self._socks_tuple()
            return f"socks5://{s[0]}:{s[1]}" if s else "no SOCKS (path down)"
        if cmd == "agents":
            self._refresh_agents()
            return "refreshing agents…"
        if cmd == "pull":
            if not self._plane.is_configured:
                return "plane not configured"
            try:
                events = self._client().poll_events(limit=20)
            except Exception as exc:
                return f"pull failed: {exc}"
            if not events:
                return "no events"
            lines = []
            for e in events[-15:]:
                ts = e.ts.strftime("%H:%M:%S") if e.ts else "?"
                lines.append(f"[{ts}] {e.level}/{e.channel} {e.message}")
            return "\n".join(lines)
        # operator note
        self._log_msg(f"note: {line}")
        return "noted"

    def _log_msg(self, msg: str) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        self._log_lines.append(f"[{ts}] {msg}")
        self._log_lines = self._log_lines[-200:]
        self._log.set_text("\n".join(self._log_lines))

    def _clear_log(self, *_a) -> None:
        self._log_lines.clear()
        self._log.set_text("")
