from __future__ import annotations

import hashlib
from pathlib import Path

from PIL import Image, ImageDraw


def stitch_grid(tiles: list[Image.Image], cols: int, rows: int) -> Image.Image:
    if len(tiles) != cols * rows:
        raise ValueError(f"expected {cols * rows} tiles, got {len(tiles)}")
    width, height = tiles[0].size
    canvas = Image.new("RGB", (cols * width, rows * height))
    for index, tile in enumerate(tiles):
        x = (index % cols) * width
        y = (index // cols) * height
        canvas.paste(tile.convert("RGB"), (x, y))
    return canvas


def make_mock_tile(panoid: str, tile_x: int, tile_y: int, width: int, height: int) -> Image.Image:
    digest = hashlib.sha1(f"{panoid}:{tile_x}:{tile_y}".encode("utf-8")).hexdigest()
    color = tuple(int(digest[i : i + 2], 16) for i in (0, 2, 4))
    image = Image.new("RGB", (width, height), color)
    draw = ImageDraw.Draw(image)
    draw.text((16, 16), f"{panoid}\n{tile_x},{tile_y}", fill=(255, 255, 255))
    return image


def save_image(image: Image.Image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, format="JPEG", quality=92)


def compute_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inspect_image(path: Path) -> dict:
    with Image.open(path) as image:
        width, height = image.size
    return {
        "file_path": str(path),
        "file_size_bytes": path.stat().st_size,
        "width": width,
        "height": height,
        "sha256": compute_sha256(path),
    }

