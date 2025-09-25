# -*- coding: utf-8 -*-
"""
NeuroTrade Nexus - ZeroMQ订阅者客户端
负责接收和处理crawler.news主题消息
"""

import sys
import os
import json
import time
import threading
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime
from queue import Queue, Empty

# 添加依赖库路径
# 添加依赖库路径（优先读取环境变量 YILAI_DIR，其次回退到 D:\\YiLai；仅在目录存在且未加入 sys.path 时插入）
YILAI_DIR = os.getenv("YILAI_DIR", r"D:\\YiLai")
core_lib_path = os.path.join(YILAI_DIR, "core_lib")
if os.path.isdir(core_lib_path) and core_lib_path not in sys.path:
    sys.path.insert(0, core_lib_path)

import zmq
from zmq import Context, Socket, Poller

from ..config import ConfigManager
from ..utils import Logger
from .publisher import NewsMessage


class ZMQSubscriber:
    """ZeroMQ订阅者客户端

    核心功能：
    1. 订阅crawler.news主题消息
    2. 异步消息处理
    3. 消息过滤和路由
    4. 错误处理和重连
    """

    def __init__(self, config: ConfigManager, logger: Logger = None):
        """初始化ZeroMQ订阅者

        Args:
            config: 配置管理器
            logger: 日志记录器
        """
        self.config = config
        self.logger = logger or Logger(config)

        # ZeroMQ配置
        self.zmq_config = config.get_zmq_config()
        self.host = self.zmq_config.get("subscriber", {}).get("host", "127.0.0.1")
        self.port = self.zmq_config.get("subscriber", {}).get("port", 5556)
        self.topics = self.zmq_config.get("subscriber", {}).get(
            "topics", ["crawler.news"]
        )
        self.timeout = self.zmq_config.get("timeout", 5000)
        self.high_water_mark = self.zmq_config.get("high_water_mark", 1000)

        # ZeroMQ上下文和套接字
        self.context: Optional[Context] = None
        self.socket: Optional[Socket] = None
        self.poller: Optional[Poller] = None

        # 连接状态
        self._connected = False
        self._running = False

        # 消息处理
        self._message_handlers: Dict[str, Callable] = {}
        self._message_queue = Queue(maxsize=10000)
        self._worker_threads: List[threading.Thread] = []
        self._num_workers = 4

        # 消息统计
        self.stats = {
            "messages_received": 0,
            "messages_processed": 0,
            "messages_failed": 0,
            "bytes_received": 0,
            "connection_errors": 0,
            "last_message_time": None,
        }

        # 线程锁
        self._lock = threading.Lock()

        self.logger.info(f"ZeroMQ订阅者初始化: {self.host}:{self.port}")

    def connect(self) -> bool:
        """连接到ZeroMQ服务器

        Returns:
            连接是否成功
        """
        try:
            with self._lock:
                if self._connected:
                    self.logger.warning("ZeroMQ订阅者已连接")
                    return True

                # 创建ZeroMQ上下文
                self.context = zmq.Context()

                # 创建订阅者套接字
                self.socket = self.context.socket(zmq.SUB)

                # 设置套接字选项
                self.socket.setsockopt(zmq.RCVHWM, self.high_water_mark)
                self.socket.setsockopt(zmq.RCVTIMEO, self.timeout)
                self.socket.setsockopt(zmq.LINGER, 1000)

                # 订阅主题
                for topic in self.topics:
                    self.socket.setsockopt_string(zmq.SUBSCRIBE, topic)
                    self.logger.info(f"订阅主题: {topic}")

                # 连接到地址
                connect_address = f"tcp://{self.host}:{self.port}"
                self.socket.connect(connect_address)

                # 创建轮询器
                self.poller = zmq.Poller()
                self.poller.register(self.socket, zmq.POLLIN)

                self._connected = True
                self._running = True

                self.logger.info(f"✓ ZeroMQ订阅者连接成功: {connect_address}")
                return True

        except Exception as e:
            self.stats["connection_errors"] += 1
            self.logger.error(f"ZeroMQ订阅者连接失败: {e}")
            return False

    def disconnect(self) -> None:
        """断开ZeroMQ连接"""
        try:
            with self._lock:
                self._running = False

                # 停止工作线程
                self._stop_workers()

                if self.poller:
                    self.poller.unregister(self.socket)
                    self.poller = None

                if self.socket:
                    self.socket.close()
                    self.socket = None

                if self.context:
                    self.context.term()
                    self.context = None

                self._connected = False

                self.logger.info("✓ ZeroMQ订阅者连接已断开")

        except Exception as e:
            self.logger.error(f"ZeroMQ订阅者断开连接失败: {e}")

    def register_handler(
        self, topic: str, handler: Callable[[NewsMessage], None]
    ) -> None:
        """注册消息处理器

        Args:
            topic: 主题名称
            handler: 消息处理函数
        """
        self._message_handlers[topic] = handler
        self.logger.info(f"注册消息处理器: {topic}")

    def start_listening(self) -> None:
        """开始监听消息"""
        if not self._connected:
            if not self.connect():
                raise RuntimeError("无法连接到ZeroMQ服务器")

        # 启动工作线程
        self._start_workers()

        self.logger.info("开始监听ZeroMQ消息...")

        try:
            while self._running:
                try:
                    # 轮询消息
                    socks = dict(self.poller.poll(timeout=1000))

                    if self.socket in socks and socks[self.socket] == zmq.POLLIN:
                        # 接收消息
                        message_parts = self.socket.recv_multipart(zmq.NOBLOCK)

                        if len(message_parts) >= 2:
                            topic = message_parts[0].decode("utf-8")
                            message_data = message_parts[1].decode("utf-8")

                            # 更新统计
                            self.stats["messages_received"] += 1
                            self.stats["bytes_received"] += len(message_data)
                            self.stats[
                                "last_message_time"
                            ] = datetime.utcnow().isoformat()

                            # 将消息加入处理队列
                            try:
                                self._message_queue.put(
                                    (topic, message_data), timeout=1
                                )
                            except:
                                self.logger.warning("消息队列已满，丢弃消息")
                                self.stats["messages_failed"] += 1

                except zmq.Again:
                    # 超时，继续轮询
                    continue
                except Exception as e:
                    self.logger.error(f"接收消息失败: {e}")
                    self.stats["connection_errors"] += 1
                    time.sleep(1)

        except KeyboardInterrupt:
            self.logger.info("收到停止信号")
        finally:
            self.disconnect()

    def _start_workers(self) -> None:
        """启动工作线程"""
        for i in range(self._num_workers):
            worker = threading.Thread(
                target=self._worker_loop, name=f"ZMQWorker-{i}", daemon=True
            )
            worker.start()
            self._worker_threads.append(worker)

        self.logger.info(f"启动 {self._num_workers} 个工作线程")

    def _stop_workers(self) -> None:
        """停止工作线程"""
        # 等待工作线程结束
        for worker in self._worker_threads:
            if worker.is_alive():
                worker.join(timeout=5)

        self._worker_threads.clear()
        self.logger.info("工作线程已停止")

    def _worker_loop(self) -> None:
        """工作线程循环"""
        while self._running:
            try:
                # 从队列获取消息
                topic, message_data = self._message_queue.get(timeout=1)

                # 处理消息
                self._process_message(topic, message_data)

                # 标记任务完成
                self._message_queue.task_done()

            except Empty:
                # 队列为空，继续等待
                continue
            except Exception as e:
                self.logger.error(f"工作线程处理消息失败: {e}")
                self.stats["messages_failed"] += 1

    def _process_message(self, topic: str, message_data: str) -> None:
        """处理单个消息

        Args:
            topic: 消息主题
            message_data: 消息数据
        """
        try:
            # 解析JSON消息
            data = json.loads(message_data)

            # 创建消息对象
            message = NewsMessage.from_dict(data)

            # 查找处理器
            handler = self._message_handlers.get(topic)

            if handler:
                # 调用处理器
                handler(message)
                self.stats["messages_processed"] += 1

                self.logger.debug(
                    f"消息处理成功: {message.id} | 主题: {topic} | " f"来源: {message.source}"
                )
            else:
                self.logger.warning(f"未找到主题处理器: {topic}")

        except json.JSONDecodeError as e:
            self.logger.error(f"消息JSON解析失败: {e}")
            self.stats["messages_failed"] += 1
        except Exception as e:
            self.logger.error(f"消息处理失败: {e}")
            self.stats["messages_failed"] += 1

    def get_stats(self) -> Dict[str, Any]:
        """获取订阅统计信息

        Returns:
            统计信息字典
        """
        stats = self.stats.copy()
        stats.update(
            {
                "connected": self._connected,
                "running": self._running,
                "queue_size": self._message_queue.qsize(),
                "worker_threads": len(self._worker_threads),
                "host": self.host,
                "port": self.port,
                "topics": self.topics,
            }
        )
        return stats

    def health_check(self) -> Dict[str, Any]:
        """健康检查

        Returns:
            健康状态信息
        """
        status = "healthy" if self._connected and self._running else "unhealthy"

        return {
            "status": status,
            "connected": self._connected,
            "running": self._running,
            "messages_received": self.stats["messages_received"],
            "messages_processed": self.stats["messages_processed"],
            "messages_failed": self.stats["messages_failed"],
            "connection_errors": self.stats["connection_errors"],
            "queue_size": self._message_queue.qsize(),
            "last_message_time": self.stats["last_message_time"],
        }

    def __enter__(self):
        """上下文管理器入口"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.disconnect()

    def __del__(self):
        """析构函数"""
        try:
            self.disconnect()
        except:
            pass


if __name__ == "__main__":
    # 测试ZeroMQ订阅者
    import json
    from ..config import ConfigManager
    from ..utils import Logger

    # 初始化配置和日志
    config = ConfigManager("development")
    logger = Logger(config)

    # 创建订阅者
    subscriber = ZMQSubscriber(config, logger)

    # 定义消息处理器
    def handle_news_message(message: NewsMessage):
        print(f"收到新闻消息: {message.title}")
        print(f"来源: {message.source}")
        print(f"内容: {message.content[:100]}...")
        print("-" * 50)

    try:
        # 注册处理器
        subscriber.register_handler("crawler.news", handle_news_message)

        # 开始监听
        print("开始监听消息，按 Ctrl+C 停止...")
        subscriber.start_listening()

    except KeyboardInterrupt:
        print("\n停止监听")
    finally:
        # 显示统计信息
        stats = subscriber.get_stats()
        print(f"订阅统计: {json.dumps(stats, indent=2, ensure_ascii=False)}")
