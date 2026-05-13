"""
街景 metadata spider。

StreetviewSpider 负责 seed 和 metadata 两个阶段的 Scrapy 请求流程：
- 加载当前 job 的配置
- 从 MySQL 读取可恢复的 seed / metadata 任务
- 构造 seed 和 metadata Request
- 将 seed 响应解析为 SeedTaskItem
- 将 metadata 响应解析为 PanoItem
- 将请求失败转换为 CrawlErrorItem

该 spider 不直接写 MySQL、不推 Redis、不下载图片，也不生成报告。
这些职责分别由 Item Pipeline、pano worker 和 reporting 服务承担。
"""

from __future__ import annotations

import scrapy

from streetview_crawler.config import load_config
from streetview_crawler.items import CrawlErrorItem, PanoItem, SeedTaskItem
from streetview_crawler.providers.baidu import (
    build_metadata_url,
    build_seed_url,
    extract_capture_date,
    extract_pano_lat,
    extract_pano_lng,
    extract_panoid_from_seed,
)
from streetview_crawler.services.db import MySQLRepository


class StreetviewSpider(scrapy.Spider):
    name = "streetview"

    def __init__(self, job_id: str, config_path: str, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.job_id = job_id
        self.config_path = config_path
        self.config = load_config(config_path)
        self.provider = self.config.get("crawler", {}).get("provider", "baidu")
        self.db: MySQLRepository | None = None

    @classmethod
    def update_settings(cls, settings):
        super().update_settings(settings)
        # Config values can still be overridden through environment variables.

    def start_requests(self):
        self.db = MySQLRepository.from_settings(self.settings)
        # MySQL 保存阶段状态，spider 从仍需补跑的任务开始生成 Request。
        for row in self.db.fetch_seed_requests(self.job_id):
            yield self._build_seed_request(row)

        for row in self.db.fetch_metadata_requests(self.job_id):
            yield self._build_metadata_request(row)

    def closed(self, reason: str) -> None:
        if self.db is not None:
            self.db.close()

    def _build_seed_request(self, row: dict):
        url = build_seed_url(row["lng"], row["lat"])
        return scrapy.Request(
            url=url,
            callback=self.parse_seed,
            errback=self.handle_error,
            dont_filter=True,
            meta={
                "stage": "seed",
                "point_index": row["point_index"],
                "lng": row["lng"],
                "lat": row["lat"],
            },
        )

    def _build_metadata_request(self, row: dict):
        url = build_metadata_url(row["panoid"])
        return scrapy.Request(
            url=url,
            callback=self.parse_metadata,
            errback=self.handle_error,
            dont_filter=True,
            meta={
                "stage": "metadata",
                "point_index": row["point_index"],
                "lng": row["lng"],
                "lat": row["lat"],
                "panoid": row["panoid"],
            },
        )

    def parse_seed(self, response):
        point_index = response.meta["point_index"]
        lng = response.meta["lng"]
        lat = response.meta["lat"]
        data = response.json()
        panoid = extract_panoid_from_seed(data)

        if not panoid:
            yield SeedTaskItem(
                job_id=self.job_id,
                point_index=point_index,
                lng=lng,
                lat=lat,
                status="empty",
                panoid=None,
                error_message=None,
            )
            return

        yield SeedTaskItem(
            job_id=self.job_id,
            point_index=point_index,
            lng=lng,
            lat=lat,
            status="found",
            panoid=panoid,
            error_message=None,
        )
        yield self._build_metadata_request(
            {"point_index": point_index, "lng": lng, "lat": lat, "panoid": panoid}
        )

    def parse_metadata(self, response):
        data = response.json()
        panoid = response.meta["panoid"]
        yield PanoItem(
            job_id=self.job_id,
            panoid=panoid,
            source_point_index=response.meta["point_index"],
            source_lng=response.meta["lng"],
            source_lat=response.meta["lat"],
            pano_lng=extract_pano_lng(data),
            pano_lat=extract_pano_lat(data),
            capture_date=extract_capture_date(data),
            provider=self.provider,
            raw_json=data,
        )

    def handle_error(self, failure):
        request = failure.request
        stage = request.meta.get("stage", "unknown")

        if stage == "seed":
            yield SeedTaskItem(
                job_id=self.job_id,
                point_index=request.meta["point_index"],
                lng=request.meta["lng"],
                lat=request.meta["lat"],
                status="failed",
                panoid=None,
                error_message=str(failure.value),
            )

        yield CrawlErrorItem(
            job_id=self.job_id,
            stage=stage,
            url=request.url,
            point_index=request.meta.get("point_index"),
            panoid=request.meta.get("panoid"),
            error_type=type(failure.value).__name__,
            error_message=str(failure.value),
            context_json=dict(request.meta),
        )
