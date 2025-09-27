# -*- coding: utf-8 -*-
"""
API路由模块

提供核心API端点，包含爬虫管理、数据查询等功能
"""

import os
import time
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

from flask import Blueprint, request, jsonify, current_app, g
from werkzeug.exceptions import BadRequest, NotFound, Conflict

from .middleware import (
    require_auth,
    require_admin,
    validate_json,
    handle_errors,
    cache_response,
)
from ..crawlers.scrapy_crawler import ScrapyCrawler
from ..crawlers.telegram_crawler import TelegramCrawler
from ..processors.pipeline import DataPipeline
from ..zmq_client import ZMQPublisher

# 创建蓝图
api_bp = Blueprint("api", __name__)

# 全局爬虫实例存储
crawler_instances = {}
data_pipeline = None
zmq_client = None


def get_or_create_crawler(crawler_type: str, crawler_id: str = None):
    """获取或创建爬虫实例

    Args:
        crawler_type: 爬虫类型 (scrapy/telegram)
        crawler_id: 爬虫ID

    Returns:
        爬虫实例
    """

    if crawler_id is None:
        crawler_id = f"{crawler_type}_default"

    instance_key = f"{crawler_type}_{crawler_id}"

    if instance_key not in crawler_instances:
        config = current_app.config_manager
        logger = current_app.logger_instance

        if crawler_type == "scrapy":
            crawler_instances[instance_key] = ScrapyCrawler(config, logger)
        elif crawler_type == "telegram":
            crawler_instances[instance_key] = TelegramCrawler(config, logger)
        else:
            raise ValueError(f"Unsupported crawler type: {crawler_type}")

    return crawler_instances[instance_key]


def get_data_pipeline():
    """获取数据处理管道实例"""
    global data_pipeline

    if data_pipeline is None:
        config = current_app.config_manager
        logger = current_app.logger_instance
        data_pipeline = DataPipeline(config, logger)

    return data_pipeline


def get_zmq_client():
    """获取ZMQ客户端实例"""
    global zmq_client

    if zmq_client is None:
        config = current_app.config_manager
        logger = current_app.logger_instance
        zmq_client = ZMQPublisher(config, logger)

    return zmq_client


