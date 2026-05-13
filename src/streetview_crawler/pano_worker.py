"""
全景图下载 worker 入口。

该模块消费 Redis 中的 pano_download_task，调用 svi_processing 完成瓦片下载和全景拼接，
并将成功或失败状态写入 MySQL。它是独立进程，便于和 Scrapy spider 并行运行。
"""

from __future__ import annotations

import argparse
import time

from streetview_crawler.config import load_config
from streetview_crawler.svi_processing.downloader import download_and_stitch_pano
from streetview_crawler.services.db import MySQLRepository
from streetview_crawler.services.redis_queue import RedisPanoDownloadQueue


def run_worker(job_id: str, config_path: str, idle_timeout: int = 5) -> int:
    config = load_config(config_path)
    key_prefix = config.get("redis", {}).get("key_prefix", "streetview")
    queue = RedisPanoDownloadQueue.from_env(job_id, key_prefix)
    db = MySQLRepository.from_env()
    try:
        while True:
            task = queue.pop_pano_download_task(timeout=idle_timeout)
            if task is None:
                if queue.metadata_done():
                    return 0
                continue

            try:
                file_info = download_and_stitch_pano(task, config)
                db.upsert_pano_file_success(task, file_info)
            except Exception as exc:
                message = str(exc)
                db.upsert_pano_file_failed(task, message)
                db.insert_crawl_error(
                    {
                        "job_id": task["job_id"],
                        "stage": "pano_download",
                        "url": None,
                        "point_index": None,
                        "panoid": task.get("panoid"),
                        "error_type": type(exc).__name__,
                        "error_message": message,
                        "context_json": task,
                    }
                )
                time.sleep(0.2)
    finally:
        db.close()
        queue.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--idle-timeout", type=int, default=5)
    args = parser.parse_args(argv)
    return run_worker(args.job_id, args.config, args.idle_timeout)


if __name__ == "__main__":
    raise SystemExit(main())
