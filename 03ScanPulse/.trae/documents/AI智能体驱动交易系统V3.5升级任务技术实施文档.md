# AI智能体驱动交易系统 V3.5 升级任务技术实施文档

## 第一部分：任务规划摘要

根据SOURCE\_DOCUMENT的要求，本次升级任务将执行以下核心步骤：

### 升级目标

将分散在各个模组中的TradingAgents-CN实现统一为一个中央AI引擎服务（TACoreService），实现系统的服务化重构。

### 执行步骤

1. **创建新的核心服务 12TACoreService**

   * 在项目根目录创建 `12TACoreService` 文件夹

   * 设计并实现统一的TradingAgents-CN适配器

   * 通过ZeroMQ REP套接字提供标准化服务

   * 编写独立的Dockerfile和配置文件

2. **为所有依赖模组执行统一升级套件**

   * 清理旧代码：删除本地TradingAgents-CN相关文件

   * 更新配置：移除本地适配器配置项

   * 重构调用逻辑：将本地函数调用改为ZeroMQ服务请求

   * 验证功能：确保模组通过新方式正确获取服务

3. **最终系统集成与编排**

   * 创建包含全部12个模组的docker-compose.yml

   * 设置正确的服务依赖关系

   * 一键启动整个系统

4. **升级后全链路回归测试**

   * 执行端到端测试和性能压力测试

   * 验证数据链路完整性

   * 检查接口响应和客户端处理

   * 对比重构前后性能

## 第二部分：核心服务 (12TACoreService) 代码生成

