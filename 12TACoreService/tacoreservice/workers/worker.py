"""Worker process implementation for TACoreService."""

import json
import logging
import threading
import time
import uuid
from typing import Dict, Any, Optional

import zmq

from ..config import get_settings
from ..core.message_handler import MessageHandler, ServiceRequest, ServiceResponse
from ..core.database import DatabaseManager
from .tradingagents_adapter import TradingAgentsAdapter


class Worker:
    """ZeroMQ DEALER worker process.

    Connects to the load balancer backend and processes requests
    using TradingAgents-CN functionality.
    """

    def __init__(self, worker_id: Optional[str] = None):
        self.settings = get_settings()
        self.worker_id = worker_id or f"worker-{uuid.uuid4().hex[:8]}"
        self.logger = logging.getLogger(f"{__name__}.{self.worker_id}")

        # ZeroMQ setup
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.DEALER)
        self.socket.identity = self.worker_id.encode("utf-8")

        # Components
        self.message_handler = MessageHandler()
        self.db_manager = DatabaseManager()
        self.trading_adapter = TradingAgentsAdapter()

        # Worker state
        self.running = False
        self.processed_requests = 0
        self.last_heartbeat = time.time()
        
        # System metrics
        self.cpu_usage = 0.0
        self.memory_usage = 0.0

        # Heartbeat thread
        self.heartbeat_thread: Optional[threading.Thread] = None

        self.logger.info(f"Worker {self.worker_id} initialized")

    def start(self):
        """Start the worker process."""
        try:
            # Set socket identity before connecting
            self.socket.setsockopt(zmq.IDENTITY, self.worker_id.encode("utf-8"))

            # Connect to load balancer backend
            backend_host = getattr(self.settings, 'zmq_backend_host', 'tacoreservice')
            backend_address = f"tcp://{backend_host}:{self.settings.zmq_backend_port}"
            self.socket.connect(backend_address)

            self.running = True

            # Send registration message to load balancer
            self._register_with_load_balancer()

            # Start heartbeat thread
            self.heartbeat_thread = threading.Thread(
                target=self._heartbeat_loop, daemon=True
            )
            self.heartbeat_thread.start()

            # Register worker with database
            self.db_manager.update_worker_status(
                worker_id=self.worker_id, status="idle", processed_requests=0
            )

            self.logger.info(
                f"Worker {self.worker_id} started and connected to {backend_address}"
            )

            # Main processing loop
            self._process_loop()

        except Exception as e:
            self.logger.error(f"Failed to start worker {self.worker_id}: {e}")
            raise

    def stop(self):
        """Stop the worker process."""
        self.running = False

        if self.heartbeat_thread:
            self.heartbeat_thread.join(timeout=5)

        # Update worker status
        self.db_manager.update_worker_status(worker_id=self.worker_id, status="stopped")

        self.socket.close()
        self.context.term()
        self.db_manager.close()

        self.logger.info(f"Worker {self.worker_id} stopped")

    def _process_loop(self):
        """Main request processing loop."""
        poller = zmq.Poller()
        poller.register(self.socket, zmq.POLLIN)

        while self.running:
            try:
                socks = dict(poller.poll(timeout=1000))

                if self.socket in socks:
                    self._handle_incoming_frames()

            except zmq.ZMQError as e:
                self.logger.error(f"ZMQ error in worker {self.worker_id}: {e}")
            except Exception as e:
                self.logger.error(f"Unexpected error in worker {self.worker_id}: {e}")

    def _handle_incoming_frames(self):
        """Receive and handle incoming multipart ZMQ frames from load balancer.
        This method replaces the previous _handle_request() that read multipart frames
        to avoid name collision with the dict-compatible _handle_request(request_data).
        """
        start_time = time.time()

        try:
            # Receive request from load balancer
            parts = self.socket.recv_multipart()

            if len(parts) == 5:
                # Expected format from load balancer: [worker_id, empty, client_id, empty, request_data]
                worker_id, empty1, client_id, empty2, request_data = parts
            elif len(parts) == 4:
                # Format when ROUTER routes to DEALER: [empty, client_id, empty, request_data]
                empty1, client_id, empty2, request_data = parts
            elif len(parts) == 3:
                # Direct format (for testing): [client_id, empty, request_data]
                client_id, empty, request_data = parts
            else:
                self.logger.error(f"Unexpected message format: {len(parts)} parts")
                return

            # Parse request
            request = self.message_handler.parse_request(request_data)

            # Log request
            self.message_handler.log_request(request, client_id.hex())
            self.db_manager.log_request(
                request_id=request.request_id,
                method=request.method,
                request_data=request.params,
                client_id=client_id.hex(),
                worker_id=self.worker_id,
            )

            # Update worker status to busy
            self.db_manager.update_worker_status(
                worker_id=self.worker_id, status="busy"
            )

            # Validate request parameters
            if not self.message_handler.validate_request_params(
                request.method, request.params
            ):
                response = self.message_handler.create_error_response(
                    request_id=request.request_id,
                    error_message="Invalid request parameters",
                )
            else:
                # Process request
                response = self._process_request(request)

            # Calculate processing time
            processing_time_ms = int((time.time() - start_time) * 1000)
            response.processing_time_ms = processing_time_ms

            # Log response
            self.message_handler.log_response(response, processing_time_ms)
            self.db_manager.log_response(
                request_id=request.request_id,
                response_data=response.data or {},
                processing_time_ms=processing_time_ms,
                status=response.status,
            )

            # Send response back
            response_data = self.message_handler.serialize_response(response)
            # Format: [client_id, empty, response_data] - worker identity is added automatically by DEALER
            self.socket.send_multipart([client_id, b"", response_data])

            # Update statistics
            self.processed_requests += 1
            self.last_heartbeat = time.time()

            # Update worker status back to idle
            self.db_manager.update_worker_status(
                worker_id=self.worker_id,
                status="idle",
                processed_requests=self.processed_requests,
            )

        except Exception as e:
            self.logger.error(f"Error handling request in worker {self.worker_id}: {e}")

            # Send error response if possible
            try:
                error_response = self.message_handler.create_error_response(
                    request_id="unknown",
                    error_message=f"Internal server error: {str(e)}",
                )
                response_data = self.message_handler.serialize_response(error_response)
                # Format: [client_id, empty, response_data] - worker identity is added automatically by DEALER
                self.socket.send_multipart([client_id, b"", response_data])
            except:
                pass  # Best effort error response

    def _handle_request(self, request_data):
        """Handle request in dict format (for testing compatibility)."""
        try:
            method = request_data.get('method')
            params = request_data.get('parameters', {})
            request_id = request_data.get('request_id', 'unknown')
            
            if method == "health.check":
                response = self._handle_health_check(request_data)
            elif method == "scan.market":
                response = self._handle_scan_market(request_data)
            elif method == "execute.order":
                response = self._handle_execute_order(request_data)
            elif method == "evaluate.risk":
                response = self._handle_evaluate_risk(request_data)
            elif method == "analyze.stock":
                response = self._handle_analyze_stock(request_data)
            elif method == "get.market_data":
                response = self._handle_get_market_data(request_data)
            else:
                return {
                    'status': 'error',
                    'error': f'unknown_method: {method}',
                    'request_id': request_id,
                    'timestamp': time.time()
                }
            
            # Convert ServiceResponse to dict if needed
            if hasattr(response, 'to_dict'):
                return response.to_dict()
            else:
                return response
                
        except Exception as e:
            return {
                'status': 'error',
                'error': f'processing_error: {str(e)}',
                'request_id': request_data.get('request_id', 'unknown'),
                'timestamp': time.time()
            }

    def _process_request(self, request: ServiceRequest) -> ServiceResponse:
        """Process a service request using TradingAgents-CN."""
        try:
            method = request.method
            params = request.params

            if method == "health.check":
                return self._handle_health_check(request)
            elif method == "scan.market":
                return self._handle_scan_market(request)
            elif method == "execute.order":
                return self._handle_execute_order(request)
            elif method == "evaluate.risk":
                return self._handle_evaluate_risk(request)
            elif method == "analyze.stock":
                return self._handle_analyze_stock(request)
            elif method == "get.market_data":
                return self._handle_get_market_data(request)
            else:
                return self.message_handler.create_error_response(
                    request_id=request.request_id,
                    error_message=f"unknown_method: {method}",
                )

        except Exception as e:
            self.logger.error(f"Error processing request {request.request_id}: {e}")
            return self.message_handler.create_error_response(
                request_id=request.request_id,
                error_message=f"Processing error: {str(e)}",
            )

    def _handle_health_check(self, request) -> ServiceResponse:
        """Handle health check request."""
        # Handle both ServiceRequest object and dict
        if hasattr(request, 'request_id'):
            request_id = request.request_id
        else:
            request_id = request.get('request_id', 'unknown')
        
        # Increment processed requests counter for performance metrics
        self.processed_requests += 1
            
        return self.message_handler.create_response(
            request_id=request_id,
            data={
                "worker_id": self.worker_id,
                "health": "ok",
                "status": "healthy",
                "processed_requests": self.processed_requests,
                "uptime": time.time() - self.last_heartbeat,
                "timestamp": time.time(),
            },
        )

    def _handle_scan_market(self, request) -> ServiceResponse:
        """Handle market scanning request."""
        try:
            # Handle both ServiceRequest object and dict
            if hasattr(request, 'params'):
                # ServiceRequest object
                params = request.params
                request_id = request.request_id
            else:
                # Dict format (for testing)
                params = request.get('parameters', {})
                request_id = request.get('request_id', 'unknown')
            
            result = self.trading_adapter.scan_market(
                market_type=params.get("market_type"),
                symbols=params.get("symbols"),
                filters=params.get("filters", {}),
            )

            # Check if adapter returned an error
            if isinstance(result, dict) and not result.get('success', True):
                error_info = result.get('error', {})
                error_type = error_info.get('type', 'unknown_error')
                error_message = error_info.get('message', 'Market scan failed')
                return self.message_handler.create_error_response(
                    request_id=request_id,
                    error_message=f"Market scan failed: {error_message} ({error_type})"
                )

            return self.message_handler.create_response(
                request_id=request_id, data=result
            )

        except Exception as e:
            # Handle both ServiceRequest object and dict
            if hasattr(request, 'request_id'):
                request_id = request.request_id
            else:
                request_id = request.get('request_id', 'unknown')
                
            return self.message_handler.create_error_response(
                request_id=request_id,
                error_message=f"Market scan failed: {str(e)} (internal_error)",
            )

    def _handle_execute_order(self, request) -> ServiceResponse:
        """Handle order execution request."""
        try:
            # Handle both ServiceRequest object and dict
            if hasattr(request, 'params'):
                # ServiceRequest object
                params = request.params
                request_id = request.request_id
            else:
                # Dict format (for testing)
                params = request.get('parameters', {})
                request_id = request.get('request_id', 'unknown')
            
            # Support both parameter formats: (action, quantity) and (side, amount)
            action = params.get("action") or params.get("side")
            quantity = params.get("quantity") or params.get("amount")

            result = self.trading_adapter.execute_order(
                symbol=params["symbol"],
                action=action,
                quantity=quantity,
                price=params.get("price"),
            )

            # Check if adapter returned an error
            if isinstance(result, dict) and not result.get('success', True):
                error_info = result.get('error', {})
                error_type = error_info.get('type', 'unknown_error')
                error_message = error_info.get('message', 'Order execution failed')
                return self.message_handler.create_error_response(
                    request_id=request_id,
                    error_message=f"Order execution failed: {error_message} ({error_type})"
                )

            return self.message_handler.create_response(
                request_id=request_id, data=result
            )

        except Exception as e:
            # Handle both ServiceRequest object and dict
            if hasattr(request, 'request_id'):
                request_id = request.request_id
            else:
                request_id = request.get('request_id', 'unknown')
                
            return self.message_handler.create_error_response(
                request_id=request_id,
                error_message=f"Order execution failed: {str(e)} (internal_error)",
            )

    def _handle_evaluate_risk(self, request) -> ServiceResponse:
        """Handle risk evaluation request.
        - Normalize request parameters to the adapter contract (params dict)
        - Backward compatibility: map 'market_conditions' to 'market_data'
        """
        try:
            # Handle both ServiceRequest object and dict
            if hasattr(request, 'params'):
                # ServiceRequest object
                params = request.params
                request_id = request.request_id
            else:
                # Dict format (for testing)
                params = request.get('parameters', {})
                request_id = request.get('request_id', 'unknown')

            # Normalize inputs to adapter's contract
            # Adapter expects a single params dict with keys: portfolio, market_data, risk_tolerance
            portfolio = params.get("portfolio", {})

            # Prefer explicit fields, then fall back to legacy nesting under proposed_trade
            risk_tolerance = params.get("risk_tolerance")
            if risk_tolerance is None:
                risk_tolerance = params.get("proposed_trade", {}).get("risk_tolerance", "moderate")

            market_data = params.get("market_data")
            if market_data is None:
                # Backward compatibility: some clients use 'market_conditions'
                market_data = params.get("market_conditions")
            if market_data is None:
                # Legacy nesting inside proposed_trade
                market_data = params.get("proposed_trade", {}).get("market_conditions", {})

            adapter_params = {
                "portfolio": portfolio,
                "market_data": market_data if isinstance(market_data, dict) else {},
                "risk_tolerance": risk_tolerance,
            }

            result = self.trading_adapter.evaluate_risk(adapter_params)

            # Check if adapter returned an error
            if isinstance(result, dict) and not result.get('success', True):
                error_info = result.get('error', {})
                error_type = error_info.get('type', 'unknown_error')
                error_message = error_info.get('message', 'Risk evaluation failed')
                return self.message_handler.create_error_response(
                    request_id=request_id,
                    error_message=f"Risk evaluation failed: {error_message} ({error_type})"
                )

            return self.message_handler.create_response(
                request_id=request_id, data=result
            )

        except Exception as e:
            # Handle both ServiceRequest object and dict
            if hasattr(request, 'request_id'):
                request_id = request.request_id
            else:
                request_id = request.get('request_id', 'unknown')

            return self.message_handler.create_error_response(
                request_id=request_id,
                error_message=f"Risk evaluation failed: {str(e)} (internal_error)",
            )

    def _handle_analyze_stock(self, request) -> ServiceResponse:
        """Handle stock analysis request."""
        try:
            # Handle both ServiceRequest object and dict
            if hasattr(request, 'params'):
                # ServiceRequest object
                params = request.params
                request_id = request.request_id
            else:
                # Dict format (for testing)
                params = request.get('parameters', {})
                request_id = request.get('request_id', 'unknown')
            
            result = self.trading_adapter.analyze_stock(
                symbol=params["symbol"],
                analysis_type=params.get("analysis_type", "comprehensive"),
            )

            return self.message_handler.create_response(
                request_id=request_id, data=result
            )

        except Exception as e:
            # Handle both ServiceRequest object and dict
            if hasattr(request, 'request_id'):
                request_id = request.request_id
            else:
                request_id = request.get('request_id', 'unknown')
                
            return self.message_handler.create_error_response(
                request_id=request_id,
                error_message=f"Stock analysis failed: {str(e)} (internal_error)",
            )

    def _handle_get_market_data(self, request) -> ServiceResponse:
        """Handle market data request."""
        try:
            # Handle both ServiceRequest object and dict
            if hasattr(request, 'params'):
                # ServiceRequest object
                params = request.params
                request_id = request.request_id
            else:
                # Dict format (for testing)
                params = request.get('parameters', {})
                request_id = request.get('request_id', 'unknown')
            
            result = self.trading_adapter.get_market_data(
                symbols=params["symbols"],
                data_type=params.get("data_type", "realtime"),
            )

            return self.message_handler.create_response(
                request_id=request_id, data=result
            )

        except Exception as e:
            # Handle both ServiceRequest object and dict
            if hasattr(request, 'request_id'):
                request_id = request.request_id
            else:
                request_id = request.get('request_id', 'unknown')
                
            return self.message_handler.create_error_response(
                request_id=request_id,
                error_message=f"Market data retrieval failed: {str(e)} (internal_error)",
            )

    def _register_with_load_balancer(self):
        """Register this worker with the load balancer."""
        try:
            # Send a registration message
            registration_msg = {
                "type": "register",
                "worker_id": self.worker_id,
                "timestamp": time.time(),
            }

            # Send registration as a special message
            # Format: [empty, REGISTER, registration_data] - worker identity is added automatically by DEALER
            self.socket.send_multipart(
                [b"", b"REGISTER", json.dumps(registration_msg).encode("utf-8")]
            )

            self.logger.info(
                f"Worker {self.worker_id} registration sent to load balancer"
            )

        except Exception as e:
            self.logger.error(f"Failed to register worker {self.worker_id}: {e}")

    def _send_response(self, response):
        """Send response back to client."""
        try:
            if hasattr(response, 'to_dict'):
                # ServiceResponse object
                response_data = response.to_dict()
            else:
                # Dict format
                response_data = response
            
            # Send response through ZMQ socket
            self.socket.send_multipart([
                b"",  # Empty frame for DEALER socket
                json.dumps(response_data).encode('utf-8')
            ])
            
        except Exception as e:
            self.logger.error(f"Failed to send response: {e}")
    
    def _update_status(self, status, **kwargs):
        """Update worker status."""
        try:
            # Update processed_requests if provided
            if 'processed_requests' in kwargs:
                self.processed_requests = kwargs['processed_requests']
            
            # Get current system metrics
            self._get_system_metrics()
            
            self.db_manager.update_worker_status(
                worker_id=self.worker_id,
                status=status,
                processed_requests=self.processed_requests,
                cpu_usage=self.cpu_usage,
                memory_usage=self.memory_usage
            )
        except Exception as e:
            self.logger.error(f"Failed to update worker status: {e}")
    
    def _get_system_metrics(self):
        """Get system metrics for monitoring."""
        try:
            import psutil
            self.cpu_usage = psutil.cpu_percent()
            memory_info = psutil.virtual_memory()
            self.memory_usage = memory_info.used / (1024 * 1024)  # Convert to MB
            
            return {
                "cpu_percent": self.cpu_usage,
                "memory_percent": memory_info.percent,
                "processed_requests": self.processed_requests,
                "worker_id": self.worker_id,
                "status": "active" if self.running else "stopped"
            }
        except ImportError:
            # Fallback if psutil is not available
            return {
                "processed_requests": self.processed_requests,
                "worker_id": self.worker_id,
                "status": "active" if self.running else "stopped"
            }
        except Exception as e:
            self.logger.error(f"Failed to get system metrics: {e}")
            return {}
    
    def _send_response(self, response_data):
        """Send response back to client."""
        try:
            # Convert ServiceResponse to dict if needed
            if hasattr(response_data, 'to_dict'):
                response_dict = response_data.to_dict()
            else:
                response_dict = response_data
            
            # Send response via socket (DEALER) as two frames: [empty, response_json]
            # ROUTER (LB backend) will prepend worker_identity -> total 3 frames
            response_json = json.dumps(response_dict)
            self.socket.send_multipart([
                b"",  # Empty delimiter frame for DEALER patterns
                response_json.encode('utf-8')
            ])
            
        except Exception as e:
            self.logger.error(f"Failed to send response: {e}")
    
    def _process_message(self, message_data):
        """Process raw message data (for testing compatibility)."""
        try:
            # Parse JSON message
            try:
                if isinstance(message_data, bytes):
                    message_str = message_data.decode('utf-8')
                else:
                    message_str = str(message_data)
                
                message_dict = json.loads(message_str)
            except json.JSONDecodeError as e:
                error_response = {
                    'status': 'error',
                    'error': f'json_parse_error: {str(e)}',
                    'request_id': 'unknown',
                    'timestamp': time.time()
                }
                self._send_response(error_response)
                return
            
            # Validate required fields
            required_fields = ['method', 'request_id']
            missing_fields = [field for field in required_fields if field not in message_dict]
            
            if missing_fields:
                error_response = {
                    'status': 'error',
                    'error': f'missing_field: {", ".join(missing_fields)}',
                    'request_id': message_dict.get('request_id', 'unknown'),
                    'timestamp': time.time()
                }
                self._send_response(error_response)
                return
            
            # Log request
            self.db_manager.log_request(
                request_id=message_dict['request_id'],
                method=message_dict['method'],
                request_data=message_dict.get('parameters', {}),
                client_id=message_dict.get('client_id', 'unknown'),
                worker_id=self.worker_id
            )
            
            # Process the request
            start_time = time.time()
            
            method = message_dict['method']
            if method == 'health.check':
                response = self._handle_health_check(message_dict)
            elif method == 'scan.market':
                response = self._handle_scan_market(message_dict)
            elif method == 'execute.order':
                response = self._handle_execute_order(message_dict)
            elif method == 'evaluate.risk':
                response = self._handle_evaluate_risk(message_dict)
            elif method == 'analyze.stock':
                response = self._handle_analyze_stock(message_dict)
            elif method == 'get.market_data':
                response = self._handle_get_market_data(message_dict)
            else:
                response = {
                    'status': 'error',
                    'error': f'unknown_method: {method}',
                    'request_id': message_dict['request_id'],
                    'timestamp': time.time()
                }
            
            # Calculate processing time
            processing_time_ms = int((time.time() - start_time) * 1000)
            
            # Ensure response has required fields
            if isinstance(response, dict):
                response['processing_time_ms'] = processing_time_ms
                if 'timestamp' not in response:
                    response['timestamp'] = time.time()
            
            # Log response
            self.db_manager.log_response(
                request_id=message_dict['request_id'],
                response_data=response if isinstance(response, dict) else response.data or {},
                processing_time_ms=processing_time_ms,
                status=response.get('status', 'unknown') if isinstance(response, dict) else response.status
            )
            
            # Send response (testing path). We don't have raw client_id bytes here, so use DEALER 2-frame.
            self._send_response(response)
            
            # Update statistics
            self.processed_requests += 1
            
        except Exception as e:
            self.logger.error(f"Error processing message: {e}")
            error_response = {
                'status': 'error',
                'error': f'internal_error: {str(e)}',
                'request_id': 'unknown',
                'timestamp': time.time()
            }
            self._send_response(error_response)

    def _heartbeat_loop(self):
        """Send periodic heartbeats to maintain worker status."""
        while self.running:
            try:
                self.last_heartbeat = time.time()

                # Update worker status in database
                self.db_manager.update_worker_status(
                    worker_id=self.worker_id,
                    status="idle" if self.processed_requests == 0 else "active",
                    processed_requests=self.processed_requests,
                )

                # Send heartbeat to load balancer
                heartbeat_msg = {
                    "type": "heartbeat",
                    "worker_id": self.worker_id,
                    "worker_id": self.worker_id,
                    "timestamp": time.time(),
                    "processed_requests": self.processed_requests,
                }

                try:
                    # Send heartbeat as a special message
                    # Format: [empty, HEARTBEAT, heartbeat_data] - worker identity is added automatically by DEALER
                    self.socket.send_multipart(
                        [b"", b"HEARTBEAT", json.dumps(heartbeat_msg).encode("utf-8")]
                    )
                except Exception as hb_error:
                    self.logger.warning(f"Failed to send heartbeat: {hb_error}")

                time.sleep(self.settings.health_check_interval)

            except Exception as e:
                self.logger.error(
                    f"Error in heartbeat loop for worker {self.worker_id}: {e}"
                )


if __name__ == "__main__":
    # Allow running worker as standalone process
    import sys
    import signal

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    worker_id = sys.argv[1] if len(sys.argv) > 1 else None
    worker = Worker(worker_id)

    def signal_handler(signum, frame):
        print(f"\nReceived signal {signum}, stopping worker...")
        worker.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        worker.start()
    except KeyboardInterrupt:
        worker.stop()
