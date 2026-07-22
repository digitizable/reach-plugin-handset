"""Decode Keepstream H.264 Annex-B access units for GTK paint.

Primary path: GStreamer appsrc → h264parse → avdec_h264 → videoconvert →
**RGB24** appsink (no jpegenc — lower latency, no filmy double-compress).

Important: call :func:`ensure_gst_init` once from the **GTK main thread** before
Session starts. Initializing GStreamer from a worker while GTK owns the default
GLib main context freezes the Control/Session UI.
"""

from __future__ import annotations

import threading
from typing import Any, NamedTuple

_gst_init_lock = threading.Lock()
_gst_ready = False
_gst_ok = False


class RgbFrame(NamedTuple):
    """Raw RGB24 frame for GdkPixbuf (rowstride = width * 3)."""

    data: bytes
    width: int
    height: int

    @property
    def rowstride(self) -> int:
        return self.width * 3


def ensure_gst_init() -> bool:
    """Initialize GStreamer once. Prefer calling from the GTK main thread."""
    global _gst_ready, _gst_ok
    if _gst_ready:
        return _gst_ok
    with _gst_init_lock:
        if _gst_ready:
            return _gst_ok
        try:
            import gi

            gi.require_version("Gst", "1.0")
            from gi.repository import Gst

            if not getattr(Gst, "is_initialized", lambda: False)():
                Gst.init(None)
            _gst_ok = True
        except Exception:
            _gst_ok = False
        _gst_ready = True
        return _gst_ok


class H264ToRgb:
    """Stateful H.264 Annex-B → RGB24 decoder (one pipeline, many AUs)."""

    def __init__(self) -> None:
        self._pipe: Any = None
        self._src: Any = None
        self._sink: Any = None
        self._lock = threading.Lock()
        self._ok = False
        self._Gst: Any = None
        self._pushed = 0
        self._w = 0
        self._h = 0

    @property
    def available(self) -> bool:
        return ensure_gst_init()

    def start(self) -> bool:
        if self._ok and self._pipe is not None:
            return True
        if not ensure_gst_init():
            return False
        try:
            import gi

            gi.require_version("Gst", "1.0")
            from gi.repository import Gst

            self._Gst = Gst
            # RGB24 direct — skip jpegenc (latency + washed/filmy recompress)
            # videoconvert handles limited→full / bt709 chroma sanely
            desc = (
                "appsrc name=src is-live=true do-timestamp=true format=time "
                "block=false max-bytes=0 "
                "caps=video/x-h264,stream-format=byte-stream,alignment=au ! "
                "h264parse config-interval=-1 ! "
                "avdec_h264 max-threads=2 ! "
                "videoconvert n-threads=2 ! "
                "video/x-raw,format=RGB ! "
                "appsink name=sink emit-signals=false sync=false "
                "max-buffers=1 drop=true enable-last-sample=false"
            )
            pipe = Gst.parse_launch(desc)
            src = pipe.get_by_name("src")
            sink = pipe.get_by_name("sink")
            if src is None or sink is None:
                return False
            src.set_property("stream-type", 0)
            src.set_property("format", Gst.Format.TIME)
            ret = pipe.set_state(Gst.State.PLAYING)
            if ret == Gst.StateChangeReturn.FAILURE:
                pipe.set_state(Gst.State.NULL)
                return False
            self._pipe = pipe
            self._src = src
            self._sink = sink
            self._ok = True
            self._pushed = 0
            self._w = 0
            self._h = 0
            return True
        except Exception:
            self.stop()
            return False

    def stop(self) -> None:
        pipe = self._pipe
        self._pipe = None
        self._src = None
        self._sink = None
        self._ok = False
        self._pushed = 0
        self._w = 0
        self._h = 0
        if pipe is not None:
            try:
                pipe.set_state(self._Gst.State.NULL if self._Gst else 1)
            except Exception:
                pass

    def decode(self, annex_b_au: bytes, *, timeout_s: float = 0.10) -> RgbFrame | None:
        """Decode one AU → RGB24. Short timeout so the stream thread stays live."""
        if not annex_b_au:
            return None
        with self._lock:
            if not self.start() or self._src is None or self._sink is None:
                return None
            Gst = self._Gst
            try:
                buf = Gst.Buffer.new_allocate(None, len(annex_b_au), None)
                buf.fill(0, annex_b_au)
                ret = self._src.emit("push-buffer", buf)
                if ret != Gst.FlowReturn.OK:
                    self.stop()
                    if not self.start():
                        return None
                    buf = Gst.Buffer.new_allocate(None, len(annex_b_au), None)
                    buf.fill(0, annex_b_au)
                    ret = self._src.emit("push-buffer", buf)
                    if ret != Gst.FlowReturn.OK:
                        return None
                self._pushed += 1
                to = timeout_s
                if self._pushed <= 4:
                    to = max(to, 0.35)
                timeout_ns = int(max(0.02, to) * Gst.SECOND)
                sample = self._sink.emit("try-pull-sample", timeout_ns)
                if sample is None:
                    return None
                caps = sample.get_caps()
                if caps is not None and caps.get_size() > 0:
                    st = caps.get_structure(0)
                    try:
                        ok_w, w = st.get_int("width")
                        ok_h, h = st.get_int("height")
                        if ok_w and ok_h and w > 0 and h > 0:
                            self._w, self._h = int(w), int(h)
                    except Exception:
                        pass
                out_buf = sample.get_buffer()
                if out_buf is None:
                    return None
                ok, mapinfo = out_buf.map(Gst.MapFlags.READ)
                if not ok:
                    return None
                try:
                    data = bytes(mapinfo.data)
                finally:
                    out_buf.unmap(mapinfo)
                w, h = self._w, self._h
                if w <= 0 or h <= 0:
                    # Infer from buffer size if caps missing (stride = w*3)
                    # uncommon after first frame
                    return None
                need = w * h * 3
                if len(data) < need:
                    return None
                if len(data) > need:
                    data = data[:need]
                return RgbFrame(data=data, width=w, height=h)
            except Exception:
                return None


# Back-compat alias used by older call sites
H264ToJpeg = H264ToRgb

_decoder: H264ToRgb | None = None
_decoder_lock = threading.Lock()


def decode_h264_au_to_rgb(au: bytes) -> RgbFrame | None:
    global _decoder
    with _decoder_lock:
        if _decoder is None:
            _decoder = H264ToRgb()
        return _decoder.decode(au)


def decode_h264_au_to_jpeg(au: bytes) -> bytes | None:
    """Legacy helper — prefer :func:`decode_h264_au_to_rgb`.

    Kept so smoke tests / old callers do not break. Returns None (RGB path only).
    """
    # No longer produces JPEG; callers should use decode_h264_au_to_rgb.
    # Return None so they fall through rather than treating RGB as JPEG.
    _ = au
    return None


def stop_h264_decoder() -> None:
    global _decoder
    with _decoder_lock:
        if _decoder is not None:
            _decoder.stop()
            _decoder = None
