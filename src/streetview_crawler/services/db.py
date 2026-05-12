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

    def upsert_pano_asset_success(self, task: dict[str, Any], file_info: dict[str, Any]) -> None:
        sql = """
        INSERT INTO pano_asset (
          job_id, panoid, asset_type, asset_spec, file_path, file_size_bytes,
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
                task["asset_type"],
                task["asset_spec"],
                file_info["file_path"],
                file_info["file_size_bytes"],
                file_info["width"],
                file_info["height"],
                file_info["sha256"],
            ),
        )

    def upsert_pano_asset_failed(self, task: dict[str, Any], error_message: str) -> None:
        sql = """
        INSERT INTO pano_asset (job_id, panoid, asset_type, asset_spec, status, error_message)
        VALUES (%s, %s, %s, %s, 'failed', %s)
        ON DUPLICATE KEY UPDATE status = 'failed', error_message = VALUES(error_message)
        """
        self.execute(
            sql,
            (task["job_id"], task["panoid"], task["asset_type"], task["asset_spec"], error_message),
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

    def fetch_missing_asset_tasks(self, job_id: str, asset_type: str, asset_spec: str) -> list[dict[str, Any]]:
        rows = self.fetchall(
            """
            SELECT p.job_id, p.panoid
            FROM pano p
            LEFT JOIN pano_asset a
              ON p.job_id = a.job_id
             AND p.panoid = a.panoid
             AND a.asset_type = %s
             AND a.asset_spec = %s
             AND a.status = 'success'
            WHERE p.job_id = %s AND a.panoid IS NULL
            ORDER BY p.panoid
            """,
            (asset_type, asset_spec, job_id),
        )
        return [
            {"job_id": row["job_id"], "panoid": row["panoid"], "asset_type": asset_type, "asset_spec": asset_spec}
            for row in rows
        ]

    def job_counts(self, job_id: str) -> dict[str, Any]:
        return {
            "seed": self.fetchall("SELECT status, COUNT(*) AS count FROM seed_task WHERE job_id=%s GROUP BY status", (job_id,)),
            "pano_count": self.fetchone("SELECT COUNT(*) AS count FROM pano WHERE job_id=%s", (job_id,))["count"],
            "asset": self.fetchall("SELECT status, COUNT(*) AS count FROM pano_asset WHERE job_id=%s GROUP BY status", (job_id,)),
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
