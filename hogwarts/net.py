"""TCP / SOCKS egress probes."""

from __future__ import annotations

import socket
import struct
import time


def tcp_probe(host: str, port: int, *, timeout: float) -> tuple[bool, float, str]:
    t0 = time.perf_counter()
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True, (time.perf_counter() - t0) * 1000.0, ""
    except OSError as exc:
        return False, (time.perf_counter() - t0) * 1000.0, str(exc)


def socks5_connect(
    socks_host: str,
    socks_port: int,
    host: str,
    port: int,
    *,
    timeout: float = 8.0,
) -> socket.socket:
    """Open a TCP connection to host:port via SOCKS5 (no-auth). Caller owns the socket."""
    sock = socket.create_connection((socks_host, socks_port), timeout=timeout)
    try:
        sock.settimeout(timeout)
        sock.sendall(b"\x05\x01\x00")
        resp = sock.recv(2)
        if len(resp) < 2 or resp[0] != 5 or resp[1] != 0:
            raise OSError("socks auth method rejected")
        host_b = host.encode("idna")
        if len(host_b) > 255:
            raise OSError("hostname too long for SOCKS")
        # Prefer domain name form so we do not require local resolve of agent host
        req = (
            b"\x05\x01\x00\x03"
            + bytes([len(host_b)])
            + host_b
            + struct.pack("!H", int(port))
        )
        sock.sendall(req)
        hdr = sock.recv(4)
        if len(hdr) < 4 or hdr[1] != 0:
            code = hdr[1] if len(hdr) > 1 else -1
            raise OSError(f"socks connect failed code={code}")
        atyp = hdr[3]
        if atyp == 1:
            sock.recv(4 + 2)
        elif atyp == 3:
            ln = sock.recv(1)
            if ln:
                sock.recv(ln[0] + 2)
        elif atyp == 4:
            sock.recv(16 + 2)
        return sock
    except Exception:
        try:
            sock.close()
        except OSError:
            pass
        raise


def socks_tcp_probe(
    socks_host: str,
    socks_port: int,
    host: str,
    port: int,
    *,
    timeout: float,
) -> tuple[bool, float, str]:
    t0 = time.perf_counter()
    try:
        sock = socks5_connect(
            socks_host, socks_port, host, port, timeout=timeout
        )
        sock.close()
        return True, (time.perf_counter() - t0) * 1000.0, ""
    except OSError as exc:
        return False, (time.perf_counter() - t0) * 1000.0, str(exc)
