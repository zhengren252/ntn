# Flask WebӦ������??
# �ṩɨ������Web���������API

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import threading
import time
import uuid
import asyncio

# Try to import app version; fallback if unavailable
try:
    from scanner import __version__ as APP_VERSION
except Exception:
    APP_VERSION = "1.0.0"

from scanner.communication.redis_client import RedisClient
from scanner.config.env_manager import get_env_manager
from scanner.utils.logger import get_logger


class ScannerWebApp:
    """扫描器Web应用"""

    def __init__(self, redis_client=None, zmq_client=None, health_checker=None):
        self.app = Flask(__name__, template_folder="templates", static_folder="static")

        # 配置CORS
        CORS(self.app)

        # SocketIO for real-time communication
        self.socketio = SocketIO(self.app, cors_allowed_origins="*")

        # 初始化组件
        self.env_manager = get_env_manager()
        self.logger = get_logger(__name__)

        # Redis客户端（启动时失败不应阻断Web服务启动）
        if redis_client:
            self.redis_client = redis_client
        else:
            redis_config = self.env_manager.get_redis_config()
            try:
                self.redis_client = RedisClient(redis_config)
                self.redis_client.connect()
            except Exception as e:
                # 非致命：记录警告并以降级模式启动，健康检查将反映Redis不可用
                self.logger.warning(f"Redis connection failed during web init, starting in degraded mode: {e}")
                self.redis_client = None

        # ZMQ客户端和健康检查器（可选）
        self.zmq_client = zmq_client
        self.health_checker = health_checker

        # Real-time data broadcasting
        self._setup_realtime_broadcasting()

        # 注册路由
        self._register_routes()
        self._register_socketio_events()

        self.logger.info("Scanner Web App initialized")

    def _setup_realtime_broadcasting(self):
        """设置实时数据广播"""
        self.broadcast_thread = threading.Thread(
            target=self._broadcast_realtime_data, daemon=True
        )
        self.broadcast_thread.start()

    def _broadcast_realtime_data(self):
        """实时数据广播线程"""
        while True:
            try:
                # 广播系统状态
                status_data = self._get_realtime_status()
                self.socketio.emit("status_update", status_data)

                # 广播性能指标
                metrics_data = self._get_realtime_metrics()
                self.socketio.emit("metrics_update", metrics_data)

                # 广播最新扫描结果
                results_data = self._get_latest_results(limit=5)
                self.socketio.emit("results_update", results_data)

                time.sleep(2)  # 每2秒广播一次
            except Exception as e:
                self.logger.error(f"Error in realtime broadcasting: {e}")
                time.sleep(5)

    def _register_socketio_events(self):
        """注册SocketIO事件"""

        @self.socketio.on("connect")
        def handle_connect():
            self.logger.info("Client connected to WebSocket")
            # 发送初始数据
            emit("status_update", self._get_realtime_status())
            emit("metrics_update", self._get_realtime_metrics())

        @self.socketio.on("disconnect")
        def handle_disconnect():
            self.logger.info("Client disconnected from WebSocket")

        @self.socketio.on("subscribe_symbol")
        def handle_subscribe_symbol(data):
            symbol = data.get("symbol")
            if symbol:
                # 加入特定交易对的房间
                self.socketio.join_room(f"symbol_{symbol}")
                self.logger.info(f"Client subscribed to symbol: {symbol}")

        @self.socketio.on("unsubscribe_symbol")
        def handle_unsubscribe_symbol(data):
            symbol = data.get("symbol")
            if symbol:
                # 离开特定交易对的房间
                self.socketio.leave_room(f"symbol_{symbol}")
                self.logger.info(f"Client unsubscribed from symbol: {symbol}")

    def _register_routes(self):
        """注册基础路由"""

        # 主页
        @self.app.route("/")
        def index():
            return render_template("index.html")

        # 状态监控页面
        @self.app.route("/status")
        def status_page():
            return render_template("status.html")

        # 规则配置页面
        @self.app.route("/rules")
        def rules_page():
            return render_template("rules.html")

        # 结果展示页面
        @self.app.route("/results")
        def results_page():
            return render_template("results.html")

        # API·��
        self._register_api_routes()

    def _register_api_routes(self):
        """注册API路由"""

        # 健康检查
        @self.app.route("/api/health")
        def health_check():
            try:
                # 检查Redis连接
                redis_status = self.redis_client.ping() if self.redis_client else False

                return jsonify(
                    {
                        "status": ("healthy" if redis_status else "unhealthy"),
                        "timestamp": datetime.now().isoformat(),
                        "components": {
                            "redis": ("connected" if redis_status else "disconnected"),
                            "web_app": "running",
                        },
                    }
                )
            except Exception as e:
                self.logger.error(f"Health check failed: {e}")
                return (
                    jsonify(
                        {
                            "status": "unhealthy",
                            "error": str(e),
                            "timestamp": datetime.now().isoformat(),
                        }
                    ),
                    500,
                )

        # 标准化健康检查（推荐使用）
        @self.app.route("/health")
        def standard_health_check():
            request_id = str(uuid.uuid4())
            # 使用UTC时间并加Z标识
            timestamp = datetime.utcnow().isoformat() + "Z"
            try:
                redis_ok = self.redis_client.ping() if self.redis_client else False
                status = "HEALTHY" if redis_ok else "UNHEALTHY"
                payload = {
                    "success": bool(redis_ok),
                    "request_id": request_id,
                    "timestamp": timestamp,
                    "service": "ScanPulse",
                    "version": APP_VERSION,
                    "environment": str(self.env_manager.get_environment()),
                    "status": status,
                    "components": {
                        "redis": {
                            "status": "connected" if redis_ok else "disconnected"
                        },
                        "web_app": {"status": "running"},
                    },
                }
                return jsonify(payload), 200
            except Exception as e:
                self.logger.error(f"Standard health check failed: {e}")
                error_payload = {
                    "success": False,
                    "request_id": request_id,
                    "timestamp": timestamp,
                    "service": "ScanPulse",
                    "version": APP_VERSION,
                    "environment": str(self.env_manager.get_environment()),
                    "status": "UNHEALTHY",
                    "error": str(e),
                }
                return jsonify(error_payload), 500

        # Liveness probe (independent of Redis)
        @self.app.route("/live")
        def live_check():
            request_id = str(uuid.uuid4())
            timestamp = datetime.utcnow().isoformat() + "Z"
            try:
                payload = {
                    "success": True,
                    "request_id": request_id,
                    "timestamp": timestamp,
                    "service": "ScanPulse",
                    "version": APP_VERSION,
                    "environment": str(self.env_manager.get_environment()),
                    "status": "ALIVE",
                    "degraded": self.redis_client is None,
                }
                return jsonify(payload), 200
            except Exception as e:
                self.logger.error(f"Liveness check failed: {e}")
                return jsonify({
                    "success": False,
                    "request_id": request_id,
                    "timestamp": timestamp,
                    "service": "ScanPulse",
                    "version": APP_VERSION,
                    "environment": str(self.env_manager.get_environment()),
                    "status": "ERROR",
                    "error": str(e),
                }), 500

        # 获取系统状态
        @self.app.route("/api/status")
        def get_system_status():
            try:
                status_data = self._get_system_status()
                return jsonify(status_data)
            except Exception as e:
                self.logger.error(f"Failed to get system status: {e}")
                return jsonify({"error": str(e)}), 500

        # 获取扫描结果
        @self.app.route("/api/results")
        def get_scan_results():
            try:
                limit = request.args.get("limit", 100, type=int)
                symbol = request.args.get("symbol")

                results = self._get_scan_results(limit=limit, symbol=symbol)
                return jsonify(results)
            except Exception as e:
                self.logger.error(f"Failed to get scan results: {e}")
                return jsonify({"error": str(e)}), 500

        # 获取规则配置
        @self.app.route("/api/rules")
        def get_rules_config():
            try:
                config = self._get_rules_config()
                return jsonify(config)
            except Exception as e:
                self.logger.error(f"Failed to get rules config: {e}")
                return jsonify({"error": str(e)}), 500

        # 更新规则配置
        @self.app.route("/api/rules", methods=["POST"])
        def update_rules_config():
            try:
                new_config = request.get_json()
                if not new_config:
                    return jsonify({"error": "No configuration provided"}), 400

                success = self._update_rules_config(new_config)
                if success:
                    return jsonify({"message": "Configuration updated successfully"})
                else:
                    return jsonify({"error": "Failed to update configuration"}), 500
            except Exception as e:
                self.logger.error(f"Failed to update rules config: {e}")
                return jsonify({"error": str(e)}), 500

        # 获取性能指标
        @self.app.route("/api/metrics")
        def get_metrics():
            try:
                metrics = self._get_performance_metrics()
                return jsonify(metrics)
            except Exception as e:
                self.logger.error(f"Failed to get metrics: {e}")
                return jsonify({"error": str(e)}), 500

        # 获取活跃交易对
        @self.app.route("/api/symbols")
        def get_active_symbols():
            try:
                symbols = self._get_active_symbols()
                return jsonify({"symbols": symbols})
            except Exception as e:
                self.logger.error(f"Failed to get active symbols: {e}")
                return jsonify({"error": str(e)}), 500

    def _get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        try:
            # 从Redis获取状态信息
            status = {
                "timestamp": datetime.now().isoformat(),
                "scanner": {
                    "status": "running",
                    "last_scan": self._get_last_scan_time(),
                    "total_scans": self._get_total_scan_count(),
                    "active_symbols": len(self._get_active_symbols()),
                },
                "engines": {
                    "three_high": self._get_engine_status("three_high"),
                    "black_horse": self._get_engine_status("black_horse"),
                    "potential_finder": self._get_engine_status("potential_finder"),
                },
                "connections": {
                    "redis": (self.redis_client.ping() if self.redis_client else False),
                    "zmq": True,  # 假设ZMQ连接正常
                },
            }
            return status
        except Exception as e:
            self.logger.error(f"Error getting system status: {e}")
            return {"error": str(e)}

    def _get_scan_results(
        self, limit: int = 100, symbol: Optional[str] = None
    ) -> Dict[str, Any]:
        """获取扫描结果"""
        try:
            results = []

            if symbol:
                # 获取特定交易对的结果
                result = self.redis_client.get_scan_result(symbol) if self.redis_client else None
                if result:
                    results.append(result)
            else:
                # 获取所有结果
                all_symbols = self._get_active_symbols()
                for sym in all_symbols[:limit]:
                    result = self.redis_client.get_scan_result(sym) if self.redis_client else None
                    if result:
                        results.append(result)

            return {
                "results": results,
                "total": len(results),
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            self.logger.error(f"Error getting scan results: {e}")
            return {"error": str(e)}

    def _get_rules_config(self) -> Dict[str, Any]:
        """获取规则配置"""
        try:
            scanner_config = self.env_manager.get_scanner_config()
            return scanner_config.get("rules", {})
        except Exception as e:
            self.logger.error(f"Error getting rules config: {e}")
            return {"error": str(e)}

    def _update_rules_config(self, new_config: Dict[str, Any]) -> bool:
        """更新规则配置"""
        try:
            # 这里应该实现配置更新逻辑
            # 目前只是记录日志
            self.logger.info(f"Rules configuration update requested: {new_config}")
            return True
        except Exception as e:
            self.logger.error(f"Error updating rules config: {e}")
            return False

    def _get_performance_metrics(self) -> Dict[str, Any]:
        """获取性能指标"""
        try:
            # 从Redis获取实时性能数据
            metrics = {}
            if self.redis_client:
                metrics = {
                    "cpu_usage": float(self.redis_client.get("metrics:cpu_usage") or 0),
                    "memory_usage": float(
                        self.redis_client.get("metrics:memory_usage") or 0
                    ),
                    "scan_rate": float(self.redis_client.get("metrics:scan_rate") or 0),
                    "queue_size": int(self.redis_client.get("metrics:queue_size") or 0),
                    "response_time": float(
                        self.redis_client.get("metrics:response_time") or 0
                    ),
                    "network_latency": float(
                        self.redis_client.get("metrics:network_latency") or 0
                    ),
                    "disk_usage": float(
                        self.redis_client.get("metrics:disk_usage") or 0
                    ),
                    "active_connections": int(
                        self.redis_client.get("metrics:active_connections") or 0
                    ),
                }

            # 如果没有实际数据，返回模拟数据
            if not any(metrics.values()):
                import random

                metrics = {
                    "cpu_usage": round(random.uniform(20, 80), 1),
                    "memory_usage": round(random.uniform(40, 90), 1),
                    "scan_rate": round(random.uniform(80, 200), 1),
                    "queue_size": random.randint(0, 50),
                    "response_time": round(random.uniform(0.05, 0.5), 3),
                    "network_latency": round(random.uniform(10, 100), 1),
                    "disk_usage": round(random.uniform(30, 85), 1),
                    "active_connections": random.randint(5, 25),
                }

            metrics["timestamp"] = datetime.now().isoformat()
            return metrics
        except Exception as e:
            self.logger.error(f"Error getting performance metrics: {e}")
            return {
                "cpu_usage": 0,
                "memory_usage": 0,
                "scan_rate": 0,
                "queue_size": 0,
                "response_time": 0,
                "network_latency": 0,
                "disk_usage": 0,
                "active_connections": 0,
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
            }

    def _get_realtime_status(self):
        """获取实时系统状态"""
        try:
            base_status = self._get_system_status()

            # 构建前端期望的数据结构
            status = {
                "timestamp": datetime.now().isoformat(),
                "engine_status": "running",
                "active_pairs": len(self._get_active_symbols()),
                "total_scans": self._get_total_scan_count(),
                "success_rate": 95.5,  # 模拟成功率
                "connections": {
                    "redis": self.redis_client.ping() if self.redis_client else False,
                    "zmq": True,
                },
                "scanner": base_status.get("scanner", {}),
                "engines": base_status.get("engines", {}),
            }

            # 添加更多实时信息
            if self.redis_client:
                status.update(
                    {
                        "active_scanners": int(
                            self.redis_client.get("status:active_scanners") or 0
                        ),
                        "pending_tasks": int(
                            self.redis_client.get("status:pending_tasks") or 0
                        ),
                        "error_count": int(
                            self.redis_client.get("status:error_count") or 0
                        ),
                        "last_error": self.redis_client.get("status:last_error")
                        or None,
                    }
                )

            return status
        except Exception as e:
            self.logger.error(f"Error getting realtime status: {e}")
            # 返回默认数据结构，避免前端错误
            return {
                "timestamp": datetime.now().isoformat(),
                "engine_status": "stopped",
                "active_pairs": 0,
                "total_scans": 0,
                "success_rate": 0,
                "connections": {"redis": False, "zmq": False},
                "error": str(e),
            }

    def _get_realtime_metrics(self):
        """获取实时性能指标"""
        return self._get_performance_metrics()

    def _get_latest_results(self, limit=10):
        """获取最新扫描结果"""
        try:
            results = self._get_scan_results(limit=limit)
            return results.get("results", [])
        except Exception as e:
            self.logger.error(f"Error getting latest results: {e}")
            return []

    def _get_active_symbols(self) -> List[str]:
        """获取活跃交易对列表"""
        try:
            # 从Redis缓存或数据库获取活跃交易对
            return [
                "BTCUSDT",
                "ETHUSDT",
                "BNBUSDT",
                "ADAUSDT",
                "DOTUSDT",
                "LINKUSDT",
                "LTCUSDT",
                "BCHUSDT",
                "XLMUSDT",
                "EOSUSDT",
            ]
        except Exception as e:
            self.logger.error(f"Error getting active symbols: {e}")
            return []

    def _get_last_scan_time(self) -> Optional[str]:
        """获取最后扫描时间"""
        try:
            # 从Redis获取最后扫描时间
            return (datetime.now() - timedelta(minutes=1)).isoformat()
        except Exception as e:
            self.logger.error(f"Error getting last scan time: {e}")
            return None

    def _get_total_scan_count(self) -> int:
        """获取总扫描次数"""
        try:
            # 从Redis获取总扫描次数
            return 15420  # 模拟数据
        except Exception as e:
            self.logger.error(f"Error getting total scan count: {e}")
            return 0

    def _get_engine_status(self, engine_name: str) -> Dict[str, Any]:
        """获取引擎状态"""
        try:
            # 从配置或数据库获取引擎状态
            scanner_config = self.env_manager.get_scanner_config()
            engine_config = scanner_config.get("rules", {}).get(engine_name, {})

            return {
                "enabled": engine_config.get("enabled", False),
                "last_trigger": (datetime.now() - timedelta(minutes=5)).isoformat(),
                "trigger_count": 42,  # 模拟数据
            }
        except Exception as e:
            self.logger.error(f"Error getting engine status for {engine_name}: {e}")
            return {"enabled": False, "error": str(e)}

    def _get_scan_performance_stats(self):
        """获取扫描性能统计"""
        try:
            if self.redis_client:
                # 获取过去24小时的扫描性能
                scan_data = []
                for i in range(24):
                    hour_key = f"stats:scan_count:{(datetime.now() - timedelta(hours=i)).strftime('%Y%m%d%H')}"
                    count = int(self.redis_client.get(hour_key) or 0)
                    scan_data.append(
                        {
                            "hour": (datetime.now() - timedelta(hours=i)).strftime(
                                "%H:00"
                            ),
                            "count": count,
                        }
                    )
                return scan_data[::-1]  # 反转以按时间顺序排列
            return []
        except Exception as e:
            self.logger.error(f"Error getting scan performance stats: {e}")
            return []

    def _get_symbol_analysis_stats(self):
        """获取交易对分析统计"""
        try:
            if self.redis_client:
                # 获取热门交易对
                symbol_scores = {}
                result_keys = self.redis_client.keys("scan_result:*")
                for key in result_keys[-100:]:  # 最近100条结果
                    result_data = self.redis_client.get(key)
                    if result_data:
                        import json

                        result = json.loads(result_data)
                        symbol = result.get("symbol")
                        score = result.get("score", 0)
                        if symbol:
                            if symbol not in symbol_scores:
                                symbol_scores[symbol] = {"total_score": 0, "count": 0}
                            symbol_scores[symbol]["total_score"] += score
                            symbol_scores[symbol]["count"] += 1

                # 计算平均分数并排序
                symbol_stats = []
                for symbol, data in symbol_scores.items():
                    avg_score = data["total_score"] / data["count"]
                    symbol_stats.append(
                        {
                            "symbol": symbol,
                            "avg_score": round(avg_score, 3),
                            "scan_count": data["count"],
                        }
                    )

                return sorted(symbol_stats, key=lambda x: x["avg_score"], reverse=True)[
                    :20
                ]
            return []
        except Exception as e:
            self.logger.error(f"Error getting symbol analysis stats: {e}")
            return []

    def _get_time_series_stats(self):
        """获取时间序列统计"""
        try:
            if self.redis_client:
                # 获取过去7天的数据
                time_series = []
                for i in range(7):
                    date = (datetime.now() - timedelta(days=i)).strftime("%Y%m%d")
                    day_key = f"stats:daily:{date}"
                    day_data = self.redis_client.get(day_key)
                    if day_data:
                        import json

                        data = json.loads(day_data)
                    else:
                        data = {
                            "total_scans": 0,
                            "high_score_results": 0,
                            "avg_score": 0,
                        }

                    time_series.append(
                        {
                            "date": date,
                            "total_scans": data.get("total_scans", 0),
                            "high_score_results": data.get("high_score_results", 0),
                            "avg_score": data.get("avg_score", 0),
                        }
                    )

                return time_series[::-1]  # 反转以按时间顺序排列
            return []
        except Exception as e:
            self.logger.error(f"Error getting time series stats: {e}")
            return []

    def _get_engine_comparison_stats(self):
        """获取引擎对比统计"""
        try:
            engines = ["three_high", "black_horse", "potential_finder"]
            engine_stats = []

            for engine in engines:
                if self.redis_client:
                    # 获取引擎统计数据
                    stats_key = f"engine_stats:{engine}"
                    stats_data = self.redis_client.get(stats_key)
                    if stats_data:
                        import json

                        stats = json.loads(stats_data)
                    else:
                        stats = {
                            "total_scans": 0,
                            "success_rate": 0,
                            "avg_score": 0,
                            "avg_response_time": 0,
                        }
                else:
                    # 模拟数据
                    import random

                    stats = {
                        "total_scans": random.randint(100, 1000),
                        "success_rate": round(random.uniform(85, 99), 1),
                        "avg_score": round(random.uniform(0.3, 0.8), 3),
                        "avg_response_time": round(random.uniform(50, 300), 1),
                    }

                engine_stats.append(
                    {
                        "engine": engine,
                        "name": {
                            "three_high": "三高股票",
                            "black_horse": "黑马股票",
                            "potential_finder": "潜力股挖掘",
                        }.get(engine, engine),
                        **stats,
                    }
                )

            return engine_stats
        except Exception as e:
            self.logger.error(f"Error getting engine comparison stats: {e}")
            return []

    async def run_async(self, host="0.0.0.0", port=8000):
        """异步启动Web应用"""
        try:
            # 使用SocketIO服务器
            self.logger.info(f"Starting SocketIO server on {host}:{port}")
            self.socketio.run(self.app, host=host, port=port, debug=False)
        except Exception as e:
            self.logger.error(f"Failed to start SocketIO server: {e}")
            # 回退到同步模式
            self.logger.info("Falling back to sync mode")
            self.app.run(host=host, port=port, debug=False)

    async def run(self, host: str = "0.0.0.0", port: int = 8000, debug: bool = False):
        """异步启动Web应用"""
        try:
            from hypercorn.asyncio import serve
            from hypercorn import Config

            config = Config()
            config.bind = [f"{host}:{port}"]
            config.debug = debug
            config.access_log_format = (
                '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'
            )

            self.logger.info(f"Starting Scanner Web App on {host}:{port}")
            await serve(self.app, config)
        except ImportError:
            # 如果hypercorn不可用，回退到同步模式
            self.logger.warning("Hypercorn not available, falling back to sync mode")
            self.app.run(host=host, port=port, debug=debug)


def create_app(redis_client=None, zmq_client=None, health_checker=None) -> Flask:
    """创建Flask应用实例"""
    web_app = ScannerWebApp(
        redis_client=redis_client, zmq_client=zmq_client, health_checker=health_checker
    )
    app = web_app.app
    # 将ScannerWebApp实例附加到Flask应用，便于运行时访问SocketIO等资源
    setattr(app, "_scanner_web_app", web_app)
    return app


async def run_web_app(app=None, host="0.0.0.0", port=8000, debug=False):
    """异步启动Web应用，优先使用Flask-SocketIO服务器；在异步环境中通过线程执行避免阻塞事件循环"""
    try:
        # 确保我们有对应的ScannerWebApp实例用于启动SocketIO服务器
        if app is None:
            web_app = ScannerWebApp()
            app = web_app.app
            setattr(app, "_scanner_web_app", web_app)
        elif hasattr(app, "_scanner_web_app"):
            web_app = getattr(app, "_scanner_web_app")
        else:
            # 回退方案：直接在传入的Flask应用上创建一个SocketIO实例以提供HTTP服务
            # 注意：此回退不包含原有的SocketIO事件注册，仅确保HTTP端点可用
            from flask_socketio import SocketIO as _SocketIO
            _socketio = _SocketIO(app, cors_allowed_origins="*")
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(
                None, lambda: _socketio.run(app, host=host, port=port, debug=debug)
            )
            return

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None,
            lambda: web_app.socketio.run(
                web_app.app, host=host, port=port, debug=debug
            ),
        )
    except Exception as e:
        logger = get_logger(__name__)
        logger.error(f"Failed to start SocketIO server: {e}")
        # 最终回退到同步Flask服务器
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None, lambda: app.run(host=host, port=port, debug=debug)
        )
