"""
Scrapy 项目配置模块。

该模块负责配置 Scrapy 运行时行为和项目级集成，包括：
- spider 模块发现路径
- 请求并发数、下载超时和重试策略
- 启用的 Item Pipeline
- 从环境变量读取 MySQL 和 Redis 连接参数

AOI 路径、采样间隔、输出目录、pano worker 数量等任务级业务参数
放在 YAML 配置文件中，不放在 Scrapy settings 中。
"""

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
