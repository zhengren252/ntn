#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NeuroTrade Nexus (NTN) - 淇℃伅婧愮埇铏ā缁勪富鍏ュ彛
妯＄粍浜岋細Info Crawler Module

鍚姩鏂瑰紡锛?
  python main.py --env development
  python main.py --env staging  
  python main.py --env production
"""

import sys
import os
import argparse
from pathlib import Path

# 添加依赖库路径（优先读取环境变量 YILAI_DIR，其次回退到 D:\\YiLai；仅在目录存在且未加入 sys.path 时插入）
YILAI_DIR = os.getenv("YILAI_DIR", r"D:\\YiLai")
pydeps_path = os.path.join(YILAI_DIR, "pydeps")
if os.path.isdir(pydeps_path) and pydeps_path not in sys.path:
    sys.path.insert(0, pydeps_path)

# 娣诲姞椤圭洰璺緞
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.config import ConfigManager
from app.utils import Logger
from app.api import create_app
from app.crawlers import ScrapyCrawler, TelegramCrawler
from app.zmq_client import ZMQPublisher


def parse_arguments():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(description="NeuroTrade Nexus Info Crawler")
    parser.add_argument(
        "--env",
        choices=["development", "staging", "production"],
        default="development",
        help="杩愯鐜 (榛樿: development)",
    )
    parser.add_argument(
        "--mode",
        choices=["crawler", "api", "all"],
        default="all",
        help="杩愯妯″紡 (榛樿: all)",
    )
    parser.add_argument("--debug", action="store_true", help="鍚敤璋冭瘯妯″紡")
    return parser.parse_args()


def setup_environment(env: str):
    """Set environment variables for runtime"""
    os.environ["NTN_ENV"] = env
    os.environ["APP_ENV"] = env
    
    # 璁剧疆鏃ュ織绾у埆
    if env == "development":
        os.environ["LOG_LEVEL"] = "DEBUG"
    else:
        os.environ["LOG_LEVEL"] = "INFO"


def start_crawler_service(config, logger):
    """Start the crawler services and ZMQ publisher"""
    logger.info("启动爬虫服务...")
    
    try:
        # 鍒濆鍖朲MQ鍙戝竷鑰?
        zmq_publisher = ZMQPublisher(config, logger=logger)
        
        # 鍚姩Scrapy鐖櫕
        # FIX: pass correct parameters; do NOT pass publisher as logger
        scrapy_crawler = ScrapyCrawler(config, logger=logger, publisher=zmq_publisher)
        scrapy_crawler.start_crawling()
        
        # 读取 Telegram 开关，默认关闭以便在生产环境缺少凭证时能启动
        telegram_enabled = config.get("telegram.enabled", False)
        if isinstance(telegram_enabled, str):
            telegram_enabled = telegram_enabled.strip().lower() in ("1", "true", "yes", "on")
        if telegram_enabled:
            # 鍚姩Telegram鐖櫕
            telegram_crawler = TelegramCrawler(config, logger=logger, publisher=zmq_publisher)
            telegram_crawler.start_crawling()
            logger.info("Telegram 爬虫已启用并启动")
        else:
            logger.warning("检测到 telegram.enabled = false，跳过 Telegram 爬虫启动")
        
        logger.info("鐖櫕鏈嶅姟鍚姩鎴愬姛")
        
        # 淇濇寔鏈嶅姟杩愯
        import time
        while True:
            time.sleep(1)
            
    except Exception as e:
        logger.error(f"鐖櫕鏈嶅姟鍚姩澶辫触: {e}")
        raise


# --- FIX: Use Flask server and pass environment string to create_app ---
def start_api_service(env: str, config, logger):
    """Start the Flask API service"""
    logger.info("启动API服务...")
    
    try:
        # 传入正确的环境字符串，避免将 ConfigManager 误作环境对象
        app = create_app(env)
        
        # 使用 Flask 内置服务器以确保与 Flask 应用兼容；端口来自配置
        debug_enabled = (os.getenv("LOG_LEVEL", "INFO").upper() == "DEBUG")
        app.run(
            host="0.0.0.0",
            port=config.get("api.port", 5000),
            debug=debug_enabled,
        )
        
    except Exception as e:
        logger.error(f"API鏈嶅姟鍚姩澶辫触: {e}")
        raise


def main():
    """Main function"""
    args = parse_arguments()
    
    # 璁剧疆鐜
    setup_environment(args.env)
    
    # 鍒濆鍖栭厤缃?
    config = ConfigManager(args.env)
    
    # 鍒濆鍖栨棩蹇?
    logger = Logger(config).get_logger()
    
    logger.info(f"NeuroTrade Nexus 淇℃伅婧愮埇铏ā缁勫惎鍔?- 鐜: {args.env}, 妯″紡: {args.mode}")
    
    try:
        if args.mode == "crawler":
            start_crawler_service(config, logger)
        elif args.mode == "api":
            # 传入环境字符串
            start_api_service(args.env, config, logger)
        elif args.mode == "all":
            # 鍦ㄧ敓浜х幆澧冧腑锛岄€氬父浣跨敤杩涚▼绠＄悊鍣ㄦ潵鍒嗗埆鍚姩涓嶅悓鏈嶅姟
            # 杩欓噷涓轰简绠€鍖栵紝浣跨敤澶氱嚎绋?
            import threading
            
            # 鍚姩鐖櫕鏈嶅姟绾跨▼
            crawler_thread = threading.Thread(
                target=start_crawler_service, args=(config, logger)
            )
            crawler_thread.daemon = True
            crawler_thread.start()
            
            # 鍚姩API鏈嶅姟锛堜富绾跨▼锛?
            start_api_service(args.env, config, logger)
            
    except KeyboardInterrupt:
        logger.info("鏀跺埌鍋滄淇″彿锛屾鍦ㄥ叧闂湇鍔?..")
    except Exception as e:
        logger.error(f"鏈嶅姟杩愯寮傚父: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
