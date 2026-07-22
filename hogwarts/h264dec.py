"""Decode Keepstream H.264 Annex-B access units for GTK paint.

Prefers GStreamer (appsrc → h264parse → avdec_h264 → jpegenc → appsink).
Falls back to None if GStreamer/plugins are unavailable (caller keeps waiting
for JPEG frames or the agent may fall back to MJPEG).
"""

from __future__ import annotations

import threading
from typing import Any


class H264ToJpeg:
    def __init__(self) -> None:
        self._pipe: Any = None
        self._src: Any = None
        self._sink: Any = None
        self._lock = threading.Lock()
        self._ok = False
        self._Gst: Any = None
        self._pushed = 0

    @property
    def available(self) -> bool:
        try:
            import gi

            gi.require_version("Gst", "1.0")
            from gi.repository import Gst  # noqa: F401

            return True
        except Exception:
            return False

    def start(self) -> bool:
        if self._ok and self._pipe is not None:
            return True
        try:
            import gi

            gi.require_version("Gst", "1.0")
            from gi.repository import Gst

            if not getattr(Gst, "is_initialized", lambda: False)():
                Gst.init(None)
            self._Gst = Gst
            # byte-stream Annex-B; config-interval so parse can recover SPS/PPS
            desc = (
                "appsrc name=src is-live=true do-timestamp=true format=time "
                "block=false max-bytes=0 "
                "caps=video/x-h264,stream-format=byte-stream,alignment=au ! "
                "h264parse config-interval=-1 ! "
                "avdec_h264 ! videoconvert ! "
                "jpegenc quality=80 ! "
                "appsink name=sink emit-signals=false sync=false "
                "max-buffers=2 drop=true enable-last-sample=false"
            )
            pipe = Gst.parse_launch(desc)
            src = pipe.get_by_name("src")
            sink = pipe.get_by_name("sink")
            if src is None or sink is None:
                return False
            src.set_property("stream-type", 0)  # GST_APP_STREAM_TYPE_STREAM
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
        if pipe is not None:
            try:
                pipe.set_state(self._Gst.State.NULL if self._Gst else 1)
            except Exception:
                pass

    def decode(self, annex_b_au: bytes, *, timeout_s: float = 0.6) -> bytes | None:
        if not annex_b_au:
            return None
        with self._lock:
            if not self.start() or self._src is None or self._sink is None:
                return None
            Gst = self._Gst
            try:
                buf = Gst.Buffer.new_allocate(None, len(annex_b_au), None)
                buf.fill(0, annex_b_au)
                # Treat as complete access unit
                try:
                    buf.set_flags(Gst.BufferFlags.HEADER if self._pushed == 0 else 0)
                except Exception:
                    pass
                ret = self._src.emit("push-buffer", buf)
                if ret != Gst.FlowReturn.OK:
                    # try restart once
                    self.stop()
                    if not self.start():
                        return None
                    buf = Gst.Buffer.new_allocate(None, len(annex_b_au), None)
                    buf.fill(0, annex_b_au)
                    ret = self._src.emit("push-buffer", buf)
                    if ret != Gst.FlowReturn.OK:
                        return None
                self._pushed += 1
                # Parameter-set-only AUs won't produce a sample — short wait is fine.
                # Picture AUs may need a bit longer on first IDR after join.
                timeout_ns = int(max(0.05, timeout_s) * Gst.SECOND)
                sample = self._sink.emit("try-pull-sample", timeout_ns)
                if sample is None:
                    # Drain a bit longer once the pipeline is warm
                    if self._pushed <= 3:
                        sample = self._sink.emit(
                            "try-pull-sample", int(0.4 * Gst.SECOND)
                        )
                    if sample is None:
                        return None
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
                if data[:2] == b"\xff\xd8":
                    return data
                return data if data else None
            except Exception:
                return None


_decoder: H264ToJpeg | None = None
_decoder_lock = threading.Lock()


def decode_h264_au_to_jpeg(au: bytes) -> bytes | None:
    global _decoder
    with _decoder_lock:
        if _decoder is None:
            _decoder = H264ToJpeg()
        return _decoder.decode(au)


def stop_h264_decoder() -> None:
    global _decoder
    with _decoder_lock:
        if _decoder is not None:
            _decoder.stop()
            _decoder = None
