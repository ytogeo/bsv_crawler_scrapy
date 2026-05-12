from __future__ import annotations

from streetview_crawler.items import CrawlErrorItem, PanoItem, SeedTaskItem
from streetview_crawler.services.db import MySQLRepository
from streetview_crawler.services.redis_queue import RedisAssetQueue


class StreetviewPipeline:
    def open_spider(self, spider) -> None:
        self.db = MySQLRepository.from_settings(spider.settings)
        key_prefix = spider.config.get("redis", {}).get("key_prefix", "streetview")
        self.queue = RedisAssetQueue.from_settings(spider.settings, spider.job_id, key_prefix)

    def process_item(self, item, spider):
        if isinstance(item, SeedTaskItem):
            self.db.upsert_seed_task(dict(item))
        elif isinstance(item, PanoItem):
            pano = dict(item)
            self.db.upsert_pano(pano)
            asset_config = spider.config.get("assets", {})
            if asset_config.get("enabled", True):
                self.queue.enqueue_asset_once(
                    job_id=pano["job_id"],
                    panoid=pano["panoid"],
                    asset_type=asset_config.get("asset_type", "panorama"),
                    asset_spec=asset_config.get("asset_spec", "full"),
                )
        elif isinstance(item, CrawlErrorItem):
            self.db.insert_crawl_error(dict(item))
        return item

    def close_spider(self, spider) -> None:
        self.queue.close()
        self.db.close()

