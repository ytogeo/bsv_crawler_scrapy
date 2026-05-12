from __future__ import annotations

import argparse
import time

from streetview_crawler.config import load_config
from streetview_crawler.services.asset_downloader import download_and_stitch_panorama
from streetview_crawler.services.db import MySQLRepository
from streetview_crawler.services.redis_queue import RedisAssetQueue


def run_worker(job_id: str, config_path: str, idle_timeout: int = 5) -> int:
    config = load_config(config_path)
    key_prefix = config.get("redis", {}).get("key_prefix", "streetview")
    queue = RedisAssetQueue.from_env(job_id, key_prefix)
    db = MySQLRepository.from_env()
    try:
        while True:
            task = queue.pop_asset_task(timeout=idle_timeout)
            if task is None:
                if queue.metadata_done():
                    return 0
                continue

            try:
                file_info = download_and_stitch_panorama(task, config)
                db.upsert_pano_asset_success(task, file_info)
            except Exception as exc:
                message = str(exc)
                db.upsert_pano_asset_failed(task, message)
                db.insert_crawl_error(
                    {
                        "job_id": task["job_id"],
                        "stage": "asset",
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

