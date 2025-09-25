"""ZeroMQ Load Balancer implementation using ROUTER/DEALER pattern."""

import zmq
import json
import time
import logging
import threading
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from ..config import get_settings


@dataclass
class WorkerInfo:
    """Worker process information."""

    worker_id: str
    last_heartbeat: float
    status: str = "idle"  # idle, busy, unhealthy
    processed_requests: int = 0


class LoadBalancer:
    """ZeroMQ ROUTER/DEALER Load Balancer.

    Implements the Lazy Pirate Pattern for reliable request-response communication.
    Routes client requests to available worker processes.
    """

    def __init__(self):
        self.settings = get_settings()
        self.context = zmq.Context()
        self.logger = logging.getLogger(__name__)

        # Frontend socket (clients connect here)
        self.frontend = self.context.socket(zmq.ROUTER)
        self.frontend.bind(
            f"tcp://{self.settings.zmq_bind_address}:{self.settings.zmq_frontend_port}"
        )

        # Backend socket (workers connect here) -> ROUTER to support identity routing
        self.backend = self.context.socket(zmq.ROUTER)
        self.backend.bind(
            f"tcp://{self.settings.zmq_bind_address}:{self.settings.zmq_backend_port}"
        )

        # Worker management
        self.workers: Dict[str, WorkerInfo] = {}
        self.available_workers: List[str] = []

        # Request tracking for client_id recovery
        self.pending_requests: Dict[str, Dict[str, Any]] = {}  # request_id -> {"client_id": bytes, "expects_empty": bool}
        # Track which worker handled which request to re-add it to pool upon response
        self.pending_assignments: Dict[str, str] = {}  # request_id -> worker_id

        # Control flags
        self.running = False
        self.health_check_thread: Optional[threading.Thread] = None

        self.logger.info(
            f"LoadBalancer initialized on ports {self.settings.zmq_frontend_port}/{self.settings.zmq_backend_port}"
        )

    def start(self):
        """Start the load balancer."""
        self.running = True

        # Start health check thread
        self.health_check_thread = threading.Thread(
            target=self._health_check_loop, daemon=True
        )
        self.health_check_thread.start()

        self.logger.info("LoadBalancer started")

        # Main message routing loop
        self._message_loop()

    def stop(self):
        """Stop the load balancer."""
        self.running = False

        if self.health_check_thread:
            self.health_check_thread.join(timeout=5)

        self.frontend.close()
        self.backend.close()
        self.context.term()

        self.logger.info("LoadBalancer stopped")

    def _message_loop(self):
        """Main message routing loop."""
        poller = zmq.Poller()
        poller.register(self.frontend, zmq.POLLIN)
        poller.register(self.backend, zmq.POLLIN)

        while self.running:
            try:
                # 初次阻塞等待任一事件到来
                _ = dict(poller.poll(timeout=1000))

                # 排空处理：先后端，后前端，直到本轮无事件
                processed_any = True
                while processed_any and self.running:
                    processed_any = False

                    # 先完全排空后端（REGISTER/HEARTBEAT/RESPONSE）
                    while True:
                        inner = dict(poller.poll(timeout=0))
                        if self.backend in inner:
                            self._handle_worker_response()
                            processed_any = True
                            continue
                        break

                    # 再完全排空前端（客户端请求）
                    while True:
                        inner = dict(poller.poll(timeout=0))
                        if self.frontend in inner:
                            self._handle_client_request()
                            processed_any = True
                            continue
                        break

            except zmq.ZMQError as e:
                self.logger.error(f"ZMQ error in message loop: {e}")
            except Exception as e:
                self.logger.error(f"Unexpected error in message loop: {e}")

    def _handle_client_request(self):
        """Handle incoming client request."""
        try:
            # Receive client request with flexible framing
            parts = self.frontend.recv_multipart()

            client_id = None
            request_data = None
            expects_empty = False

            if len(parts) == 3:
                # Typical client format (DEALER with delimiter): [client_id, empty, request_data]
                client_id, _empty, request_data = parts
                expects_empty = True
            elif len(parts) == 2:
                # REQ->ROUTER format: [client_id, request_data]
                client_id, request_data = parts
                expects_empty = False
            elif len(parts) > 3:
                # Fallback: take first as client_id, last as request_data
                client_id = parts[0]
                request_data = parts[-1]
                # Heuristic: if the frame before last is an empty delimiter, preserve it on reply
                expects_empty = (len(parts) >= 2 and parts[-2] == b"")
                self.logger.debug(
                    f"Received non-standard client frames: {len(parts)}; using first and last frames"
                )
            else:
                raise ValueError(
                    f"Unexpected client message format: {len(parts)} parts"
                )

            # Parse request JSON safely
            try:
                request = json.loads(request_data.decode("utf-8"))
            except Exception as e:
                error_response = {
                    "status": "error",
                    "request_id": "unknown",
                    "error": f"invalid_json: {str(e)}",
                }
                encoded = json.dumps(error_response).encode("utf-8")
                if expects_empty:
                    self.frontend.send_multipart([client_id, b"", encoded])
                else:
                    self.frontend.send_multipart([client_id, encoded])
                return

            # Ensure request_id exists to maintain pending mapping
            request_id = request.get("request_id")
            if not request_id or not isinstance(request_id, str):
                import uuid as _uuid

                request_id = _uuid.uuid4().hex
                request["request_id"] = request_id
                request_data = json.dumps(request).encode("utf-8")

            self.logger.debug(
                f"Received request {request_id} from client {client_id.hex()}"
            )

            # Check if workers are available
            if not self.available_workers:
                error_response = {
                    "status": "error",
                    "request_id": request_id,
                    "error": "No workers available",
                }
                encoded = json.dumps(error_response).encode("utf-8")
                if expects_empty:
                    self.frontend.send_multipart([client_id, b"", encoded])
                else:
                    self.frontend.send_multipart([client_id, encoded])
                return

            # Get next available worker
            worker_id = self.available_workers.pop(0)

            # Update worker status
            if worker_id in self.workers:
                self.workers[worker_id].status = "busy"
                self.workers[worker_id].processed_requests += 1

            # Store client_id and framing expectation for this request
            self.pending_requests[request_id] = {
                "client_id": client_id,
                "expects_empty": expects_empty,
            }
            # Track worker assignment for this request so we can re-add on completion
            self.pending_assignments[request_id] = worker_id

            # Forward request to worker (ROUTER backend requires worker identity prefix)
            self.backend.send_multipart(
                [worker_id.encode("utf-8"), b"", client_id, b"", request_data]
            )

        except Exception as e:
            self.logger.error(f"Error handling client request: {e}")

    def _handle_worker_heartbeat(self, worker_id: str, heartbeat_data: bytes):
        """Handle worker heartbeat."""
        try:
            import json

            heartbeat_msg = json.loads(heartbeat_data.decode("utf-8"))

            # Update worker heartbeat time
            if worker_id in self.workers:
                self.workers[worker_id].last_heartbeat = time.time()
                self.workers[worker_id].processed_requests = heartbeat_msg.get(
                    "processed_requests", 0
                )
                self.logger.debug(f"Heartbeat received from worker {worker_id}")
            else:
                self.logger.warning(
                    f"Received heartbeat from unregistered worker: {worker_id}"
                )

        except Exception as e:
            self.logger.error(f"Error handling worker heartbeat for {worker_id}: {e}")

    def _handle_worker_response(self):
        """Handle any message arriving from backend (workers):
        - Registration: [worker_id, empty?, b"REGISTER", registration_json]
        - Heartbeat:    [worker_id, empty?, b"HEARTBEAT", heartbeat_json]
        - Response:     [worker_id, client_id, empty, response_json]
        兼容旧格式（无worker_id前缀）以提高健壮性。
        """
        try:
            parts = self.backend.recv_multipart()
            if not parts:
                return

            worker_identity: Optional[bytes] = None
            idx = 0

            # 尝试解析首帧为worker身份（ROUTER特有）
            if parts and parts[0] not in (b"", b"REGISTER", b"HEARTBEAT"):
                worker_identity = parts[0]
                idx = 1
                if idx < len(parts) and parts[idx] == b"":
                    idx += 1

            # 控制消息（REGISTER/HEARTBEAT）
            if idx < len(parts) and parts[idx] in (b"REGISTER", b"HEARTBEAT"):
                msg_type = parts[idx]
                payload = parts[idx + 1] if (idx + 1) < len(parts) else b"{}"
                try:
                    data = json.loads(payload.decode("utf-8"))
                except Exception:
                    data = {}
                worker_id = (
                    (worker_identity.decode("utf-8") if worker_identity else None)
                    or data.get("worker_id")
                    or "unknown"
                )

                if msg_type == b"REGISTER":
                    if worker_id != "unknown":
                        if worker_id not in self.workers:
                            self.register_worker(worker_id)
                        else:
                            if worker_id not in self.available_workers:
                                self.available_workers.append(worker_id)
                    else:
                        self.logger.warning("REGISTER message missing worker_id")
                else:  # HEARTBEAT
                    if worker_id != "unknown":
                        self._handle_worker_heartbeat(worker_id, payload)
                    else:
                        self.logger.warning("HEARTBEAT message missing worker_id")
                return

            # 普通响应（带有client_id）
            client_id: Optional[bytes] = None
            response_bytes: Optional[bytes] = None

            if worker_identity is not None:
                # 格式: [worker_id, client_id, empty?, response_json]
                if idx < len(parts):
                    client_id = parts[idx]
                    # 响应数据在最后一帧
                    response_bytes = parts[-1]
                else:
                    self.logger.warning("Backend message missing client_id after identity")
                    return
            else:
                # 兼容旧格式（无worker身份前缀）
                if len(parts) >= 3:
                    client_id = parts[0]
                    response_bytes = parts[-1]
                elif len(parts) == 2 and parts[0] != b"":
                    client_id = parts[0]
                    response_bytes = parts[1]
                else:
                    self.logger.warning(
                        f"Unexpected backend message format: {len(parts)} parts"
                    )
                    return

            # 解析 request_id 以便回收 worker
            request_id = None
            try:
                resp_obj = json.loads(response_bytes.decode("utf-8"))
                request_id = resp_obj.get("request_id")
            except Exception:
                resp_obj = None

            # 从pending映射解析client_id与响应帧格式（如果存在）
            expects_empty = False
            if request_id and request_id in self.pending_requests:
                entry = self.pending_requests.pop(request_id)
                client_id = entry.get("client_id", client_id)
                expects_empty = bool(entry.get("expects_empty", False))

            # 将响应转发给前端客户端（根据原始请求的帧格式）
            if client_id is not None:
                if expects_empty:
                    self.frontend.send_multipart([client_id, b"", response_bytes])
                else:
                    self.frontend.send_multipart([client_id, response_bytes])
            else:
                self.logger.warning("Cannot route response: missing client_id")

            # 将完成任务的worker重新加入可用池
            if request_id and request_id in self.pending_assignments:
                worker_id = self.pending_assignments.pop(request_id)
                if worker_id in self.workers:
                    self.workers[worker_id].status = "idle"
                    if worker_id not in self.available_workers:
                        self.available_workers.append(worker_id)
                else:
                    self.logger.debug(
                        f"Completed request {request_id} from unknown worker {worker_id}"
                    )

        except Exception as e:
            self.logger.error(f"Error handling worker backend message: {e}")

    def _health_check_loop(self):
        """Periodic health check to prune stale workers and keep availability accurate."""
        interval = getattr(self.settings, "health_check_interval", 5)
        stale_factor = 3  # consider worker stale if no heartbeat for 3x interval
        while self.running:
            try:
                now = time.time()
                stale_threshold = now - stale_factor * interval

                # Remove workers that are stale from available pool and mark unhealthy
                for worker_id, info in list(self.workers.items()):
                    if info.last_heartbeat < stale_threshold:
                        if worker_id in self.available_workers:
                            try:
                                self.available_workers.remove(worker_id)
                            except ValueError:
                                pass
                        info.status = "unhealthy"

                time.sleep(interval)
            except Exception as e:
                self.logger.error(f"Health check loop error: {e}")
                time.sleep(interval)

    def register_worker(self, worker_id: str):
        """Register a new worker."""
        self.workers[worker_id] = WorkerInfo(
            worker_id=worker_id, last_heartbeat=time.time()
        )
        self.available_workers.append(worker_id)
        self.logger.info(f"Worker registered: {worker_id}")

    def get_status(self) -> Dict:
        """Get load balancer status."""
        return {
            "active_workers": len(self.workers),
            "available_workers": len(self.available_workers),
            "total_requests_processed": sum(
                w.processed_requests for w in self.workers.values()
            ),
            "workers": {
                worker_id: {
                    "status": info.status,
                    "processed_requests": info.processed_requests,
                    "last_heartbeat": info.last_heartbeat,
                }
                for worker_id, info in self.workers.items()
            },
        }
