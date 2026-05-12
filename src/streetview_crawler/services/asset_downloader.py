from __future__ import annotations

from io import BytesIO
from typing import Any

import requests
from PIL import Image

from streetview_crawler.config import resolve_path
from streetview_crawler.services.image_stitcher import inspect_image, make_mock_tile, save_image, stitch_grid


def download_and_stitch_panorama(task: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    assets = config.get("assets", {})
    output_dir = resolve_path(config, config.get("output_dir", "data/images"))
    job_id = task["job_id"]
    panoid = task["panoid"]
    out_path = output_dir / job_id / f"{panoid}.jpg"

    cols = int(assets.get("tile_cols", 4))
    rows = int(assets.get("tile_rows", 2))
    tile_width = int(assets.get("tile_width", 256))
    tile_height = int(assets.get("tile_height", 256))
    mock_download = bool(assets.get("mock_download", True))

    tiles: list[Image.Image] = []
    session = requests.Session()
    for y in range(rows):
        for x in range(cols):
            if mock_download:
                tiles.append(make_mock_tile(panoid, x, y, tile_width, tile_height))
            else:
                tiles.append(_download_tile(session, panoid, x, y, int(assets.get("tile_zoom", 4))))

    panorama = stitch_grid(tiles, cols, rows)
    save_image(panorama, out_path)
    return inspect_image(out_path)


def _download_tile(session: requests.Session, panoid: str, x: int, y: int, zoom: int) -> Image.Image:
    url = f"https://mapsv0.bdimg.com/?qt=pdata&sid={panoid}&pos={x}_{y}&z={zoom}"
    response = session.get(url, timeout=15)
    response.raise_for_status()
    return Image.open(BytesIO(response.content)).convert("RGB")

