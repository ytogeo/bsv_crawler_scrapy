from __future__ import annotations

import argparse
import os
import subprocess
import sys
from datetime import datetime

from streetview_crawler.config import load_config, project_root, resolve_path
from streetview_crawler.geo.seed_points import generate_seed_points
from streetview_crawler.services.db import MySQLRepository
from streetview_crawler.services.redis_queue import RedisAssetQueue
from streetview_crawler.services.reporting import write_report


def run_job(config_path: str, job_id: str | None = None, resume: bool = False) -> int:
    config = load_config(config_path)
    job_id = job_id or f"job_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
    db = MySQLRepository.from_env()
    key_prefix = config.get("redis", {}).get("key_prefix", "streetview")
    queue = RedisAssetQueue.from_env(job_id, key_prefix)

    try:
        if not resume:
            db.create_job(job_id, config["_config_path"])
            points = generate_seed_points(resolve_path(config, config["aoi_path"]), float(config["sample_interval_m"]))
            db.upsert_seed_tasks_pending(job_id, points)
        else:
            db.update_job_status(job_id, "running")

        queue.clear_job_keys()
        _rebuild_asset_queue_from_mysql(db, queue, job_id, config)

        worker_count = int(config.get("assets", {}).get("workers", 2))
        workers = [_start_worker(job_id, config_path) for _ in range(worker_count)]
        spider = _start_spider(job_id, config_path)

        spider_code = spider.wait()
        queue.set_metadata_done()

        worker_codes = [worker.wait() for worker in workers]
        status = _final_status(spider_code, worker_codes)
        db.update_job_status(job_id, status)
        write_report(job_id, config, db)
        print(f"job_id={job_id} status={status}")
        return 0 if status in {"success", "partial"} else 1
    finally:
        db.close()
        queue.close()


def _rebuild_asset_queue_from_mysql(db: MySQLRepository, queue: RedisAssetQueue, job_id: str, config: dict) -> None:
    asset_config = config.get("assets", {})
    tasks = db.fetch_missing_asset_tasks(
        job_id,
        asset_config.get("asset_type", "panorama"),
        asset_config.get("asset_spec", "full"),
    )
    for task in tasks:
        queue.push_asset_task(task)


def _start_spider(job_id: str, config_path: str) -> subprocess.Popen:
    return subprocess.Popen(
        [
            sys.executable,
            "-m",
            "scrapy",
            "crawl",
            "streetview",
            "-a",
            f"job_id={job_id}",
            "-a",
            f"config_path={config_path}",
        ],
        cwd=project_root(),
        env=_child_env(),
    )


def _start_worker(job_id: str, config_path: str) -> subprocess.Popen:
    return subprocess.Popen(
        [
            sys.executable,
            "-m",
            "streetview_crawler.asset_worker",
            "--job-id",
            job_id,
            "--config",
            config_path,
        ],
        cwd=project_root(),
        env=_child_env(),
    )


def _child_env() -> dict[str, str]:
    env = os.environ.copy()
    src = str(project_root() / "src")
    env["PYTHONPATH"] = src + os.pathsep + env.get("PYTHONPATH", "")
    return env


def _final_status(spider_code: int, worker_codes: list[int]) -> str:
    if spider_code != 0:
        return "failed"
    if any(code != 0 for code in worker_codes):
        return "partial"
    return "success"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run-job")
    run_parser.add_argument("--config", required=True)
    run_parser.add_argument("--job-id")

    resume_parser = subparsers.add_parser("resume-job")
    resume_parser.add_argument("--config", required=True)
    resume_parser.add_argument("--job-id", required=True)

    args = parser.parse_args(argv)
    if args.command == "run-job":
        return run_job(args.config, args.job_id, resume=False)
    if args.command == "resume-job":
        return run_job(args.config, args.job_id, resume=True)
    raise ValueError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())

