"""Handset — C2-esque operator desk for Reach (authorized lab use)."""

from __future__ import annotations

import json
import socket
import struct
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import GLib, Gtk  # noqa: E402


def create_page(ctx):
    return HandsetPage(ctx)


class HandsetPage(Gtk.Box):
    def __init__(self, ctx) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.add_css_class("page")
        self.add_css_class("handset-page")
        self.set_hexpand(True)
        self.set_vexpand(True)
        self._ctx = ctx
        self._busy = False

        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        header.add_css_class("pane-header")
        titles = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        titles.set_hexpand(True)
        t = Gtk.Label(label="Handset", xalign=0)
        t.add_css_class("pane-header-title")
        titles.append(t)
        s = Gtk.Label(
            label="Operator desk · path-aware reachback (authorized lab)",
            xalign=0,
        )
        s.add_css_class("pane-header-sub")
        titles.append(s)
        header.append(titles)
        refresh = Gtk.Button()
        refresh.set_icon_name("view-refresh-symbolic")
        refresh.add_css_class("flat")
        refresh.set_tooltip_text("Refresh path status")
        refresh.connect("clicked", lambda *_: self._refresh_status())
        header.append(refresh)
        self.append(header)

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_hexpand(True)
        scroll.set_vexpand(True)

        body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        body.set_margin_top(20)
        body.set_margin_bottom(28)
        body.set_margin_start(24)
        body.set_margin_end(24)
        body.set_halign(Gtk.Align.FILL)
        body.set_size_request(420, -1)

        warn = Gtk.Label(
            label=(
                "Authorized use only — lab, contracts, and infra you control. "
                "Handset is a reachback / purple-team desk, not an implant kit."
            ),
            wrap=True,
            xalign=0,
        )
        warn.add_css_class("muted")
        body.append(warn)

        # ── Path / channel status ─────────────────────────────────
        body.append(self._section("Channel"))
        self._status = Gtk.Label(xalign=0, wrap=True, selectable=True)
        self._status.add_css_class("handset-status")
        body.append(self._status)

        # ── Listener notes ────────────────────────────────────────
        body.append(self._section("Listener notes"))
        meta = self._load_meta()
        self._accept_host = Gtk.Entry()
        self._accept_host.set_placeholder_text("accept host / IP")
        self._accept_host.set_text(str(meta.get("accept_host") or ""))
        body.append(self._field("Accept host", self._accept_host))

        self._accept_port = Gtk.Entry()
        self._accept_port.set_placeholder_text("e.g. 18443")
        self._accept_port.set_text(str(meta.get("accept_port") or "18443"))
        body.append(self._field("Accept port", self._accept_port))

        self._face = Gtk.Entry()
        self._face.set_placeholder_text("cover face notes (PRR / REALITY / …)")
        self._face.set_text(str(meta.get("face") or ""))
        body.append(self._field("Cover face", self._face))

        self._notes = Gtk.TextView()
        self._notes.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self._notes.set_top_margin(6)
        self._notes.set_bottom_margin(6)
        self._notes.set_left_margin(8)
        self._notes.set_right_margin(8)
        self._notes.set_size_request(-1, 80)
        buf = self._notes.get_buffer()
        buf.set_text(str(meta.get("notes") or ""))
        body.append(self._field("Ops notes", self._notes))

        save_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        save_btn = Gtk.Button(label="Save notes")
        save_btn.add_css_class("suggested-action")
        save_btn.connect("clicked", self._on_save)
        save_row.append(save_btn)
        export_btn = Gtk.Button(label="Export playbook JSON")
        export_btn.add_css_class("flat")
        export_btn.connect("clicked", self._on_export_playbook)
        save_row.append(export_btn)
        body.append(save_row)

        # ── Egress matrix (lightweight) ───────────────────────────
        body.append(self._section("Egress probes"))
        tip = Gtk.Label(
            label="TCP connect checks — direct vs path SOCKS when Spectre is up.",
            wrap=True,
            xalign=0,
        )
        tip.add_css_class("muted")
        body.append(tip)

        self._probe_out = Gtk.Label(xalign=0, wrap=True, selectable=True)
        self._probe_out.add_css_class("handset-probe-out")
        self._probe_out.set_text("Run probes to populate results.")
        body.append(self._probe_out)

        probe_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        run_p = Gtk.Button(label="Run egress probes")
        run_p.add_css_class("suggested-action")
        run_p.connect("clicked", self._on_probe)
        probe_row.append(run_p)
        body.append(probe_row)

        # ── Agent package ─────────────────────────────────────────
        body.append(self._section("Agent package"))
        pack = Gtk.Label(
            label=(
                "Open Reach’s reverse export folder (Inverse Snowflake / dial-out "
                "packages). Pair with Mirage cover on the accept face when needed."
            ),
            wrap=True,
            xalign=0,
        )
        pack.add_css_class("muted")
        body.append(pack)
        open_exp = Gtk.Button(label="Open export folder")
        open_exp.add_css_class("flat")
        open_exp.set_halign(Gtk.Align.START)
        open_exp.connect("clicked", self._on_open_export)
        body.append(open_exp)

        scroll.set_child(body)
        self.append(scroll)
        self._refresh_status()

    def _section(self, title: str) -> Gtk.Widget:
        lab = Gtk.Label(label=title, xalign=0)
        lab.add_css_class("section-label")
        lab.set_margin_top(4)
        return lab

    def _field(self, title: str, child: Gtk.Widget) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        lab = Gtk.Label(label=title, xalign=0)
        lab.add_css_class("field-label")
        box.append(lab)
        box.append(child)
        return box

    def _meta_path(self) -> Path:
        return self._ctx.data_path("handset.json")

    def _load_meta(self) -> dict:
        p = self._meta_path()
        if not p.is_file():
            return {}
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}

    def _save_meta(self, data: dict) -> None:
        p = self._meta_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    def _notes_text(self) -> str:
        buf = self._notes.get_buffer()
        return buf.get_text(buf.get_start_iter(), buf.get_end_iter(), False)

    def _on_save(self, *_a) -> None:
        data = {
            "accept_host": self._accept_host.get_text().strip(),
            "accept_port": self._accept_port.get_text().strip(),
            "face": self._face.get_text().strip(),
            "notes": self._notes_text().strip(),
            "updated": datetime.now(timezone.utc).isoformat(),
        }
        self._save_meta(data)
        if self._ctx.toast:
            self._ctx.toast("Handset notes saved")

    def _refresh_status(self) -> None:
        lines = []
        try:
            st = self._ctx.services.core.status(force=True)
            state = getattr(getattr(st, "state", None), "value", str(getattr(st, "state", "")))
            lines.append(f"Spectre: {state}")
            lines.append(f"Path: {getattr(st, 'path_summary', None) or '—'}")
            hops = getattr(st, "hops", None) or []
            if hops:
                lines.append(f"Hops: {' → '.join(hops)}")
            proxy = (getattr(st, "local_proxy", None) or "").strip()
            lines.append(f"SOCKS: {proxy or '—'}")
            note = (getattr(st, "fingerprint_note", None) or "").strip()
            if note:
                lines.append(f"FP: {note}")
        except Exception as exc:
            lines.append(f"Spectre status unavailable: {exc}")
        lines.append(f"Plugin data: {self._ctx.data_path()}")
        self._status.set_text("\n".join(lines))

    def _socks_tuple(self) -> tuple[str, int] | None:
        try:
            st = self._ctx.services.core.status(force=True)
            proxy = (getattr(st, "local_proxy", None) or "").strip()
        except Exception:
            return None
        if not proxy:
            return None
        raw = proxy
        if "://" in raw:
            raw = raw.split("://", 1)[1]
        raw = raw.split("/")[0]
        if ":" not in raw:
            return None
        host, port_s = raw.rsplit(":", 1)
        try:
            return host, int(port_s)
        except ValueError:
            return None

    def _on_probe(self, *_a) -> None:
        if self._busy:
            return
        self._busy = True
        self._probe_out.set_text("Probing…")
        targets = [
            ("1.1.1.1", 443, "HTTPS Cloudflare"),
            ("8.8.8.8", 443, "HTTPS Google DNS IP"),
            ("9.9.9.9", 853, "DoT Quad9"),
            ("1.1.1.1", 53, "DNS TCP Cloudflare"),
        ]
        socks = self._socks_tuple()

        def work() -> None:
            lines: list[str] = []
            lines.append(
                f"SOCKS underlay: {socks[0]}:{socks[1]}" if socks else "SOCKS underlay: none"
            )
            lines.append("")
            for host, port, label in targets:
                d_ok, d_ms, d_err = _tcp_probe(host, port, timeout=3.0)
                line = f"{label}  {host}:{port}"
                line += f"\n  direct: {'OK' if d_ok else 'FAIL'} {d_ms:.0f}ms" + (
                    f" ({d_err})" if d_err and not d_ok else ""
                )
                if socks:
                    s_ok, s_ms, s_err = _socks_tcp_probe(
                        socks[0], socks[1], host, port, timeout=8.0
                    )
                    line += f"\n  via path: {'OK' if s_ok else 'FAIL'} {s_ms:.0f}ms" + (
                        f" ({s_err})" if s_err and not s_ok else ""
                    )
                lines.append(line)
                lines.append("")

            text = "\n".join(lines).rstrip()
            # persist last probe
            try:
                meta = self._load_meta()
                meta["last_probe"] = {
                    "ts": datetime.now(timezone.utc).isoformat(),
                    "text": text,
                }
                self._save_meta(meta)
            except Exception:
                pass

            def done() -> bool:
                self._busy = False
                self._probe_out.set_text(text)
                if self._ctx.toast:
                    self._ctx.toast("Egress probes complete")
                return False

            GLib.idle_add(done)

        threading.Thread(target=work, name="handset-probe", daemon=True).start()

    def _on_export_playbook(self, *_a) -> None:
        self._on_save()
        meta = self._load_meta()
        path_info: dict = {}
        try:
            st = self._ctx.services.core.status(force=True)
            path_info = {
                "state": getattr(getattr(st, "state", None), "value", ""),
                "path_summary": getattr(st, "path_summary", ""),
                "local_proxy": getattr(st, "local_proxy", ""),
                "hops": list(getattr(st, "hops", None) or []),
            }
        except Exception as exc:
            path_info = {"error": str(exc)}

        playbook = {
            "handset_version": self._ctx.manifest.version,
            "exported": datetime.now(timezone.utc).isoformat(),
            "listener": {
                "accept_host": meta.get("accept_host"),
                "accept_port": meta.get("accept_port"),
                "face": meta.get("face"),
            },
            "notes": meta.get("notes"),
            "path": path_info,
            "last_probe": meta.get("last_probe"),
            "disclaimer": "Authorized lab use only",
        }
        out = self._ctx.data_path(
            f"playbook-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
        )
        out.write_text(json.dumps(playbook, indent=2) + "\n", encoding="utf-8")
        if self._ctx.toast:
            self._ctx.toast(f"Playbook → {out.name}")
        self._probe_out.set_text(
            (self._probe_out.get_text() or "")
            + f"\n\nPlaybook written:\n{out}"
        )

    def _on_open_export(self, *_a) -> None:
        import subprocess
        from pathlib import Path

        try:
            from app_config import user_data_dir

            path = Path(user_data_dir()) / "reverse"
        except Exception:
            path = Path.home() / ".local" / "share" / "reach" / "reverse"
        path.mkdir(parents=True, exist_ok=True)
        try:
            subprocess.Popen(
                ["xdg-open", str(path)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            if self._ctx.toast:
                self._ctx.toast("Opened export folder")
        except OSError as exc:
            if self._ctx.toast:
                self._ctx.toast(f"Could not open: {exc}")


def _tcp_probe(host: str, port: int, *, timeout: float) -> tuple[bool, float, str]:
    t0 = time.perf_counter()
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True, (time.perf_counter() - t0) * 1000.0, ""
    except OSError as exc:
        return False, (time.perf_counter() - t0) * 1000.0, str(exc)


def _socks_tcp_probe(
    socks_host: str,
    socks_port: int,
    host: str,
    port: int,
    *,
    timeout: float,
) -> tuple[bool, float, str]:
    t0 = time.perf_counter()
    try:
        sock = socket.create_connection((socks_host, socks_port), timeout=timeout)
        try:
            sock.settimeout(timeout)
            sock.sendall(b"\x05\x01\x00")
            resp = sock.recv(2)
            if len(resp) < 2 or resp[0] != 5 or resp[1] != 0:
                return False, (time.perf_counter() - t0) * 1000.0, "socks auth"
            host_b = host.encode("idna")
            req = (
                b"\x05\x01\x00\x03"
                + bytes([len(host_b)])
                + host_b
                + struct.pack("!H", port)
            )
            sock.sendall(req)
            hdr = sock.recv(4)
            if len(hdr) < 4 or hdr[1] != 0:
                code = hdr[1] if len(hdr) > 1 else -1
                return False, (time.perf_counter() - t0) * 1000.0, f"socks {code}"
            # drain bind addr
            atyp = hdr[3]
            if atyp == 1:
                sock.recv(4 + 2)
            elif atyp == 3:
                ln = sock.recv(1)
                if ln:
                    sock.recv(ln[0] + 2)
            elif atyp == 4:
                sock.recv(16 + 2)
            return True, (time.perf_counter() - t0) * 1000.0, ""
        finally:
            sock.close()
    except OSError as exc:
        return False, (time.perf_counter() - t0) * 1000.0, str(exc)
