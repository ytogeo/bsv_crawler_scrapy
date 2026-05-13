"""
MySQL Repository，封装采集系统的持久化读写和状态查询。

该模块集中管理与 MySQL 相关的 SQL，避免 spider、pipeline、worker 和 CLI
直接操作 cursor 或拼写 SQL。它负责把数据库表结构、幂等写入策略和断点重跑
判断封装在统一的数据访问接口中。

主要封装：
- job 生命周期：create_job、update_job_status
- seed 状态写入：upsert_seed_tasks_pending、upsert_seed_task
- pano 元数据写入：upsert_pano
- pano 文件结果写入：upsert_pano_file_success、upsert_pano_file_failed
- 错误记录写入：insert_crawl_error
- 断点重跑查询：fetch_seed_requests、fetch_metadata_requests、fetch_missing_pano_file_tasks
- 报告统计查询：job_counts

设计上属于 Repository Pattern 的简化实现。调用方只关心“读写哪类业务状态”，
不需要关心具体 SQL、唯一键和 upsert 细节。
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any, Iterable


class MySQLRepository:
    def __init__(self, connection: Any) -> None:
        self.connection = connection

    @classmethod
    def from_env(cls) -> "MySQLRepository":
        import pymysql
        from pymysql.cursors import DictCursor

        return cls(
            pymysql.connect(
                host=os.getenv("MYSQL_HOST", "127.0.0.1"),
                port=int(os.getenv("MYSQL_PORT", "3306")),
                user=os.getenv("MYSQL_USER", "root"),
                password=os.getenv("MYSQL_PASSWORD", "root"),
                database=os.getenv("MYSQL_DATABASE", "streetview"),
                charset="utf8mb4",
                cursorclass=DictCursor,
                autocommit=True,
            )
        )

    @classmethod
    def from_settings(cls, settings: Any) -> "MySQLRepository":
        import pymysql
        from pymysql.cursors import DictCursor

        return cls(
            pymysql.connect(
                host=settings.get("MYSQL_HOST", "127.0.0.1"),
                port=settings.getint("MYSQL_PORT", 3306),
                user=settings.get("MYSQL_USER", "root"),
                password=settings.get("MYSQL_PASSWORD", "root"),
                database=settings.get("MYSQL_DATABASE", "streetview"),
                charset="utf8mb4",
                cursorclass=DictCursor,
                autocommit=True,
            )
        )

    def create_job(self, job_id: str, config_path: str) -> None:
        sql = """
        INSERT INTO crawl_job (id, status, config_path, started_at)
        VALUES (%s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE status = VALUES(status), updated_at = CURRENT_TIMESTAMP
        """
        self.execute(sql, (job_id, "running", config_path, datetime.utcnow()))

    def update_job_status(self, job_id: str, status: str) -> None:
        sql = """
        UPDATE crawl_job
        SET status = %s, finished_at = CASE WHEN %s IN ('success', 'failed', 'partial') THEN %s ELSE finished_at END
        WHERE id = %s
        """
        now = datetime.utcnow()
        self.execute(sql, (status, status, now, job_id))

    def upsert_seed_tasks_pending(self, job_id: str, points: Iterable[dict[str, Any]]) -> int:
        count = 0
        sql = """
        INSERT INTO seed_task (job_id, point_index, lng, lat, status)
        VALUES (%s, %s, %s, %s, 'pending')
        ON DUPLICATE KEY UPDATE lng = VALUES(lng), lat = VALUES(lat)
        """
        with self.connection.cursor() as cursor:
            for point in points:
                cursor.execute(sql, (job_id, point["point_index"], point["lng"], point["lat"]))
                count += 1
        return count

    def upsert_seed_task(self, item: dict[str, Any]) -> None:
        sql = """
        INSERT INTO seed_task (job_id, point_index, lng, lat, status, panoid, error_message)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
          lng = VALUES(lng),
          lat = VALUES(lat),
          status = VALUES(status),
          panoid = VALUES(panoid),
          error_message = VALUES(error_message)
        """
        self.execute(
            sql,
            (
                item["job_id"],
                item["point_index"],
                item["lng"],
                item["lat"],
                item["status"],
                item.get("panoid"),
                item.get("error_message"),
            ),
        )

    def upsert_pano(self, item: dict[str, Any]) -> None:
        sql = """
        INSERT INTO pano (
          job_id, panoid, source_point_index, source_lng, source_lat,
          pano_lng, pano_lat, capture_date, provider, raw_json
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
          source_point_index = VALUES(source_point_index),
          source_lng = VALUES(source_lng),
          source_lat = VALUES(source_lat),
          pano_lng = VALUES(pano_lng),
          pano_lat = VALUES(pano_lat),
          capture_date = VALUES(capture_date),
          provider = VALUES(provider),
          raw_json = VALUES(raw_json)
        """
        self.execute(
            sql,
            (
                item["job_id"],
                item["panoid"],
                item.get("source_point_index"),
                item.get("source_lng"),
                item.get("source_lat"),
                item.get("pano_lng"),
                item.get("pano_lat"),
                item.get("capture_date"),
                item.get("provider", "baidu"),
                json.dumps(item.get("raw_json", {}), ensure_ascii=False),
            ),
        )

    def upsert_pano_file_success(self, task: dict[str, Any], file_info: dict[str, Any]) -> None:
        sql = """
        INSERT INTO pano_file (
          job_id, panoid, file_type, file_spec, file_path, file_size_bytes,
          width, height, sha256, status, error_message
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'success', NULL)
        ON DUPLICATE KEY UPDATE
          file_path = VALUES(file_path),
          file_size_bytes = VALUES(file_size_bytes),
          width = VALUES(width),
          height = VALUES(height),
          sha256 = VALUES(sha256),
          status = 'success',
          error_message = NULL
        """
        self.execute(
            sql,
            (
                task["job_id"],
                task["panoid"],
                task["file_type"],
                task["file_spec"],
                file_info["file_path"],
                file_info["file_size_bytes"],
                file_info["width"],
                file_info["height"],
                file_info["sha256"],
            ),
        )

    def upsert_pano_file_failed(self, task: dict[str, Any], error_message: str) -> None:
        sql = """
        INSERT INTO pano_file (job_id, panoid, file_type, file_spec, status, error_message)
        VALUES (%s, %s, %s, %s, 'failed', %s)
        ON DUPLICATE KEY UPDATE status = 'failed', error_message = VALUES(error_message)
        """
        self.execute(
            sql,
            (task["job_id"], task["panoid"], task["file_type"], task["file_spec"], error_message),
        )

    def insert_crawl_error(self, item: dict[str, Any]) -> None:
        sql = """
        INSERT INTO crawl_error (
          job_id, stage, url, point_index, panoid, error_type, error_message, context_json
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        self.execute(
            sql,
            (
                item["job_id"],
                item["stage"],
                item.get("url"),
                item.get("point_index"),
                item.get("panoid"),
                item["error_type"],
                item["error_message"],
                json.dumps(item.get("context_json") or {}, ensure_ascii=False),
            ),
        )

    def fetch_seed_requests(self, job_id: str) -> list[dict[str, Any]]:
        return self.fetchall(
            """
            SELECT point_index, lng, lat
            FROM seed_task
            WHERE job_id = %s AND status IN ('pending', 'failed')
            ORDER BY point_index
            """,
            (job_id,),
        )

    def fetch_metadata_requests(self, job_id: str) -> list[dict[str, Any]]:
        return self.fetchall(
            """
            SELECT s.point_index, s.lng, s.lat, s.panoid
            FROM seed_task s
            LEFT JOIN pano p ON s.job_id = p.job_id AND s.panoid = p.panoid
            WHERE s.job_id = %s
              AND s.status = 'found'
              AND s.panoid IS NOT NULL
              AND p.panoid IS NULL
            ORDER BY s.point_index
            """,
            (job_id,),
        )

    def fetch_missing_pano_file_tasks(self, job_id: str, file_type: str, file_spec: str) -> list[dict[str, Any]]:
        rows = self.fetchall(
            """
            SELECT p.job_id, p.panoid
            FROM pano p
            LEFT JOIN pano_file a
              ON p.job_id = a.job_id
             AND p.panoid = a.panoid
             AND a.file_type = %s
             AND a.file_spec = %s
             AND a.status = 'success'
            WHERE p.job_id = %s AND a.panoid IS NULL
            ORDER BY p.panoid
            """,
            (file_type, file_spec, job_id),
        )
        return [
            {"job_id": row["job_id"], "panoid": row["panoid"], "file_type": file_type, "file_spec": file_spec}
            for row in rows
        ]

    def job_counts(self, job_id: str) -> dict[str, Any]:
        return {
            "seed": self.fetchall("SELECT status, COUNT(*) AS count FROM seed_task WHERE job_id=%s GROUP BY status", (job_id,)),
            "pano_count": self.fetchone("SELECT COUNT(*) AS count FROM pano WHERE job_id=%s", (job_id,))["count"],
            "pano_file": self.fetchall("SELECT status, COUNT(*) AS count FROM pano_file WHERE job_id=%s GROUP BY status", (job_id,)),
            "errors": self.fetchall("SELECT stage, COUNT(*) AS count FROM crawl_error WHERE job_id=%s GROUP BY stage", (job_id,)),
            "error_samples": self.fetchall(
                "SELECT stage, error_type, error_message FROM crawl_error WHERE job_id=%s ORDER BY id DESC LIMIT 10",
                (job_id,),
            ),
        }

    def execute(self, sql: str, params: tuple[Any, ...]) -> None:
        with self.connection.cursor() as cursor:
            cursor.execute(sql, params)

    def fetchone(self, sql: str, params: tuple[Any, ...]) -> dict[str, Any] | None:
        with self.connection.cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.fetchone()

    def fetchall(self, sql: str, params: tuple[Any, ...]) -> list[dict[str, Any]]:
        with self.connection.cursor() as cursor:
            cursor.execute(sql, params)
            return list(cursor.fetchall())

    def close(self) -> None:
        self.connection.close()
