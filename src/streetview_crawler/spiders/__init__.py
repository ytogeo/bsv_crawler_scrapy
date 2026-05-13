"""
Scrapy spider 包。

Spider 模块负责生成 Request、解析 Response 和处理请求失败。Spider 应该
yield Item 或新的 Request；数据库写入和 Redis 派发交给 Pipeline 和服务层。
"""
