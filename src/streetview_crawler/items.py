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

