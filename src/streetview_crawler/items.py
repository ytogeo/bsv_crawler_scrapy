"""
Scrapy Item 定义模块。

Item 是 spider 产出的结构化数据，也是 spider callback 与后续 pipeline
之间的数据契约。Spider 只负责 yield Item，具体的持久化和队列派发由
Pipeline 处理。

当前定义：
- SeedTaskItem：seed point 的处理结果
- PanoItem：已确认 pano 的元数据和完整 raw_json
- CrawlErrorItem：seed、metadata、pano_download 阶段的标准化错误记录
"""

import scrapy


class SeedTaskItem(scrapy.Item):
    job_id = scrapy.Field()
    point_index = scrapy.Field()
    lng = scrapy.Field()
    lat = scrapy.Field()
    status = scrapy.Field()
    panoid = scrapy.Field()
    error_message = scrapy.Field()


class PanoItem(scrapy.Item):
    job_id = scrapy.Field()
    panoid = scrapy.Field()
    source_point_index = scrapy.Field()
    source_lng = scrapy.Field()
    source_lat = scrapy.Field()
    pano_lng = scrapy.Field()
    pano_lat = scrapy.Field()
    capture_date = scrapy.Field()
    provider = scrapy.Field()
    raw_json = scrapy.Field()


class CrawlErrorItem(scrapy.Item):
    job_id = scrapy.Field()
    stage = scrapy.Field()
    url = scrapy.Field()
    point_index = scrapy.Field()
    panoid = scrapy.Field()
    error_type = scrapy.Field()
    error_message = scrapy.Field()
    context_json = scrapy.Field()