### 1. 主服务文件 - main.py

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TACoreService - 统一的TradingAgents-CN核心服务
负载均衡代理，为所有模组提供统一的AI交易代理服务
"""

import zmq
import json
import threading
import time
import logging
from typing import Dict, Any, List
from datetime import datetime
from multiprocessing import Process, Queue
import signal
import sys

from worker import TradingAgentWorker

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TACoreService:
    """TradingAgents-CN核心服务主类"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.context = None
        self.socket = None
        self.workers = []
        self.worker_queue = Queue()
        self.is_running = False
        
        # 服务配置
        self.bind_address = config.get('bind_address', 'tcp://*:5555')
        self.worker_count = config.get('worker_count', 4)
        self.max_queue_size = config.get('max_queue_size', 100)
        
        # 统计信息
        self.stats = {
            'requests_total': 0,
            'requests_success': 0,
            'requests_failed': 0,
            'start_time': None
        }
        
        logger.info(f"TACoreService initialized with {self.worker_count} workers")
    
    def start(self):
        """启动核心服务"""
        try:
            # 初始化ZMQ上下文和套接字
            self.context = zmq.Context()
            self.socket = self.context.socket(zmq.REP)
            self.socket.bind(self.bind_address)
            
            # 启动工作进程
            self._start_workers()
            
            # 设置信号处理
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)
            
            self.is_running = True
            self.stats['start_time'] = datetime.now().isoformat()
            
            logger.info(f"TACoreService started on {self.bind_address}")
            
            # 主循环
            self._main_loop()
            
        except Exception as e:
            logger.error(f"Failed to start TACoreService: {e}")
            self.stop()
    
    def _start_workers(self):
        """启动工作进程池"""
        for i in range(self.worker_count):
            worker = TradingAgentWorker(f"worker-{i}", self.worker_queue)
            process = Process(target=worker.run)
            process.start()
            self.workers.append(process)
            logger.info(f"Started worker process {i}")
    
    def _main_loop(self):
        """主循环处理请求"""
        while self.is_running:
            try:
                # 接收请求
                message = self.socket.recv_json(zmq.NOBLOCK)
                self.stats['requests_total'] += 1
                
                logger.debug(f"Received request: {message.get('method', 'unknown')}")
                
                # 处理请求
                response = self._process_request(message)
                
                # 发送响应
                self.socket.send_json(response)
                
                if response.get('status') == 'success':
                    self.stats['requests_success'] += 1
                else:
                    self.stats['requests_failed'] += 1
                    
            except zmq.Again:
                # 无消息，继续循环
                time.sleep(0.01)
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                error_response = {
                    'status': 'error',
                    'message': str(e),
                    'timestamp': datetime.now().isoformat()
                }
                try:
                    self.socket.send_json(error_response)
                except:
                    pass
                self.stats['requests_failed'] += 1
    
    def _process_request(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """处理单个请求"""
        try:
            method = message.get('method')
            params = message.get('params', {})
            request_id = message.get('request_id')
            
            if not method:
                return {
                    'status': 'error',
                    'message': 'Missing method parameter',
                    'request_id': request_id,
                    'timestamp': datetime.now().isoformat()
                }
            
            # 根据方法路由请求
            if method == 'scan.market':
                result = self._handle_scan_market(params)
            elif method == 'analyze.symbol':
                result = self._handle_analyze_symbol(params)
            elif method == 'get.market_data':
                result = self._handle_get_market_data(params)
            elif method == 'health.check':
                result = self._handle_health_check()
            else:
                return {
                    'status': 'error',
                    'message': f'Unknown method: {method}',
                    'request_id': request_id,
                    'timestamp': datetime.now().isoformat()
                }
            
            return {
                'status': 'success',
                'result': result,
                'request_id': request_id,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error processing request: {e}")
            return {
                'status': 'error',
                'message': str(e),
                'request_id': message.get('request_id'),
                'timestamp': datetime.now().isoformat()
            }
    
    def _handle_scan_market(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """处理市场扫描请求"""
        symbols = params.get('symbols', [])
        scan_type = params.get('scan_type', 'basic')
        
        # 这里应该调用实际的TradingAgents-CN扫描逻辑
        # 目前返回模拟数据
        results = []
        for symbol in symbols:
            results.append({
                'symbol': symbol,
                'score': 0.75,
                'signals': ['volume_spike', 'price_momentum'],
                'timestamp': datetime.now().isoformat()
            })
        
        return {
            'scan_results': results,
            'total_scanned': len(symbols),
            'scan_type': scan_type
        }
    
    def _handle_analyze_symbol(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """处理单个交易对分析请求"""
        symbol = params.get('symbol')
        analysis_type = params.get('analysis_type', 'comprehensive')
        
        if not symbol:
            raise ValueError("Symbol parameter is required")
        
        # 模拟分析结果
        return {
            'symbol': symbol,
            'analysis': {
                'trend': 'bullish',
                'strength': 0.8,
                'support_levels': [45000, 44000],
                'resistance_levels': [48000, 50000],
                'recommendation': 'buy'
            },
            'analysis_type': analysis_type
        }
    
    def _handle_get_market_data(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """处理市场数据获取请求"""
        symbol = params.get('symbol')
        timeframe = params.get('timeframe', '1h')
        
        if not symbol:
            raise ValueError("Symbol parameter is required")
        
        # 模拟市场数据
        return {
            'symbol': symbol,
            'timeframe': timeframe,
            'data': {
                'price': 47500.0,
                'volume': 1250000,
                'change_24h': 2.5,
                'high_24h': 48000,
                'low_24h': 46000
            }
        }
    
    def _handle_health_check(self) -> Dict[str, Any]:
        """处理健康检查请求"""
        uptime = 0
        if self.stats['start_time']:
            start_time = datetime.fromisoformat(self.stats['start_time'])
            uptime = (datetime.now() - start_time).total_seconds()
        
        return {
            'status': 'healthy',
            'uptime_seconds': uptime,
            'worker_count': len(self.workers),
            'stats': self.stats.copy()
        }
    
    def _signal_handler(self, signum, frame):
        """信号处理器"""
        logger.info(f"Received signal {signum}, shutting down...")
        self.stop()
    
    def stop(self):
        """停止服务"""
        logger.info("Stopping TACoreService...")
        self.is_running = False
        
        # 停止工作进程
        for worker in self.workers:
            worker.terminate()
            worker.join(timeout=5)
        
        # 关闭ZMQ资源
        if self.socket:
            self.socket.close()
        if self.context:
            self.context.term()
        
        logger.info("TACoreService stopped")

def main():
    """主函数"""
    config = {
        'bind_address': 'tcp://*:5555',
        'worker_count': 4,
        'max_queue_size': 100
    }
    
    service = TACoreService(config)
    service.start()

if __name__ == '__main__':
    main()
```

### 2. 工作进程骨架 - worker.py

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TradingAgent Worker Process
工作进程骨架，处理具体的TradingAgents-CN业务逻辑
"""

import time
import logging
from typing import Dict, Any
from multiprocessing import Queue
from datetime import datetime

logger = logging.getLogger(__name__)

class TradingAgentWorker:
    """TradingAgent工作进程"""
    
    def __init__(self, worker_id: str, task_queue: Queue):
        self.worker_id = worker_id
        self.task_queue = task_queue
        self.is_running = False
        
        # 这里应该初始化实际的TradingAgents-CN组件
        # self.trading_agent = TradingAgentsCN(config)
        
        logger.info(f"Worker {worker_id} initialized")
    
    def run(self):
        """工作进程主循环"""
        self.is_running = True
        logger.info(f"Worker {self.worker_id} started")
        
        while self.is_running:
            try:
                # 从队列获取任务
                if not self.task_queue.empty():
                    task = self.task_queue.get(timeout=1)
                    result = self._process_task(task)
                    # 这里应该将结果返回给主进程
                    logger.debug(f"Worker {self.worker_id} completed task")
                else:
                    time.sleep(0.1)
                    
            except Exception as e:
                logger.error(f"Worker {self.worker_id} error: {e}")
                time.sleep(1)
        
        logger.info(f"Worker {self.worker_id} stopped")
    
    def _process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """处理具体任务"""
        method = task.get('method')
        params = task.get('params', {})
        
        # 根据方法执行相应的TradingAgents-CN逻辑
        if method == 'scan.market':
            return self._scan_market(params)
        elif method == 'analyze.symbol':
            return self._analyze_symbol(params)
        elif method == 'get.market_data':
            return self._get_market_data(params)
        else:
            raise ValueError(f"Unknown method: {method}")
    
    def _scan_market(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """执行市场扫描"""
        # 这里应该调用实际的TradingAgents-CN扫描逻辑
        symbols = params.get('symbols', [])
        
        # 模拟扫描处理
        time.sleep(0.1)  # 模拟处理时间
        
        results = []
        for symbol in symbols:
            results.append({
                'symbol': symbol,
                'score': 0.75,
                'worker_id': self.worker_id,
                'processed_at': datetime.now().isoformat()
            })
        
        return {'scan_results': results}
    
    def _analyze_symbol(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """分析单个交易对"""
        symbol = params.get('symbol')
        
        # 模拟分析处理
        time.sleep(0.05)
        
        return {
            'symbol': symbol,
            'analysis': {
                'trend': 'bullish',
                'confidence': 0.8
            },
            'worker_id': self.worker_id
        }
    
    def _get_market_data(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """获取市场数据"""
        symbol = params.get('symbol')
        
        # 模拟数据获取
        return {
            'symbol': symbol,
            'price': 47500.0,
            'volume': 1250000,
            'worker_id': self.worker_id
        }
    
    def stop(self):
        """停止工作进程"""
        self.is_running = False
```

### 3. Docker配置 - Dockerfile

```dockerfile
# TACoreService Dockerfile
# 统一的TradingAgents-CN核心服务容器

FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libzmq3-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY main.py .
COPY worker.py .
COPY config/ ./config/

# 创建日志目录
RUN mkdir -p /app/logs

# 创建非root用户
RUN groupadd -r tacore && useradd -r -g tacore tacore
RUN chown -R tacore:tacore /app
USER tacore

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import zmq; ctx=zmq.Context(); sock=ctx.socket(zmq.REQ); sock.connect('tcp://localhost:5555'); sock.send_json({'method':'health.check'}); resp=sock.recv_json(); exit(0 if resp.get('status')=='success' else 1)"

# 暴露端口
EXPOSE 5555

# 启动命令
CMD ["python", "main.py"]
```

## 第三部分：依赖模组重构示例

### 重构说明

以 **03ScanPulse (扫描器)** 模组为例，重构的核心是将本地TradingAgents-CN调用改为对TACoreService的ZeroMQ客户端请求。目标方法是 `scan.market`。

### 重构后的扫描器客户端 - scanner\_client.py

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
扫描器客户端 - 重构后版本
通过ZeroMQ连接到TACoreService获取扫描服务
"""

import zmq
import json
import uuid
import time
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class ScannerClient:
    """扫描器ZeroMQ客户端"""
    
    def __init__(self, service_address: str = "tcp://tacore_service:5555"):
        self.service_address = service_address
        self.context = None
        self.socket = None
        self.is_connected = False
        
        # 连接配置
        self.timeout = 30000  # 30秒超时
        self.max_retries = 3
        
        logger.info(f"ScannerClient initialized for {service_address}")
    
    def connect(self) -> bool:
        """连接到TACoreService"""
        try:
            if self.is_connected:
                return True
            
            self.context = zmq.Context()
            self.socket = self.context.socket(zmq.REQ)
            self.socket.setsockopt(zmq.RCVTIMEO, self.timeout)
            self.socket.setsockopt(zmq.SNDTIMEO, self.timeout)
            self.socket.connect(self.service_address)
            
            # 测试连接
            health_check = self._send_request("health.check", {})
            if health_check and health_check.get('status') == 'success':
                self.is_connected = True
                logger.info("Successfully connected to TACoreService")
                return True
            else:
                logger.error("Health check failed")
                return False
                
        except Exception as e:
            logger.error(f"Failed to connect to TACoreService: {e}")
            self.disconnect()
            return False
    
    def disconnect(self):
        """断开连接"""
        self.is_connected = False
        
        if self.socket:
            self.socket.close()
            self.socket = None
        
        if self.context:
            self.context.term()
            self.context = None
        
        logger.info("Disconnected from TACoreService")
    
    def scan_market(self, symbols: List[str], scan_type: str = "basic") -> Optional[Dict[str, Any]]:
        """扫描市场 - 核心重构方法
        
        Args:
            symbols: 要扫描的交易对列表
            scan_type: 扫描类型
            
        Returns:
            扫描结果字典
        """
        if not self.is_connected:
            if not self.connect():
                logger.error("Cannot scan market: not connected to service")
                return None
        
        params = {
            "symbols": symbols,
            "scan_type": scan_type
        }
        
        logger.info(f"Scanning {len(symbols)} symbols with type '{scan_type}'")
        
        result = self._send_request("scan.market", params)
        
        if result and result.get('status') == 'success':
            scan_data = result.get('result', {})
            logger.info(f"Scan completed: {scan_data.get('total_scanned', 0)} symbols processed")
            return scan_data
        else:
            logger.error(f"Scan failed: {result.get('message', 'Unknown error') if result else 'No response'}")
            return None
    
    def analyze_symbol(self, symbol: str, analysis_type: str = "comprehensive") -> Optional[Dict[str, Any]]:
        """分析单个交易对
        
        Args:
            symbol: 交易对符号
            analysis_type: 分析类型
            
        Returns:
            分析结果字典
        """
        if not self.is_connected:
            if not self.connect():
                return None
        
        params = {
            "symbol": symbol,
            "analysis_type": analysis_type
        }
        
        result = self._send_request("analyze.symbol", params)
        
        if result and result.get('status') == 'success':
            return result.get('result', {})
        else:
            logger.error(f"Analysis failed for {symbol}: {result.get('message', 'Unknown error') if result else 'No response'}")
            return None
    
    def get_market_data(self, symbol: str, timeframe: str = "1h") -> Optional[Dict[str, Any]]:
        """获取市场数据
        
        Args:
            symbol: 交易对符号
            timeframe: 时间框架
            
        Returns:
            市场数据字典
        """
        if not self.is_connected:
            if not self.connect():
                return None
        
        params = {
            "symbol": symbol,
            "timeframe": timeframe
        }
        
        result = self._send_request("get.market_data", params)
        
        if result and result.get('status') == 'success':
            return result.get('result', {})
        else:
            logger.error(f"Failed to get market data for {symbol}")
            return None
    
    def _send_request(self, method: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """发送请求到TACoreService
        
        Args:
            method: 请求方法
            params: 请求参数
            
        Returns:
            响应字典
        """
        request = {
            "method": method,
            "params": params,
            "request_id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat()
        }
        
        for attempt in range(self.max_retries):
            try:
                # 发送请求
                self.socket.send_json(request)
                
                # 接收响应
                response = self.socket.recv_json()
                
                logger.debug(f"Request {method} completed in attempt {attempt + 1}")
                return response
                
            except zmq.Again:
                logger.warning(f"Request {method} timeout on attempt {attempt + 1}")
                if attempt < self.max_retries - 1:
                    # 重新创建socket以避免状态问题
                    self._recreate_socket()
                    time.sleep(1)
                else:
                    logger.error(f"Request {method} failed after {self.max_retries} attempts")
                    
            except Exception as e:
                logger.error(f"Request {method} error on attempt {attempt + 1}: {e}")
                if attempt < self.max_retries - 1:
                    self._recreate_socket()
                    time.sleep(1)
        
        return None
    
    def _recreate_socket(self):
        """重新创建socket连接"""
        try:
            if self.socket:
                self.socket.close()
            
            self.socket = self.context.socket(zmq.REQ)
            self.socket.setsockopt(zmq.RCVTIMEO, self.timeout)
            self.socket.setsockopt(zmq.SNDTIMEO, self.timeout)
            self.socket.connect(self.service_address)
            
        except Exception as e:
            logger.error(f"Failed to recreate socket: {e}")
            self.is_connected = False

# 使用示例
class ScannerModule:
    """重构后的扫描器模块"""
    
    def __init__(self):
        self.client = ScannerClient()
        
    def start_scanning(self):
        """开始扫描流程"""
        if not self.client.connect():
            logger.error("Failed to connect to TACoreService")
            return
        
        # 获取要扫描的交易对列表
        symbols = ["BTCUSDT", "ETHUSDT", "ADAUSDT", "DOTUSDT"]
        
        # 执行市场扫描
        scan_results = self.client.scan_market(symbols, "comprehensive")
        
        if scan_results:
            logger.info(f"Scan completed successfully: {scan_results}")
            
            # 处理扫描结果
            for result in scan_results.get('scan_results', []):
                symbol = result.get('symbol')
                score = result.get('score', 0)
                
                if score > 0.7:  # 高分交易对
                    # 进行详细分析
                    analysis = self.client.analyze_symbol(symbol)
                    if analysis:
                        logger.info(f"Analysis for {symbol}: {analysis}")
        else:
            logger.error("Scan failed")
        
        self.client.disconnect()

if __name__ == "__main__":
    # 测试代码
    scanner = ScannerModule()
    scanner.start_scanning()
```

## 第四部分：最终系统集成文件

### 完整的 docker-compose.yml

```yaml
# AI智能体驱动交易系统 V3.5 - 完整系统编排
# 包含所有12个模组的统一部署配置

version: '3.8'

services:
  # ===================================================================
  # 核心服务层
  # ===================================================================
  
  # TradingAgents-CN 核心服务
  tacore_service:
    build:
      context: ./12TACoreService
      dockerfile: Dockerfile
    container_name: tacore_service
    restart: unless-stopped
    ports:
      - "5555:5555"
    volumes:
      - ./logs/tacore:/app/logs
    environment:
      - SERVICE_ENV=production
      - BIND_ADDRESS=tcp://*:5555
      - WORKER_COUNT=4
    networks:
      - trading_network
    healthcheck:
      test: ["CMD", "python", "-c", "import zmq; ctx=zmq.Context(); sock=ctx.socket(zmq.REQ); sock.connect('tcp://localhost:5555'); sock.send_json({'method':'health.check'}); resp=sock.recv_json(); exit(0 if resp.get('status')=='success' else 1)"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 30s

  # Redis 缓存服务
  redis:
    image: redis:7-alpine
    container_name: trading_redis
    restart: unless-stopped
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
      - ./docker/redis.conf:/usr/local/etc/redis/redis.conf
    command: redis-server /usr/local/etc/redis/redis.conf
    networks:
      - trading_network
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 3

  # ===================================================================
  # 业务模组层 (11个模组)
  # ===================================================================

  # 01. API工厂模组
  api_factory:
    build:
      context: ./01APIFactory
      dockerfile: Dockerfile
    container_name: api_factory
    restart: unless-stopped
    ports:
      - "8001:8000"
    volumes:
      - ./logs/api_factory:/app/logs
    environment:
      - MODULE_ENV=production
      - TACORE_SERVICE_URL=tcp://tacore_service:5555
      - REDIS_URL=redis://redis:6379
    depends_on:
      tacore_service:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - trading_network

  # 02. 爬虫模组
  crawler:
    build:
      context: ./02Crawler
      dockerfile: Dockerfile
    container_name: crawler
    restart: unless-stopped
    ports:
      - "8002:8000"
    volumes:
      - ./logs/crawler:/app/logs
    environment:
      - MODULE_ENV=production
      - TACORE_SERVICE_URL=tcp://tacore_service:5555
      - REDIS_URL=redis://redis:6379
    depends_on:
      tacore_service:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - trading_network

  # 03. 扫描器模组
  scanner:
    build:
      context: ./03ScanPulse
      dockerfile: Dockerfile
    container_name: scanner
    restart: unless-stopped
    ports:
      - "8003:8000"
      - "5556:5556"  # ZMQ Publisher
      - "5557:5557"  # ZMQ Subscriber
    volumes:
      - ./logs/scanner:/app/logs
    environment:
      - MODULE_ENV=production
      - TACORE_SERVICE_URL=tcp://tacore_service:5555
      - REDIS_URL=redis://redis:6379
    depends_on:
      tacore_service:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - trading_network

  # 04. 交易员模组
  trader:
    build:
      context: ./04TraderBot
      dockerfile: Dockerfile
    container_name: trader
    restart: unless-stopped
    ports:
      - "8004:8000"
    volumes:
      - ./logs/trader:/app/logs
    environment:
      - MODULE_ENV=production
      - TACORE_SERVICE_URL=tcp://tacore_service:5555
      - REDIS_URL=redis://redis:6379
    depends_on:
      tacore_service:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - trading_network

  # 05. 风控模组
  risk_manager:
    build:
      context: ./05RiskGuard
      dockerfile: Dockerfile
    container_name: risk_manager
    restart: unless-stopped
    ports:
      - "8005:8000"
    volumes:
      - ./logs/risk_manager:/app/logs
    environment:
      - MODULE_ENV=production
      - TACORE_SERVICE_URL=tcp://tacore_service:5555
      - REDIS_URL=redis://redis:6379
    depends_on:
      tacore_service:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - trading_network

  # 06. 投资组合模组
  portfolio:
    build:
      context: ./06PortfolioSync
      dockerfile: Dockerfile
    container_name: portfolio
    restart: unless-stopped
    ports:
      - "8006:8000"
    volumes:
      - ./logs/portfolio:/app/logs
    environment:
      - MODULE_ENV=production
      - TACORE_SERVICE_URL=tcp://tacore_service:5555
      - REDIS_URL=redis://redis:6379
    depends_on:
      tacore_service:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - trading_network

  # 07. 通知模组
  notifier:
    build:
      context: ./07NotifyHub
      dockerfile: Dockerfile
    container_name: notifier
    restart: unless-stopped
    ports:
      - "8007:8000"
    volumes:
      - ./logs/notifier:/app/logs
    environment:
      - MODULE_ENV=production
      - TACORE_SERVICE_URL=tcp://tacore_service:5555
      - REDIS_URL=redis://redis:6379
    depends_on:
      tacore_service:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - trading_network

  # 08. 数据分析模组
  analytics:
    build:
      context: ./08DataLens
      dockerfile: Dockerfile
    container_name: analytics
    restart: unless-stopped
    ports:
      - "8008:8000"
    volumes:
      - ./logs/analytics:/app/logs
    environment:
      - MODULE_ENV=production
      - TACORE_SERVICE_URL=tcp://tacore_service:5555
      - REDIS_URL=redis://redis:6379
    depends_on:
      tacore_service:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - trading_network

  # 09. 回测模组
  backtester:
    build:
      context: ./09BacktestLab
      dockerfile: Dockerfile
    container_name: backtester
    restart: unless-stopped
    ports:
      - "8009:8000"
    volumes:
      - ./logs/backtester:/app/logs
    environment:
      - MODULE_ENV=production
      - TACORE_SERVICE_URL=tcp://tacore_service:5555
      - REDIS_URL=redis://redis:6379
    depends_on:
      tacore_service:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - trading_network

  # 10. 用户界面模组
  web_ui:
    build:
      context: ./10WebPortal
      dockerfile: Dockerfile
    container_name: web_ui
    restart: unless-stopped
    ports:
      - "3000:3000"
    volumes:
      - ./logs/web_ui:/app/logs
    environment:
      - MODULE_ENV=production
      - API_BASE_URL=http://api_factory:8000
      - REDIS_URL=redis://redis:6379
    depends_on:
      - api_factory
      - redis
    networks:
      - trading_network

  # 11. 监控模组
  monitor:
    build:
      context: ./11MonitorEye
      dockerfile: Dockerfile
    container_name: monitor
    restart: unless-stopped
    ports:
      - "8011:8000"
      - "9090:9090"  # Prometheus
    volumes:
      - ./logs/monitor:/app/logs
      - prometheus_data:/prometheus
    environment:
      - MODULE_ENV=production
      - TACORE_SERVICE_URL=tcp://tacore_service:5555
      - REDIS_URL=redis://redis:6379
    depends_on:
      tacore_service:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - trading_network

# ===================================================================
# 网络和存储配置
# ===================================================================

networks:
  trading_network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.30.0.0/16

volumes:
  redis_data:
    driver: local
  prometheus_data:
    driver: local
```

## 第五部分：升级后回归测试清单

### 系统升级后回归测试清单

#### 测试环境准备

* [ ] 确认所有12个服务容器正常启动

* [ ] 验证TACoreService健康检查通过

* [ ] 确认Redis缓存服务可用

* [ ] 检查所有服务间网络连通性

#### 1. 数据链路测试

**目标**: 追踪一笔交易从"扫描"到"执行"的完整生命周期，确保数据流没有中断

* [ ] **扫描阶段**

  * [ ] 扫描器模组能够成功连接到TACoreService

  * [ ] 扫描器能够发送scan.market请求并接收响应

  * [ ] 扫描结果正确写入Redis缓存

  * [ ] 扫描结果通过ZMQ正确发布给订阅者

* [ ] **分析阶段**

  * [ ] 交易员模组能够接收扫描器发布的机会信号

  * [ ] 交易员能够调用TACoreService进行详细分析

  * [ ] 分析结果正确返回并处理

* [ ] **执行阶段**

  * [ ] 风控模组能够接收交易请求

  * [ ] 风控检查通过后交易正确执行

  * [ ] 投资组合模组正确更新持仓信息

  * [ ] 通知模组发送执行确认

* [ ] **监控阶段**

  * [ ] 监控模组能够收集所有环节的指标

  * [ ] 数据分析模组能够生成完整的交易报告

#### 2. 接口响应测试

**目标**: 检查TACoreService的日志，确认其收到了所有请求并正确响应

* [ ] **健康检查接口**

  * [ ] health.check请求响应正常

  * [ ] 响应时间在可接受范围内(<100ms)

  * [ ] 状态信息准确反映服务状态

* [ ] **核心业务接口**

  * [ ] scan.market接口正常响应

  * [ ] analyze.symbol接口正常响应

  * [ ] get.market\_data接口正常响应

  * [ ] 所有接口错误处理正确

* [ ] **日志验证**

  * [ ] TACoreService日志记录所有请求

  * [ ] 请求ID正确追踪

  * [ ] 错误日志包含足够的调试信息

  * [ ] 统计信息准确更新

#### 3. 客户端处理测试

**目标**: 检查各个客户端模组的日志，确认它们能正确处理来自TACoreService的成功或失败的响应

* [ ] **连接管理**

  * [ ] 客户端能够正确建立ZMQ连接

  * [ ] 连接断开时能够自动重连

  * [ ] 超时处理机制正常工作

* [ ] **响应处理**

  * [ ] 成功响应正确解析和处理

  * [ ] 错误响应正确识别和处理

  * [ ] 超时情况正确处理

  * [ ] 重试机制正常工作

* [ ] **各模组客户端验证**

  * [ ] 扫描器客户端正常工作

  * [ ] 交易员客户端正常工作

  * [ ] 风控客户端正常工作

  * [ ] 其他模组客户端正常工作

#### 4. 性能测试

**目标**: 对比重构前后的性能，确认服务化没有引入不可接受的延迟

* [ ] **响应时间测试**

  * [ ] 单次请求响应时间<500ms

  * [ ] 批量请求平均响应时间可接受

  * [ ] 99%请求响应时间<2s

* [ ] **并发测试**

  * [ ] 支持至少50个并发客户端

  * [ ] 高并发下响应时间稳定

  * [ ] 无内存泄漏或资源耗尽

* [ ] **压力测试**

  * [ ] 持续负载下系统稳定运行

  * [ ] 资源使用率在合理范围内

  * [ ] 错误率低于1%

* [ ] **性能对比**

  * [ ] 与重构前性能对比

  * [ ] 延迟增加不超过20%

  * [ ] 吞吐量不低于重构前90%

#### 5. 故障恢复测试

* [ ] **服务重启测试**

  * [ ] TACoreService重启后客户端自动重连

  * [ ] 重启过程中的请求正确处理

  * [ ] 数据一致性保持

* [ ] **网络故障测试**

  * [ ] 网络中断后自动恢复

  * [ ] 部分网络故障下系统降级运行

  * [ ] 故障恢复后数据同步正确

#### 6. 安全性测试

* [ ] **访问控制**

  * [ ] 未授权请求被正确拒绝

  * [ ] 服务间通信安全

  * [ ] 敏感数据正确保护

* [ ] **输入验证**

  * [ ] 恶意输入被正确过滤

  * [ ] 参数验证正常工作

  * [ ] 注入攻击防护有效

#### 测试执行记录

| 测试项目    | 执行时间   | 测试结果   | 问题描述   | 解决方案   |
| ------- | ------ | ------ | ------ | ------ |
| 数据链路测试  | <br /> | <br /> | <br /> | <br /> |
| 接口响应测试  | <br /> | <br /> | <br /> | <br /> |
| 客户端处理测试 | <br /> | <br /> | <br /> | <br /> |
| 性能测试    | <br /> | <br /> | <br /> | <br /> |
| 故障恢复测试  | <br /> | <br /> | <br /> | <br /> |
| 安全性测试   | <br /> | <br /> | <br /> | <br /> |

#### 测试通过标准

* [ ] 所有核心功能测试通过

* [ ] 性能指标满足要求

* [ ] 无严重或高优先级缺陷

* [ ] 系统稳定性达标

* [ ] 安全性测试通过

#### 测试负责人签字

* 测试执行人: \_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_ 日期: \_\_\_\_\_\_\_\_\_

* 测试审核人: \_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_ 日期: \_\_\_\_\_\_\_\_\_

* 项目经理: \_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_ 日期: \_\_\_\_\_\_\_\_\_

***

**注意事项**:

1. 所有测试必须在staging环境完成后才能部署到生产环境
2. 发现任何问题必须立即记录并分配给相应的开发团队
3. 性能测试数据必须与重构前基线进行对比
4. 测试过程中的所有日志文件必须保存备查

