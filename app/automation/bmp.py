from __future__ import annotations

import struct
from pathlib import Path


def _read_bmp(path: Path) -> tuple[int, int, int, bytes, int]:
    data = path.read_bytes()
    if data[:2] != b"BM":
        raise ValueError(f"{path} is not a BMP file.")
    offset = struct.unpack_from("<I", data, 10)[0]
    width = struct.unpack_from("<i", data, 18)[0]
    height = struct.unpack_from("<i", data, 22)[0]
    bits_per_pixel = struct.unpack_from("<H", data, 28)[0]
    compression = struct.unpack_from("<I", data, 30)[0]
    if compression != 0:
        raise ValueError("Compressed BMP is not supported.")
    if bits_per_pixel not in (24, 32):
        raise ValueError(f"Unsupported BMP bit depth: {bits_per_pixel}")
    return width, height, bits_per_pixel, data, offset


def _pixel_at(width: int, height: int, bits_per_pixel: int, data: bytes, offset: int, x: int, y: int) -> tuple[int, int, int]:
    top_down = height < 0
    actual_height = abs(height)
    row_size = ((bits_per_pixel * width + 31) // 32) * 4
    row_index = y if top_down else (actual_height - 1 - y)
    row_start = offset + row_index * row_size
    step = bits_per_pixel // 8
    px = row_start + (x * step)
    blue = data[px]
    green = data[px + 1]
    red = data[px + 2]
    return red, green, blue


def compute_signature(path: Path, grid_size: int = 16) -> str:
    width, height, bits_per_pixel, data, offset = _read_bmp(path)
    actual_height = abs(height)
    signature_parts: list[str] = []
    for gy in range(grid_size):
        y = min(actual_height - 1, int((gy + 0.5) * actual_height / grid_size))
        for gx in range(grid_size):
            x = min(width - 1, int((gx + 0.5) * width / grid_size))
            red, green, blue = _pixel_at(width, height, bits_per_pixel, data, offset, x, y)
            luminance = int((0.299 * red) + (0.587 * green) + (0.114 * blue))
            signature_parts.append(f"{luminance // 16:x}")
    return "".join(signature_parts)


def normalized_distance(left: str | None, right: str) -> float:
    if not left:
        return 1.0
    if len(left) != len(right):
        return 1.0
    mismatches = sum(1 for a, b in zip(left, right, strict=True) if a != b)
    return mismatches / len(right)
