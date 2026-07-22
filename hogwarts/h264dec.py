"""Back-compat re-export — H.264 decode lives in keepstream.h264dec."""

from __future__ import annotations

from keepstream.h264dec import (
    H264ToJpeg,
    H264ToRgb,
    RgbFrame,
    decode_h264_au_to_jpeg,
    decode_h264_au_to_rgb,
    ensure_gst_init,
    stop_h264_decoder,
)

__all__ = [
    "RgbFrame",
    "ensure_gst_init",
    "H264ToRgb",
    "H264ToJpeg",
    "decode_h264_au_to_rgb",
    "decode_h264_au_to_jpeg",
    "stop_h264_decoder",
]
