"""
全景图下载与拼接编排模块。

该模块把一个 pano 下载任务转换为一个本地全景图文件，负责：
- 根据 job_id 和 panoid 解析输出路径
- 调用 provider URL 构造函数下载街景瓦片
- 调用 stitcher 完成全景拼接、保存和文件检查
- 返回写入 pano_file 表所需的文件元数据

模块不直接写数据库，也不读取 Redis；队列消费和状态持久化由 pano_worker 负责。
"""

from __future__ import annotations

from io import BytesIO
from typing import Any

import requests
from PIL import Image

from streetview_crawler.svi_processing.stitcher import inspect_image, save_image, stitch_grid
from streetview_crawler.config import resolve_path
from streetview_crawler.providers.baidu import build_panorama_tile_url, get_panorama_tile_shape


def download_and_stitch_pano(task: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    pano_file_config = config.get("pano_file", {})
    output_dir = resolve_path(config, config.get("output_dir", "data/images"))
    job_id = task["job_id"]
    panoid = task["panoid"]
    out_path = output_dir / job_id / f"{panoid}.jpg"

    zoom = int(pano_file_config.get("tile_zoom", 4))
    x_count, y_count = get_panorama_tile_shape(zoom)

    tiles: list[Image.Image] = []
    session = requests.Session()
    for x_index in range(x_count):
        for y_index in range(y_count):
            tiles.append(_download_tile(session, panoid, x_index, y_index, zoom))

    panorama = stitch_grid(tiles, cols=y_count, rows=x_count)
    save_image(panorama, out_path)
    return inspect_image(out_path)


def _download_tile(session: requests.Session, panoid: str, x: int, y: int, zoom: int) -> Image.Image:
    url = build_panorama_tile_url(panoid, x, y, zoom)
    response = session.get(url, timeout=15)
    response.raise_for_status()
    return Image.open(BytesIO(response.content)).convert("RGB")

