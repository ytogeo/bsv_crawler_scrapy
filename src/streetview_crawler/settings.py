import os

BOT_NAME = "streetview_crawler"

SPIDER_MODULES = ["streetview_crawler.spiders"]
NEWSPIDER_MODULE = "streetview_crawler.spiders"

ROBOTSTXT_OBEY = False
LOG_LEVEL = os.getenv("SCRAPY_LOG_LEVEL", "INFO")

CONCURRENT_REQUESTS = int(os.getenv("SCRAPY_CONCURRENT_REQUESTS", "16"))
DOWNLOAD_TIMEOUT = int(os.getenv("SCRAPY_DOWNLOAD_TIMEOUT", "10"))

RETRY_ENABLED = True
RETRY_TIMES = int(os.getenv("SCRAPY_RETRY_TIMES", "3"))
RETRY_HTTP_CODES = [408, 429, 500, 502, 503, 504]

ITEM_PIPELINES = {
    "streetview_crawler.pipelines.StreetviewPipeline": 300,
}

MYSQL_HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "root")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "streetview")

REDIS_HOST = os.getenv("REDIS_HOST", "127.0.0.1")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))

