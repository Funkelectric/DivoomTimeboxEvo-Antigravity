"""
Divoom Timebox-Evo SPP Communication Protocol Encoder.

Handles packet construction, checksum calculation, byte escaping,
and image/animation frame encoding for 16x16 pixel display.
"""

from typing import List, Tuple, Sequence

START_BYTE = 0x01
END_BYTE = 0x02

import math
from typing import List, Tuple, Sequence

START_BYTE = 0x01
END_BYTE = 0x02

# Command IDs
CMD_SET_RADIO = 0x05
CMD_SET_TIME = 0x18
CMD_SET_VIEW = 0x45          # SPP_SET_BOX_MODE; byte0 = LightEnum (5 = USER_DEFINE_MODE)
CMD_SET_BOX_COLOR = 0x44     # SPP_SET_BOX_COLOR: static pic, header 00 0A 0A 04 + AA-block
CMD_DRAW_PAD_CTRL = 0x58     # SPP_DRAWING_PAD_CTRL: r g b n pos[n]
CMD_DRAW_PAD_EXIT = 0x5A
CMD_DRAW_FILL = 0x6F         # SPP_DRAWING_MUL_PAD_ENTER: r g b (fill canvas)
CMD_SEND_STATIC_IMAGE = 0x44
CMD_SEND_ANIM_FRAME = 0x49
CMD_SET_WEATHER = 0x5F
CMD_SET_BRIGHTNESS = 0x74

def calculate_checksum(data: bytes) -> int:
    """16-bit sum. APK u.k()/u.l(): sum of bytes from the LENGTH field through the last
    data byte (i.e. length_lo + length_hi + cmd + data) -- NOT just cmd+data."""
    return sum(data) & 0xFFFF

def escape_bytes(data: bytes) -> bytes:
    """Legacy (BlueModeEnum.OldMode) escaping, APK u.l(): 01->03 04, 02->03 05, 03->03 06.
    New mode (u.k()) sends raw bytes."""
    out = bytearray()
    for b in data:
        if b in (1, 2, 3):
            out.extend([0x03, b + 3])
        else:
            out.append(b)
    return bytes(out)

def build_packet(payload: bytes, escape: bool = False) -> bytes:
    """payload = [cmd][data...]. Frame: 01 | len(2 LE) | cmd data | cksum(2 LE) | 02,
    len = len(payload) + 2; checksum covers len bytes + payload (verified in APK u.k)."""
    length = len(payload) + 2
    body = bytes([length & 0xFF, (length >> 8) & 0xFF]) + payload
    ck = calculate_checksum(body)
    body += bytes([ck & 0xFF, (ck >> 8) & 0xFF])
    if escape:
        body = escape_bytes(body)
    return bytes([START_BYTE]) + body + bytes([END_BYTE])

def encode_brightness(percent: int) -> bytes:
    """Brightness 0 - 100%"""
    val = max(0, min(100, percent))
    return build_packet(bytes([CMD_SET_BRIGHTNESS, val]))

def encode_channel(channel_id: int) -> bytes:
    """
    0: Clock
    1: Lighting
    2: Cloud Channel
    3: VJ Effects
    4: Visualizer / Spectrum
    5: Custom
    """
    return build_packet(bytes([CMD_SET_VIEW, channel_id & 0xFF]))

def encode_16x16_frame(pixels_rgb: Sequence[Tuple[int, int, int]], delay_ms: int = 200, frame_idx: int = 0) -> bytes:
    """
    Encodes a 16x16 RGB image using Timebox-Evo palette quantization (Command 0x49).
    This compresses the 768-byte raw frame down to ~50-80 bytes, preventing serial
    buffer bottlenecks over Bluetooth.
    """
    if len(pixels_rgb) != 256:
        raise ValueError(f"Expected 256 pixels, got {len(pixels_rgb)}")

    palette = []
    pixel_indices = []
    for rgb in pixels_rgb:
        col = (rgb[0] & 0xFF, rgb[1] & 0xFF, rgb[2] & 0xFF)
        if col not in palette:
            palette.append(col)
        pixel_indices.append(palette.index(col))

    num_colors = len(palette)
    bpp = max(1, math.ceil(math.log2(num_colors))) if num_colors > 1 else 1
    if bpp > 8:
        bpp = 8

    packed_bits = []
    bit_buf = 0
    bits_in_buf = 0
    for idx in pixel_indices:
        bit_buf |= (idx << bits_in_buf)
        bits_in_buf += bpp
        while bits_in_buf >= 8:
            packed_bits.append(bit_buf & 0xFF)
            bit_buf >>= 8
            bits_in_buf -= 8
    if bits_in_buf > 0:
        packed_bits.append(bit_buf & 0xFF)

    pal_bytes = bytearray([num_colors if num_colors < 256 else 0])
    for r, g, b in palette:
        pal_bytes.extend([r, g, b])

    # Frame header: [frame_idx_lsb, frame_idx_msb, delay_lsb, delay_msb, reset_flag]
    frame_header = bytearray([frame_idx & 0xFF, (frame_idx >> 8) & 0xFF, delay_ms & 0xFF, (delay_ms >> 8) & 0xFF, 0x00])
    full_frame = frame_header + pal_bytes + bytearray(packed_bits)
    total_size = len(full_frame)
    payload = bytearray([CMD_SEND_ANIM_FRAME, total_size & 0xFF, (total_size >> 8) & 0xFF]) + full_frame
    return build_packet(bytes(payload))



def _encode_block(pixels_rgb, delay_ms=0):
    """AA-block produced by native PixelEncode: AA len(2) time(2) reset(1) ncolors(1) palette bitpacked.
    (format from community docs; native lib not disassembled)."""
    palette, idx = [], []
    for rgb in pixels_rgb:
        c = tuple(v & 0xFF for v in rgb)
        if c not in palette:
            palette.append(c)
        idx.append(palette.index(c))
    n = len(palette)
    bpp = max(1, math.ceil(math.log2(n))) if n > 1 else 1
    bits = bytearray(); buf = 0; cnt = 0
    for v in idx:
        buf |= v << cnt; cnt += bpp
        while cnt >= 8:
            bits.append(buf & 0xFF); buf >>= 8; cnt -= 8
    if cnt:
        bits.append(buf & 0xFF)
    pal = bytes([n & 0xFF]) + b"".join(bytes(c) for c in palette)
    inner = bytes([delay_ms & 0xFF, (delay_ms >> 8) & 0xFF, 0x00]) + pal + bytes(bits)
    total = len(inner) + 3
    return bytes([0xAA, total & 0xFF, (total >> 8) & 0xFF]) + inner

def encode_static_image(pixels_rgb) -> bytes:
    """APK CmdManager.A0: cmd 0x44, payload 00 0A 0A 04 + AA-block."""
    if len(pixels_rgb) != 256:
        raise ValueError("Expected 256 pixels")
    return build_packet(bytes([CMD_SET_BOX_COLOR, 0x00, 0x0A, 0x0A, 0x04]) + _encode_block(pixels_rgb))

def encode_draw_pixels(rgb, positions) -> bytes:
    """APK CmdManager.i2: live drawing pad stroke: 0x58 r g b n pos[n] (pos = y*16+x)."""
    return build_packet(bytes([CMD_DRAW_PAD_CTRL, rgb[0], rgb[1], rgb[2], len(positions)]) + bytes(positions))

def encode_draw_exit() -> bytes:
    return build_packet(bytes([CMD_DRAW_PAD_EXIT]))

def encode_fill(rgb) -> bytes:
    return build_packet(bytes([CMD_DRAW_FILL, rgb[0], rgb[1], rgb[2]]))
