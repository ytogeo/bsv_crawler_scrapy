"""
Redis pano 下载队列服务，封装图片任务的运行期分发、去重和完成信号。

该模块统一管理每个 job 对应的 Redis key，并提供 Pipeline 与 pano worker
之间的任务队列接口。Redis 在本项目中只承担运行期队列职责，不作为持久化
任务事实来源。

主要封装：
- pano_download_queue：待处理 pano 下载任务的 Redis list
- pano_download_seen：防止同一 pano 文件任务在运行期重复入队的 Redis set
- metadata_done：通知 worker metadata 阶段已结束的完成标记
- enqueue_pano_download_once：按 panoid + file_type + file_spec 去重后入队
- pop_pano_download_task：阻塞式消费 pano 下载任务
- clear_job_keys：清理当前 job 的运行期 Redis 状态

断点重跑时应以 MySQL 状态为依据重建 Redis 队列。
"""

from __future__ import annotations

import json
import os
from typing import Any

import redis


class RedisPanoDownloadQueue:
    def __init__(self, client: Any, key_prefix: str, job_id: str) -> None:
        self.client = client
        self.key_prefix = key_prefix
        self.job_id = job_id

    @classmethod
    def from_env(cls, job_id: str, key_prefix: str = "streetview") -> "RedisPanoDownloadQueue":
        client = redis.Redis(
            host=os.getenv("REDIS_HOST", "127.0.0.1"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            db=int(os.getenv("REDIS_DB", "0")),
            decode_responses=True,
        )
        return cls(client, key_prefix, job_id)

    @classmethod
    def from_settings(cls, settings: Any, job_id: str, key_prefix: str = "streetview") -> "RedisPanoDownloadQueue":
        client = redis.Redis(
            host=settings.get("REDIS_HOST", "127.0.0.1"),
            port=settings.getint("REDIS_PORT", 6379),
            db=settings.getint("REDIS_DB", 0),
            decode_responses=True,
        )
        return cls(client, key_prefix, job_id)

    @property
    def pano_download_queue_key(self) -> str:
        return f"{self.key_prefix}:{self.job_id}:pano_download_queue"

    @property
    def pano_download_seen_key(self) -> str:
        return f"{self.key_prefix}:{self.job_id}:pano_download_seen"

    @property
    def metadata_done_key(self) -> str:
        return f"{self.key_prefix}:{self.job_id}:metadata_done"

    def enqueue_pano_download_once(self, job_id: str, panoid: str, file_type: str, file_spec: str) -> bool:
        pano_file_key = f"{panoid}:{file_type}:{file_spec}"
        added = self.client.sadd(self.pano_download_seen_key, pano_file_key)
        if added:
            task = {
                "job_id": job_id,
                "panoid": panoid,
                "file_type": file_type,
                "file_spec": file_spec,
            }
            self.client.lpush(self.pano_download_queue_key, json.dumps(task, ensure_ascii=False))
            return True
        return False

    def push_pano_download_task(self, task: dict[str, Any]) -> None:
        pano_file_key = f"{task['panoid']}:{task['file_type']}:{task['file_spec']}"
        self.client.sadd(self.pano_download_seen_key, pano_file_key)
        self.client.lpush(self.pano_download_queue_key, json.dumps(task, ensure_ascii=False))

    def pop_pano_download_task(self, timeout: int = 5) -> dict[str, Any] | None:
        value = self.client.brpop(self.pano_download_queue_key, timeout=timeout)
        if value is None:
            return None
        _, payload = value
        return json.loads(payload)

    def set_metadata_done(self) -> None:
        self.client.set(self.metadata_done_key, "1")

    def metadata_done(self) -> bool:
        return self.client.get(self.metadata_done_key) == "1"

    def clear_job_keys(self) -> None:
        self.client.delete(self.pano_download_queue_key, self.pano_download_seen_key, self.metadata_done_key)

    def close(self) -> None:
        self.client.close()
