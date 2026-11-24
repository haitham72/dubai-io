"""Small PNG codec for 8-bit RGB and RGBA. No extra dependency."""

from __future__ import annotations

import struct
import zlib

_SIG = b"\x89PNG\r\n\x1a\n"


def _chunk(tag: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)


def encode_png(width: int, height: int, samples: bytes, channels: int) -> bytes:
    if channels not in (3, 4):
        raise ValueError("channels")
    stride = width * channels
    if len(samples) != stride * height:
        raise ValueError("sample size")
    raw = bytearray()
    for y in range(height):
        raw.append(0)
        raw += samples[y * stride : (y + 1) * stride]
    color = 6 if channels == 4 else 2
    ihdr = struct.pack(">IIBBBBB", width, height, 8, color, 0, 0, 0)
    return _SIG + _chunk(b"IHDR", ihdr) + _chunk(b"IDAT", zlib.compress(bytes(raw))) + _chunk(b"IEND", b"")


def _paeth(a: int, b: int, c: int) -> int:
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    if pb <= pc:
        return b
    return c


def decode_png(data: bytes) -> tuple[int, int, int, bytes]:
    if not data.startswith(_SIG):
        raise ValueError("not a png")
    pos = 8
    width = height = color = None
    idat = bytearray()
    while pos + 8 <= len(data):
        length = struct.unpack(">I", data[pos : pos + 4])[0]
        tag = data[pos + 4 : pos + 8]
        start = pos + 8
        chunk = data[start : start + length]
        pos = start + length + 4
        if tag == b"IHDR":
            width, height, bit, color, _comp, _filt, inter = struct.unpack(">IIBBBBB", chunk)
            if bit != 8 or inter or color not in (2, 6):
                raise ValueError("unsupported png")
        elif tag == b"IDAT":
            idat += chunk
        elif tag == b"IEND":
            break
    if width is None or color is None:
        raise ValueError("truncated png")
    channels = 4 if color == 6 else 3
    raw = zlib.decompress(bytes(idat))
    stride = width * channels
    out = bytearray()
    prev = bytearray(stride)
    i = 0
    for _y in range(height):
        filt = raw[i]
        i += 1
        row = bytearray(raw[i : i + stride])
        i += stride
        if filt == 1:
            for x in range(stride):
                left = row[x - channels] if x >= channels else 0
                row[x] = (row[x] + left) & 255
        elif filt == 2:
            for x in range(stride):
                row[x] = (row[x] + prev[x]) & 255
        elif filt == 3:
            for x in range(stride):
                left = row[x - channels] if x >= channels else 0
                row[x] = (row[x] + ((left + prev[x]) // 2)) & 255
        elif filt == 4:
            for x in range(stride):
                a = row[x - channels] if x >= channels else 0
                b = prev[x]
                c = prev[x - channels] if x >= channels else 0
                row[x] = (row[x] + _paeth(a, b, c)) & 255
        elif filt != 0:
            raise ValueError("bad filter")
        out += row
        prev = row
    return width, height, channels, bytes(out)


def apply_matte(image: bytes, alpha: bytes) -> bytes:
    """Keep the photo RGB. Attach one alpha byte per pixel. Paint nothing new."""
    width, height, channels, samples = decode_png(image)
    if len(alpha) != width * height:
        raise ValueError("alpha size")
    rgba = bytearray(width * height * 4)
    for i in range(width * height):
        base = i * channels
        rgba[i * 4] = samples[base]
        rgba[i * 4 + 1] = samples[base + 1]
        rgba[i * 4 + 2] = samples[base + 2]
        rgba[i * 4 + 3] = alpha[i]
    return encode_png(width, height, bytes(rgba), 4)
