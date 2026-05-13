"""
Scrapy Item Pipeline 模块，负责 Item 的持久化和 pano 下载任务派发。

StreetviewPipeline 通过 settings.ITEM_PIPELINES 注册。Spider yield Item 后，
Scrapy 会自动调用 process_item。

当前处理逻辑：
- SeedTaskItem：将 seed_task 状态写入 MySQL
- PanoItem：将 pano 元数据写入 MySQL，并向 Redis 推入一个 pano 下载任务
- CrawlErrorItem：将标准化错误记录写入 MySQL

Pipeline 不发起 HTTP 请求，也不处理图片文件。HTTP 抓取属于 spider，
图片下载和拼接属于 pano worker。
"""

from __future__ import annotations

from streetview_crawler.items import CrawlErrorItem, PanoItem, SeedTaskItem
from streetview_crawler.services.db import MySQLRepository
from streetview_crawler.services.redis_queue import RedisPanoDownloadQueue


class StreetviewPipeline:
    def open_spider(self, spider) -> None:
        self.db = MySQLRepository.from_settings(spider.settings)
        key_prefix = spider.config.get("redis", {}).get("key_prefix", "streetview")
        self.queue = RedisPanoDownloadQueue.from_settings(spider.settings, spider.job_id, key_prefix)

    def process_item(self, item, spider):
        if isinstance(item, SeedTaskItem):
            self.db.upsert_seed_task(dict(item))
        elif isinstance(item, PanoItem):
            pano = dict(item)
            self.db.upsert_pano(pano)
            pano_file_config = spider.config.get("pano_file", {})
            if pano_file_config.get("enabled", True):
                self.queue.enqueue_pano_download_once(
                    job_id=pano["job_id"],
                    panoid=pano["panoid"],
                    file_type=pano_file_config.get("file_type", "panorama"),
                    file_spec=pano_file_config.get("file_spec", "full"),
                )
        elif isinstance(item, CrawlErrorItem):
            self.db.insert_crawl_error(dict(item))
        return item

    def close_spider(self, spider) -> None:
        self.queue.close()
        self.db.close()