def _safe_health_check(crawler):
    """安全地执行健康检查，确保返回值可以JSON序列化"""
    try:
        if hasattr(crawler, "health_check"):
            health_result = crawler.health_check()
            # 确保结果可以JSON序列化
            if isinstance(health_result, dict):
                return health_result
            else:
                return {"status": "unknown", "error": "Invalid health check result"}
        else:
            return {"status": "unknown"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@api_bp.route("/status", methods=["GET"])
@handle_errors
@cache_response(60)
def get_status():
    """获取API状态"""
    config = current_app.config_manager

    return jsonify(
        {
            "status": "running",
            "timestamp": datetime.utcnow().isoformat(),
            "version": config.get_config("app.version", "1.0.0"),
            "environment": config.environment,
            "uptime": time.time() - current_app.start_time,
            "active_crawlers": len(crawler_instances),
            "components": {
                "data_pipeline": data_pipeline is not None,
                "zmq_client": zmq_client is not None,
            },
        }
    )


@api_bp.route("/crawlers", methods=["GET"])
@require_auth
@handle_errors
def list_crawlers():
    """列出所有爬虫实例"""
    crawlers = []

    for instance_key, crawler in crawler_instances.items():
        crawler_type, crawler_id = instance_key.split("_", 1)

        crawlers.append(
            {
                "id": crawler_id,
                "type": crawler_type,
                "status": "running"
                if getattr(crawler, "is_running", False)
                else "stopped",
                "stats": crawler.get_stats() if hasattr(crawler, "get_stats") else {},
                "health": _safe_health_check(crawler),
            }
        )

    return jsonify({"crawlers": crawlers, "total": len(crawlers)})


@api_bp.route("/crawlers/<crawler_type>", methods=["POST"])
@require_auth
@validate_json(required_fields=["config"])
@handle_errors
def create_crawler(crawler_type: str):
    """创建新的爬虫实例"""
    data = g.json_data
    crawler_id = data.get("id", f"{crawler_type}_{int(time.time())}")
    crawler_config = data.get("config", {})

    # 检查爬虫类型
    if crawler_type not in ["scrapy", "telegram"]:
        raise BadRequest(f"Unsupported crawler type: {crawler_type}")

    # 检查是否已存在
    instance_key = f"{crawler_type}_{crawler_id}"
    if instance_key in crawler_instances:
        raise Conflict(f"Crawler {crawler_id} already exists")

    try:
        # 创建爬虫实例
        crawler = get_or_create_crawler(crawler_type, crawler_id)

        # 应用配置
        if hasattr(crawler, "update_config"):
            crawler.update_config(crawler_config)

        return (
            jsonify(
                {
                    "message": f"Crawler {crawler_id} created successfully",
                    "crawler": {
                        "id": crawler_id,
                        "type": crawler_type,
                        "status": "created",
                        "config": crawler_config,
                    },
                }
            ),
            201,
        )

    except Exception as e:
        # 清理失败的实例
        if instance_key in crawler_instances:
            del crawler_instances[instance_key]
        raise


@api_bp.route("/crawlers/<crawler_type>/<crawler_id>", methods=["GET"])
@require_auth
@handle_errors
def get_crawler(crawler_type: str, crawler_id: str):
    """获取特定爬虫信息"""
    instance_key = f"{crawler_type}_{crawler_id}"

    if instance_key not in crawler_instances:
        raise NotFound(f"Crawler {crawler_id} not found")

    crawler = crawler_instances[instance_key]

    # 获取配置信息，确保可以JSON序列化
    crawler_config = getattr(crawler, "config", {})
    if hasattr(crawler_config, "to_dict"):
        crawler_config = crawler_config.to_dict()
    elif not isinstance(crawler_config, dict):
        crawler_config = {}

    return jsonify(
        {
            "id": crawler_id,
            "type": crawler_type,
            "status": "running" if getattr(crawler, "is_running", False) else "stopped",
            "stats": crawler.get_stats() if hasattr(crawler, "get_stats") else {},
            "health": _safe_health_check(crawler),
            "config": crawler_config,
        }
    )


@api_bp.route("/crawlers/<crawler_type>/<crawler_id>/start", methods=["POST"])
@require_auth
@handle_errors
def start_crawler(crawler_type: str, crawler_id: str):
    """启动爬虫"""
    instance_key = f"{crawler_type}_{crawler_id}"

    if instance_key not in crawler_instances:
        raise NotFound(f"Crawler {crawler_id} not found")

    crawler = crawler_instances[instance_key]

    # 检查是否已在运行
    if getattr(crawler, "is_running", False):
        return jsonify({"message": f"Crawler {crawler_id} is already running"})

    try:
        # 启动爬虫
        if hasattr(crawler, "start"):
            if asyncio.iscoroutinefunction(crawler.start):
                # 异步启动
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(crawler.start())
            else:
                # 同步启动
                crawler.start()

        return jsonify(
            {
                "message": f"Crawler {crawler_id} started successfully",
                "status": "running",
            }
        )

    except Exception as e:
        current_app.logger_instance.error(f"Failed to start crawler {crawler_id}: {e}")
        return (
            jsonify({"error": {"message": f"Failed to start crawler: {str(e)}"}}),
            500,
        )


@api_bp.route("/crawlers/<crawler_type>/<crawler_id>/stop", methods=["POST"])
@require_auth
@handle_errors
def stop_crawler(crawler_type: str, crawler_id: str):
    """停止爬虫"""
    instance_key = f"{crawler_type}_{crawler_id}"

    if instance_key not in crawler_instances:
        raise NotFound(f"Crawler {crawler_id} not found")

    crawler = crawler_instances[instance_key]

    # 检查是否已停止
    if not getattr(crawler, "is_running", False):
        return jsonify({"message": f"Crawler {crawler_id} is already stopped"})

    try:
        # 停止爬虫
        if hasattr(crawler, "stop"):
            if asyncio.iscoroutinefunction(crawler.stop):
                # 异步停止
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(crawler.stop())
            else:
                # 同步停止
                crawler.stop()

        return jsonify(
            {
                "message": f"Crawler {crawler_id} stopped successfully",
                "status": "stopped",
            }
        )

    except Exception as e:
        current_app.logger_instance.error(f"Failed to stop crawler {crawler_id}: {e}")
        return jsonify({"error": {"message": f"Failed to stop crawler: {str(e)}"}}), 500


@api_bp.route("/crawlers/<crawler_type>/<crawler_id>", methods=["DELETE"])
@require_admin
@handle_errors
def delete_crawler(crawler_type: str, crawler_id: str):
    """删除爬虫实例"""
    instance_key = f"{crawler_type}_{crawler_id}"

    if instance_key not in crawler_instances:
        raise NotFound(f"Crawler {crawler_id} not found")

    crawler = crawler_instances[instance_key]

    try:
        # 先停止爬虫
        if getattr(crawler, "is_running", False):
            if hasattr(crawler, "stop"):
                if asyncio.iscoroutinefunction(crawler.stop):
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(crawler.stop())
                else:
                    crawler.stop()

        # 清理资源
        if hasattr(crawler, "cleanup"):
            crawler.cleanup()

        # 删除实例
        del crawler_instances[instance_key]

        return jsonify({"message": f"Crawler {crawler_id} deleted successfully"})

    except Exception as e:
        current_app.logger_instance.error(f"Failed to delete crawler {crawler_id}: {e}")
        return (
            jsonify({"error": {"message": f"Failed to delete crawler: {str(e)}"}}),
            500,
        )


@api_bp.route("/data/process", methods=["POST"])
@require_auth
@validate_json(required_fields=["data"])
@handle_errors
def process_data():
    """处理数据"""
    data = g.json_data
    input_data = data.get("data")
    processing_config = data.get("config", {})

    try:
        # 获取数据处理管道
        pipeline = get_data_pipeline()

        # 处理数据
        if isinstance(input_data, list):
            # 批量处理
            result = pipeline.process_batch(input_data)

            return jsonify(
                {
                    "success": True,
                    "result": {
                        "total_items": result.total_items,
                        "successful_items": result.successful_items,
                        "failed_items": result.failed_items,
                        "processing_time": result.processing_time,
                        "results": [
                            {
                                "success": r.success,
                                "data": r.data,
                                "errors": r.errors,
                                "warnings": r.warnings,
                            }
                            for r in result.results
                        ],
                    },
                }
            )
        else:
            # 单项处理
            result = pipeline.process_item(input_data)

            return jsonify(
                {
                    "success": result.success,
                    "data": result.data,
                    "errors": result.errors,
                    "warnings": result.warnings,
                    "processing_time": result.processing_time,
                    "stages_completed": [
                        stage.value for stage in result.stages_completed
                    ],
                }
            )

    except Exception as e:
        current_app.logger_instance.error(f"Data processing failed: {e}")
        return jsonify({"error": {"message": f"Data processing failed: {str(e)}"}}), 500


@api_bp.route("/data/publish", methods=["POST"])
@require_auth
@validate_json(required_fields=["topic", "data"])
@handle_errors
def publish_data():
    """发布数据到ZMQ"""
    data = g.json_data
    orig_topic = data.get("topic")
    message_data = data.get("data")
    topic = "crawler.news"
    if orig_topic and orig_topic != topic:
        current_app.logger_instance.warning(
            f"Incoming topic '{orig_topic}' ignored; using fixed topic '{topic}'"
        )

    try:
        # 获取ZMQ客户端
        client = get_zmq_client()

        # 发布消息
        success = client.publish(topic, message_data)

        if success:
            return jsonify(
                {"success": True, "message": f"Data published to topic {topic}"}
            )
        else:
            return jsonify({"error": {"message": "Failed to publish data"}}), 500

    except Exception as e:
        current_app.logger_instance.error(f"Data publishing failed: {e}")
        return jsonify({"error": {"message": f"Data publishing failed: {str(e)}"}}), 500


@api_bp.route("/stats", methods=["GET"])
@require_auth
@handle_errors
@cache_response(30)
def get_stats():
    """获取系统统计信息"""
    stats = {
        "timestamp": datetime.utcnow().isoformat(),
        "uptime": time.time() - current_app.start_time,
        "crawlers": {
            "total": len(crawler_instances),
            "running": sum(
                1 for c in crawler_instances.values() if getattr(c, "is_running", False)
            ),
            "instances": {},
        },
        "api": {
            "requests": current_app.request_logger.get_stats(),
            "rate_limit": current_app.rate_limiter.get_stats(),
        },
    }

    # 收集爬虫统计
    for instance_key, crawler in crawler_instances.items():
        if hasattr(crawler, "get_stats"):
            stats["crawlers"]["instances"][instance_key] = crawler.get_stats()

    # 数据处理管道统计
    if data_pipeline:
        stats["data_pipeline"] = data_pipeline.get_stats()

    # ZMQ客户端统计
    if zmq_client:
        stats["zmq_client"] = zmq_client.get_stats()

    return jsonify(stats)


@api_bp.route("/logs", methods=["GET"])
@require_admin
@handle_errors
def get_logs():
    """获取日志信息"""
    # 获取查询参数
    level = request.args.get("level", "INFO")
    limit = min(int(request.args.get("limit", 100)), 1000)  # 最多1000条
    since = request.args.get("since")  # ISO格式时间

    try:
        # 这里应该从日志文件或日志系统中读取日志
        # 为了演示，返回模拟数据
        logs = [
            {
                "timestamp": datetime.utcnow().isoformat(),
                "level": "INFO",
                "message": "API server started",
                "module": "api.app",
            },
            {
                "timestamp": (datetime.utcnow() - timedelta(minutes=1)).isoformat(),
                "level": "DEBUG",
                "message": "Crawler status check completed",
                "module": "crawlers.base",
            },
        ]

        return jsonify(
            {"logs": logs[:limit], "total": len(logs), "level": level, "limit": limit}
        )

    except Exception as e:
        current_app.logger_instance.error(f"Failed to retrieve logs: {e}")
        return (
            jsonify({"error": {"message": f"Failed to retrieve logs: {str(e)}"}}),
            500,
        )


@api_bp.route("/system/info", methods=["GET"])
@require_auth
@handle_errors
@cache_response(300)  # 5分钟缓存
def get_system_info():
    """获取系统信息"""
    import psutil
    import platform

    try:
        # 系统信息
        system_info = {
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "cpu_count": psutil.cpu_count(),
            "memory": {
                "total": psutil.virtual_memory().total,
                "available": psutil.virtual_memory().available,
                "percent": psutil.virtual_memory().percent,
            },
            "disk": {
                "total": psutil.disk_usage("/").total,
                "free": psutil.disk_usage("/").free,
                "percent": psutil.disk_usage("/").percent,
            },
            "network": {
                "bytes_sent": psutil.net_io_counters().bytes_sent,
                "bytes_recv": psutil.net_io_counters().bytes_recv,
            },
        }

        return jsonify(
            {
                "system": system_info,
                "process": {
                    "pid": os.getpid(),
                    "memory_percent": psutil.Process().memory_percent(),
                    "cpu_percent": psutil.Process().cpu_percent(),
                    "create_time": psutil.Process().create_time(),
                },
            }
        )

    except Exception as e:
        current_app.logger_instance.error(f"Failed to get system info: {e}")
        return (
            jsonify({"error": {"message": f"Failed to get system info: {str(e)}"}}),
            500,
        )


if __name__ == "__main__":
    # 测试路由功能
    from flask import Flask
    from ..config import ConfigManager
    from ..utils import Logger

    # 创建测试应用
    app = Flask(__name__)
    app.config_manager = ConfigManager("development")
    app.logger_instance = Logger(app.config_manager)
    app.start_time = time.time()

    # 注册蓝图
    app.register_blueprint(api_bp, url_prefix="/api/v1")

    print("API路由注册完成")
    print("可用端点:")

    for rule in app.url_map.iter_rules():
        print(f"  {rule.methods} {rule.rule}")
