"""Draw the TaskBoard icon (three columns on a dark square) as PNG files."""

import struct
import zlib
from pathlib import Path

NAVY = (23, 43, 77)
WHITE = (255, 255, 255)
TOP = 0.22
# Each column: left edge, right edge, bottom edge, as fractions of the icon size.
COLUMNS = [(0.20, 0.36, 0.78), (0.42, 0.58, 0.56), (0.64, 0.80, 0.68)]


def colour(x, y, size):
    for left, right, bottom in COLUMNS:
        if left * size <= x < right * size and TOP * size <= y < bottom * size:
            return WHITE
    return NAVY


def chunk(kind, data):
    body = kind + data
    return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body))


def write_png(path, size):
    rows = b""
    for y in range(size):
        rows += b"\x00" + bytes(c for x in range(size) for c in colour(x, y, size))
    header = struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header)
    png += chunk(b"IDAT", zlib.compress(rows)) + chunk(b"IEND", b"")
    path.write_bytes(png)
    print("wrote", path)


public = Path("frontend/public")
write_png(public / "icon-192.png", 192)
write_png(public / "icon-512.png", 512)
write_png(public / "apple-touch-icon.png", 180)