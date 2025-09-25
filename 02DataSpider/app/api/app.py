# -*- coding: utf-8 -*-
"""
Flask应用主文件

实现应用工厂模式，提供API服务和监控面板
"""

import os
import sys
import time
from datetime import datetime

# 添加依赖库路径（优先读取环境变量 YILAI_DIR，其次回退到 D:\\YiLai；仅在目录存在且未加入 sys.path 时插入）
YILAI_DIR = os.getenv("YILAI_DIR", r"D:\\YiLai")
pydeps_path = os.path.join(YILAI_DIR, "pydeps")
if os.path.isdir(pydeps_path) and pydeps_path not in sys.path:
    sys.path.insert(0, pydeps_path)
from flask import Flask, request, g
from flask_cors import CORS
from werkzeug.exceptions import HTTPException

from ..config import ConfigManager
from ..utils import Logger
from .middleware import setup_middleware
from .routes import api_bp
from .auth import auth_bp
from .monitoring import monitoring_bp
from .config import config_bp


def create_app(environment: str = None) -> Flask:
    """创建Flask应用

    Args:
        environment: 环境名称 (development/staging/production)

    Returns:
        Flask应用实例
    """
    # 确定环境
    if environment is None:
        environment = os.getenv("FLASK_ENV", "development")

    # 初始化配置和日志
    config = ConfigManager(environment)
    logger = Logger(config)

    # 创建Flask应用
    app = Flask(__name__)

    # 基础配置
    app.config.update(
        {
            "SECRET_KEY": config.get_config("api.secret_key", "dev-secret-key"),
            "DEBUG": environment == "development",
            "TESTING": environment == "testing",
            "JSON_AS_ASCII": False,
            "JSONIFY_PRETTYPRINT_REGULAR": True,
            "MAX_CONTENT_LENGTH": config.get_config(
                "api.max_content_length", 16 * 1024 * 1024
            ),  # 16MB
            "SEND_FILE_MAX_AGE_DEFAULT": config.get_config("api.cache_timeout", 3600),
        }
    )

    # CORS配置
    cors_config = config.get_config("api.cors", {})
    CORS(
        app,
        origins=cors_config.get("origins", ["http://localhost:3000"]),
        methods=cors_config.get("methods", ["GET", "POST", "PUT", "DELETE", "OPTIONS"]),
        allow_headers=cors_config.get("headers", ["Content-Type", "Authorization"]),
    )

    # 存储配置和日志到应用上下文
    app.config_manager = config
    app.logger_instance = logger

    # 设置中间件
    setup_middleware(app)

    # 注册蓝图
    app.register_blueprint(api_bp, url_prefix="/api/v1")
    app.register_blueprint(auth_bp, url_prefix="/api/v1/auth")
    app.register_blueprint(monitoring_bp, url_prefix="/api/v1/monitoring")
    app.register_blueprint(config_bp, url_prefix="/api/v1/config")

    # 请求前处理
    @app.before_request
    def before_request():
        """请求前处理"""
        g.start_time = time.time()
        g.request_id = f"{int(time.time() * 1000)}-{os.getpid()}"

        # 记录请求日志
        logger.info(
            f"请求开始: {request.method} {request.path} | "
            f"IP: {request.remote_addr} | "
            f"User-Agent: {request.headers.get('User-Agent', 'Unknown')} | "
            f"Request-ID: {g.request_id}"
        )

    # 请求后处理
    @app.after_request
    def after_request(response):
        """请求后处理"""
        if hasattr(g, "start_time"):
            duration = time.time() - g.start_time

            # 记录响应日志
            logger.info(
                f"请求完成: {request.method} {request.path} | "
                f"状态: {response.status_code} | "
                f"耗时: {duration:.3f}s | "
                f"Request-ID: {getattr(g, 'request_id', 'unknown')}"
            )

            # 添加响应头
            response.headers["X-Request-ID"] = getattr(g, "request_id", "unknown")
            response.headers["X-Response-Time"] = f"{duration:.3f}s"

        return response

    # 错误处理
    @app.errorhandler(HTTPException)
    def handle_http_exception(e):
        """处理HTTP异常"""
        import json
        from flask import Response

        logger.warning(
            f"HTTP异常: {e.code} {e.name} | "
            f"路径: {request.path} | "
            f"描述: {e.description}"
        )

        error_data = {
            "error": {
                "code": e.code,
                "name": e.name,
                "description": e.description,
                "timestamp": datetime.now().isoformat(),
                "request_id": getattr(g, "request_id", "unknown"),
            }
        }

        return Response(
            json.dumps(error_data), mimetype="application/json", status=e.code
        )

    @app.errorhandler(Exception)
    def handle_exception(e):
        """处理通用异常"""
        import json
        from flask import Response

        logger.error(
            f"服务器异常: {type(e).__name__}: {str(e)} | "
            f"路径: {request.path} | "
            f"Request-ID: {getattr(g, 'request_id', 'unknown')}",
            exc_info=True,
        )

        error_data = {
            "error": {
                "code": 500,
                "name": "Internal Server Error",
                "description": "An internal server error occurred",
                "timestamp": datetime.now().isoformat(),
                "request_id": getattr(g, "request_id", "unknown"),
            }
        }

        return Response(json.dumps(error_data), mimetype="application/json", status=500)

    # 健康检查端点
    @app.route("/health")
    def health_check():
        """健康检查端点"""
        import json
        from flask import Response

        try:
            request_id = getattr(g, "request_id", "unknown")
            health_data = {
                "success": True,
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "request_id": request_id,
                "environment": environment or os.getenv("ENV", "production"),
                "version": "1.0.0",
                "uptime": round(time.time() - getattr(app, "start_time", time.time()), 3),
            }
            return Response(
                json.dumps(health_data), mimetype="application/json", status=200
            )
        except Exception as e:
            request_id = getattr(g, "request_id", "unknown")
            error_data = {
                "success": False,
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "request_id": request_id,
            }
            return Response(
                json.dumps(error_data), mimetype="application/json", status=500
            )

    # 轻量级存活探针
    @app.route("/live")
    def live_probe():
        """存活性探针：快速返回运行状态，无依赖检查"""
        import json
        from flask import Response

        payload = {
            "status": "alive",
            "timestamp": datetime.now().isoformat(),
            "module": "模组02: DataSpider",
            "version": "1.0.0",
        }
        return Response(json.dumps(payload), mimetype="application/json", status=200)

    # 根路径
    @app.route("/")
    def index():
        """根路径"""
        import json
        from flask import Response

        try:
            index_data = {
                "name": "NeuroTrade Nexus - Data Spider API",
                "version": "1.0.0",
                "environment": environment or os.getenv("ENV", "production"),
                "timestamp": datetime.now().isoformat(),
                "endpoints": {
                    "health": "/health",
                    "live": "/live",
                    "api": "/api/v1",
                    "monitoring": "/api/v1/monitoring",
                    "config": "/api/v1/config",
                    "auth": "/api/v1/auth",
                },
            }
            return Response(
                json.dumps(index_data), mimetype="application/json", status=200
            )
        except Exception as e:
            error_data = {
                "name": "NeuroTrade Nexus - Data Spider API",
                "version": "1.0.0",
                "environment": environment or os.getenv("ENV", "production"),
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
                "endpoints": {
                    "health": "/health",
                    "live": "/live",
                    "api": "/api/v1",
                    "monitoring": "/api/v1/monitoring",
                    "config": "/api/v1/config",
                    "auth": "/api/v1/auth",
                },
            }
            return Response(
                json.dumps(error_data), mimetype="application/json", status=500
            )

    # 记录应用启动时间
    app.start_time = time.time()

    # 确保environment是字符串
    env_str = str(environment) if environment else "production"
    logger.info(f"Flask应用创建完成: 环境={env_str} | 调试模式={app.config['DEBUG']}")

    return app


def run_app(host: str = "0.0.0.0", port: int = 5000, environment: str = None):
    """运行Flask应用

    Args:
        host: 主机地址
        port: 端口号
        environment: 环境名称
    """
    app = create_app(environment)

    # 获取配置
    config = app.config_manager
    logger = app.logger_instance

    # 服务器配置
    server_config = config.get_config("api.server", {})
    host = server_config.get("host", host)
    port = server_config.get("port", port)
    debug = app.config["DEBUG"]

    logger.info(f"启动Flask服务器: http://{host}:{port} | 调试模式={debug}")

    try:
        app.run(host=host, port=port, debug=debug, threaded=True, use_reloader=debug)
    except KeyboardInterrupt:
        logger.info("Flask服务器已停止")
    except Exception as e:
        logger.error(f"Flask服务器启动失败: {e}")
        raise


if __name__ == "__main__":
    import sys

    # 从命令行参数获取环境
    environment = sys.argv[1] if len(sys.argv) > 1 else "development"

    # 运行应用
    run_app(environment=environment)
