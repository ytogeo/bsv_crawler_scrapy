"""
全景图文件处理工具模块。

该模块只包含纯图片/文件操作：
- 将 Pillow 图片瓦片按网格拼接为全景图
- 将图片保存到本地
- 计算文件 SHA256 指纹
- 读取已保存图片的尺寸和文件元数据

模块不依赖 Redis、MySQL 或 Scrapy。
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from PIL import Image


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

