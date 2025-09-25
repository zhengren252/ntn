# 信息源爬虫模组 (Info Crawler Module)
# 严格按照模组二：核心设计理念和全局规范

__version__ = "1.1.0"
__author__ = "NeuroTrade Nexus Team"
__description__ = "信息源爬虫模组 - 系统情报搜集员"

# 模组标识
MODULE_ID = "info-crawler-module"
MODULE_VERSION = "1.1"

# ZeroMQ主题命名规范: [模组来源].[类别].[具体内容]
ZMQ_TOPICS = {
    "NEWS_PUBLISH": "crawler.news",
    "STATUS_REPORT": "crawler.status",
    "ERROR_ALERT": "crawler.error",
}

# 数据结构版本
SCHEMA_VERSION = "1.1"
