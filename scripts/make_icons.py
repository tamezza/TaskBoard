"""Draw the TaskBoard icon (three folders filed one behind the other) as PNG files."""

import struct
import zlib
from pathlib import Path

PLUM = (107, 45, 74)
# Each folder: colour, then two rounded rectangles on a 100 x 100 grid,
# the tab and the body, as (left, top, right, bottom). Back folder first.
FOLDERS = [
    ((169, 203, 224), (56, 21, 84, 81), (16, 32, 84, 81)),
    ((185, 207, 159), (36, 34, 64, 81), (16, 45, 84, 81)),
    ((242, 166, 143), (16, 47, 44, 81), (16, 58, 84, 81)),
]
RADIUS = 5
SAMPLES = 3  # each pixel is measured at 3 x 3 points to smooth the curves


def inside(x, y, box):
    left, top, right, bottom = box
    if not (left <= x <= right and top <= y <= bottom):
        return False
    # Distance to the nearest corner centre decides the rounded corners.
    dx = max(left + RADIUS - x, x - (right - RADIUS), 0)
    dy = max(top + RADIUS - y, y - (bottom - RADIUS), 0)
    return dx * dx + dy * dy <= RADIUS * RADIUS


def colour(x, y):
    result = PLUM
    for shade, tab, body in FOLDERS:
        if inside(x, y, tab) or inside(x, y, body):
            result = shade
    return result


def pixel(column, row, size):
    total = [0, 0, 0]
    for i in range(SAMPLES):
        for j in range(SAMPLES):
            x = (column + (i + 0.5) / SAMPLES) * 100 / size
            y = (row + (j + 0.5) / SAMPLES) * 100 / size
            for channel, value in enumerate(colour(x, y)):
                total[channel] += value
    return bytes(value // (SAMPLES * SAMPLES) for value in total)


def chunk(kind, data):
    body = kind + data
    return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body))


def write_png(path, size):
    rows = b""
    for row in range(size):
        rows += b"\x00" + b"".join(pixel(column, row, size) for column in range(size))
    header = struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header)
    png += chunk(b"IDAT", zlib.compress(rows)) + chunk(b"IEND", b"")
    path.write_bytes(png)
    print("wrote", path)


public = Path("frontend/public")
write_png(public / "icon-192.png", 192)
write_png(public / "icon-512.png", 512)
write_png(public / "apple-touch-icon.png", 180)