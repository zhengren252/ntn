"""Tests for Worker process functionality."""

import pytest
import json
import zmq
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# 添加项目根目录到Python路径
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tacoreservice.workers.worker import Worker
from tacoreservice.workers.tradingagents_adapter import TradingAgentsAdapter


# Module-level fixtures that can be used by all test classes
@pytest.fixture
def mock_context():
    """Mock ZMQ context."""
    context = Mock()
    socket = Mock()
    context.socket.return_value = socket
    return context, socket

@pytest.fixture
def mock_database():
    """Mock database manager."""
    db = Mock()
    db.log_request.return_value = None
    db.log_response.return_value = None
    db.update_worker_status.return_value = None
    return db


@pytest.mark.unit
class TestWorker:
    """Test Worker process functionality."""

    @pytest.fixture
    def mock_adapter(self):
        """Mock TradingAgents adapter."""
        adapter = Mock(spec=TradingAgentsAdapter)
        
        # Set up default return values
        adapter.scan_market.return_value = {
            'success': True,
            'opportunities': [
                {'symbol': 'AAPL', 'score': 85.5, 'recommendation': 'BUY'},
                {'symbol': 'MSFT', 'score': 78.2, 'recommendation': 'HOLD'}
            ],
            'summary': {
                'total_symbols': 2,
                'success_rate': 100.0,
                'market_sentiment': 'BULLISH'
            }
        }
        
        adapter.execute_order.return_value = {
            'success': True,
            'execution': {
                'order_id': 'ORD123456',
                'status': 'FILLED',
                'executed_price': 154.95,
                'executed_quantity': 100,
                'commission': 1.0
            }
        }
        
        adapter.evaluate_risk.return_value = {
            'success': True,
            'risk_assessment': {
                'risk_score': 65.0,
                'risk_level': 'MEDIUM',
                'confidence': 0.85,
                'recommendations': [
                    'Consider reducing position size',
                    'Monitor market volatility'
                ]
            }
        }
        
        return adapter

    @pytest.fixture
    def worker(self, mock_context, mock_database, mock_adapter):
        """Create Worker instance for testing."""
        context, socket = mock_context
        
        with patch('zmq.Context', return_value=context), \
             patch('tacoreservice.workers.worker.DatabaseManager', return_value=mock_database), \
             patch('tacoreservice.workers.worker.TradingAgentsAdapter', return_value=mock_adapter):
            
            worker = Worker(worker_id='test_worker_1')
            worker.socket = socket
            worker.database = mock_database
            worker.adapter = mock_adapter
            
            return worker

    def test_worker_initialization(self, worker):
        """Test worker initialization."""
        assert worker.worker_id == 'test_worker_1'
        assert worker.socket is not None
        assert worker.db_manager is not None
        assert worker.trading_adapter is not None
        assert worker.running is False

    def test_handle_scan_market_success(self, worker, mock_adapter):
        """Test successful market scan handling."""
        request_data = {
            'method': 'scan.market',
            'parameters': {
                'market_type': 'US',
                'filters': {'min_price': 100.0, 'max_price': 200.0},
                'limit': 10
            },
            'request_id': 'req_scan_123',
            'timestamp': '2024-01-01T10:00:00Z'
        }
        
        response = worker._handle_scan_market(request_data)
        response_dict = response.to_dict() if hasattr(response, 'to_dict') else response
        
        assert response_dict['status'] == 'success'
        assert 'data' in response_dict
        assert response_dict['data']['success'] is True
        assert 'opportunities' in response_dict['data']
        assert len(response_dict['data']['opportunities']) == 2
        
        # Verify adapter was called with correct parameters
        mock_adapter.scan_market.assert_called_once_with(
            market_type='US',
            symbols=None,
            filters={'min_price': 100.0, 'max_price': 200.0}
        )

    def test_handle_scan_market_failure(self, worker, mock_adapter):
        """Test market scan handling with failure."""
        # Configure adapter to return failure
        mock_adapter.scan_market.return_value = {
            'success': False,
            'error': {
                'type': 'validation_error',
                'message': 'Invalid market type'
            }
        }
        
        request_data = {
            'method': 'scan.market',
            'parameters': {'market_type': 'INVALID'},
            'request_id': 'req_scan_fail',
            'timestamp': '2024-01-01T10:00:00Z'
        }
        
        response = worker._handle_scan_market(request_data)
        response_dict = response.to_dict() if hasattr(response, 'to_dict') else response
        
        assert response_dict['status'] == 'error'
        assert 'error' in response_dict
        assert 'validation_error' in response_dict['error']

    def test_handle_execute_order_success(self, worker, mock_adapter):
        """Test successful order execution handling."""
        request_data = {
            'method': 'execute.order',
            'parameters': {
                'symbol': 'AAPL',
                'side': 'buy',
                'quantity': 100,
                'order_type': 'market'
            },
            'request_id': 'req_order_123',
            'timestamp': '2024-01-01T10:00:00Z'
        }
        
        response = worker._handle_execute_order(request_data)
        response_dict = response.to_dict() if hasattr(response, 'to_dict') else response
        
        assert response_dict['status'] == 'success'
        assert 'data' in response_dict
        assert response_dict['data']['success'] is True
        assert 'execution' in response_dict['data']
        assert response_dict['data']['execution']['order_id'] == 'ORD123456'
        
        # Verify adapter was called with correct parameters
        mock_adapter.execute_order.assert_called_once_with(
            symbol='AAPL',
            action='buy',
            quantity=100,
            price=None
        )

    def test_handle_execute_order_failure(self, worker, mock_adapter):
        """Test order execution handling with failure."""
        # Configure adapter to return failure
        mock_adapter.execute_order.return_value = {
            'success': False,
            'error': {
                'type': 'market_closed',
                'message': 'Market is currently closed'
            }
        }
        
        request_data = {
            'method': 'execute.order',
            'parameters': {
                'symbol': 'AAPL',
                'side': 'buy',
                'quantity': 100,
                'order_type': 'market'
            },
            'request_id': 'req_order_fail',
            'timestamp': '2024-01-01T10:00:00Z'
        }
        
        response = worker._handle_execute_order(request_data)
        response_dict = response.to_dict() if hasattr(response, 'to_dict') else response
        
        assert response_dict['status'] == 'error'
        assert 'error' in response_dict
        assert 'market_closed' in response_dict['error']

    def test_handle_evaluate_risk_success(self, worker, mock_adapter):
        """Test successful risk evaluation handling."""
        request_data = {
            'method': 'evaluate.risk',
            'parameters': {
                'portfolio': {
                    'AAPL': {'quantity': 100, 'avg_price': 150.0}
                },
                'market_data': {
                    'AAPL': {'current_price': 155.0, 'volatility': 0.25}
                },
                'risk_tolerance': 'moderate'
            },
            'request_id': 'req_risk_123',
            'timestamp': '2024-01-01T10:00:00Z'
        }
        
        response = worker._handle_evaluate_risk(request_data)
        response_dict = response.to_dict() if hasattr(response, 'to_dict') else response
        
        assert response_dict['status'] == 'success'
        assert 'data' in response_dict
        assert response_dict['data']['success'] is True
        assert 'risk_assessment' in response_dict['data']
        assert response_dict['data']['risk_assessment']['risk_score'] == 65.0
        
        # Verify adapter was called with correct parameters
        expected_portfolio = {
            'AAPL': {'quantity': 100, 'avg_price': 150.0}
        }
        expected_proposed_trade = {
            'symbol': 'PORTFOLIO_ANALYSIS',
            'action': 'evaluate',
            'quantity': 1,
            'market_conditions': {'AAPL': {'current_price': 155.0, 'volatility': 0.25}},
            'risk_tolerance': 'moderate'
        }
        mock_adapter.evaluate_risk.assert_called_once_with(
            portfolio=expected_portfolio,
            proposed_trade=expected_proposed_trade
        )

    def test_handle_evaluate_risk_failure(self, worker, mock_adapter):
        """Test risk evaluation handling with failure."""
        # Configure adapter to return failure
        mock_adapter.evaluate_risk.return_value = {
            'success': False,
            'error': {
                'type': 'insufficient_data',
                'message': 'Insufficient market data for risk evaluation'
            }
        }
        
        request_data = {
            'method': 'evaluate.risk',
            'parameters': {
                'portfolio': {},
                'market_data': {}
            },
            'request_id': 'req_risk_fail',
            'timestamp': '2024-01-01T10:00:00Z'
        }
        
        response = worker._handle_evaluate_risk(request_data)
        response_dict = response.to_dict() if hasattr(response, 'to_dict') else response
        
        assert response_dict['status'] == 'error'
        assert 'error' in response_dict
        assert 'insufficient_data' in response_dict['error']

    def test_handle_health_check(self, worker):
        """Test health check handling."""
        request_data = {
            'method': 'health.check',
            'parameters': {},
            'request_id': 'req_health_123',
            'timestamp': '2024-01-01T10:00:00Z'
        }
        
        response = worker._handle_health_check(request_data)
        response_dict = response.to_dict() if hasattr(response, 'to_dict') else response
        
        assert response_dict['status'] == 'success'
        assert response_dict['data']['health'] == 'ok'
        assert response_dict['data']['worker_id'] == 'test_worker_1'
        assert 'timestamp' in response_dict['data']
        assert 'uptime' in response_dict['data']

    def test_handle_unknown_method(self, worker):
        """Test handling of unknown method."""
        request_data = {
            'method': 'unknown.method',
            'parameters': {},
            'request_id': 'req_unknown_123',
            'timestamp': '2024-01-01T10:00:00Z'
        }
        
        response = worker._handle_request(request_data)
        response_dict = response.to_dict() if hasattr(response, 'to_dict') else response
        
        assert response_dict['status'] == 'error'
        assert 'error' in response_dict
        assert 'unknown_method' in response_dict['error']
        assert response_dict['request_id'] == 'req_unknown_123'

    def test_process_message_success(self, worker, mock_database):
        """Test successful message processing."""
        message_data = {
            'method': 'health.check',
            'parameters': {},
            'request_id': 'req_msg_123',
            'timestamp': '2024-01-01T10:00:00Z',
            'client_id': 'client_123'
        }
        
        message = json.dumps(message_data).encode('utf-8')
        
        with patch.object(worker, '_send_response') as mock_send:
            worker._process_message(message)
            
            # Verify database logging
            mock_database.log_request.assert_called_once()
            mock_database.log_response.assert_called_once()
            
            # Verify response was sent
            mock_send.assert_called_once()
            
            # Check response content
            call_args = mock_send.call_args[0][0]
            response_dict = call_args.to_dict() if hasattr(call_args, 'to_dict') else call_args
            assert response_dict['status'] == 'success'
            assert response_dict['request_id'] == 'req_msg_123'

    def test_process_message_invalid_json(self, worker, mock_database):
        """Test processing of invalid JSON message."""
        invalid_message = b'invalid json content'
        
        with patch.object(worker, '_send_response') as mock_send:
            worker._process_message(invalid_message)
            
            # Verify error response was sent
            mock_send.assert_called_once()
            
            call_args = mock_send.call_args[0][0]
            response_dict = call_args.to_dict() if hasattr(call_args, 'to_dict') else call_args
            assert response_dict['status'] == 'error'
            assert 'json_parse_error' in response_dict['error']

    def test_process_message_missing_fields(self, worker, mock_database):
        """Test processing of message with missing required fields."""
        incomplete_message = {
            'method': 'health.check'
            # Missing request_id, timestamp, etc.
        }
        
        message = json.dumps(incomplete_message).encode('utf-8')
        
        with patch.object(worker, '_send_response') as mock_send:
            worker._process_message(message)
            
            # Verify error response was sent
            mock_send.assert_called_once()
            
            call_args = mock_send.call_args[0][0]
            response_dict = call_args.to_dict() if hasattr(call_args, 'to_dict') else call_args
            assert response_dict['status'] == 'error'
            assert 'missing_field' in response_dict['error']

    def test_send_response(self, worker):
        """Test response sending."""
        response_data = {
            'status': 'success',
            'data': {'test': 'data'},
            'request_id': 'req_123',
            'timestamp': '2024-01-01T10:00:00Z'
        }
        
        worker._send_response(response_data)
        
        # Verify socket.send_multipart was called with two frames: [empty, response_json]
        worker.socket.send_multipart.assert_called_once()
        frames = worker.socket.send_multipart.call_args[0][0]
        assert isinstance(frames, (list, tuple))
        assert len(frames) == 2
        assert frames[0] == b""
        
        parsed_data = json.loads(frames[1].decode('utf-8'))
        assert parsed_data == response_data

    def test_update_status(self, worker, mock_database):
        """Test worker status update."""
        worker._update_status('busy', processed_requests=10)
        
        mock_database.update_worker_status.assert_called_once_with(
            worker_id='test_worker_1',
            status='busy',
            processed_requests=10,
            cpu_usage=worker.cpu_usage,
            memory_usage=worker.memory_usage
        )

    def test_get_system_metrics(self, worker):
        """Test system metrics collection."""
        with patch('psutil.cpu_percent', return_value=25.5), \
             patch('psutil.virtual_memory') as mock_memory:
            
            mock_memory.return_value.used = 1024 * 1024 * 512  # 512 MB
            
            worker._get_system_metrics()
            
            assert worker.cpu_usage == 25.5
            assert worker.memory_usage == 512.0

    def test_worker_exception_handling(self, worker, mock_adapter):
        """Test worker exception handling."""
        # Configure adapter to raise exception
        mock_adapter.scan_market.side_effect = Exception("Unexpected error")
        
        request_data = {
            'method': 'scan.market',
            'parameters': {'market_type': 'US'},
            'request_id': 'req_exception',
            'timestamp': '2024-01-01T10:00:00Z'
        }
        
        response = worker._handle_scan_market(request_data)
        response_dict = response.to_dict() if hasattr(response, 'to_dict') else response
        
        assert response_dict['status'] == 'error'
        assert 'error' in response_dict
        assert 'internal_error' in response_dict['error']
        assert 'Unexpected error' in response_dict['error']

    def test_worker_performance_metrics(self, worker):
        """Test worker performance metrics tracking."""
        # Process multiple requests to test metrics
        for i in range(5):
            request_data = {
                'method': 'health.check',
                'parameters': {},
                'request_id': f'req_perf_{i}',
                'timestamp': '2024-01-01T10:00:00Z'
            }
            
            response = worker._handle_health_check(request_data)
            response_dict = response.to_dict() if hasattr(response, 'to_dict') else response
            assert response_dict['status'] == 'success'
        
        # Check that processed_requests counter increased
        assert worker.processed_requests == 5

    def test_worker_concurrent_request_handling(self, worker, mock_adapter):
        """Test worker handling of concurrent requests."""
        import threading
        import time
        
        results = []
        
        def process_request(request_id):
            request_data = {
                'method': 'health.check',
                'parameters': {},
                'request_id': request_id,
                'timestamp': '2024-01-01T10:00:00Z'
            }
            
            response = worker._handle_health_check(request_data)
            results.append(response)
        
        # Create multiple threads to simulate concurrent requests
        threads = []
        for i in range(3):
            thread = threading.Thread(target=process_request, args=[f'req_concurrent_{i}'])
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify all requests were processed successfully
        assert len(results) == 3
        for result in results:
            result_dict = result.to_dict() if hasattr(result, 'to_dict') else result
            assert result_dict['status'] == 'success'


@pytest.mark.integration
class TestWorkerIntegration:
    """Test Worker integration with real components."""

    def test_worker_with_real_adapter(self, mock_context, mock_database):
        """Test worker with real TradingAgentsAdapter."""
        context, socket = mock_context
        
        with patch('zmq.Context', return_value=context), \
             patch('tacoreservice.workers.worker.DatabaseManager', return_value=mock_database):
            
            worker = Worker(worker_id='integration_test_worker')
            worker.socket = socket
            worker.database = mock_database
            
            # Test with real adapter (should fallback to mock implementation)
            request_data = {
                'method': 'scan.market',
                'parameters': {
                    'market_type': 'US',
                    'filters': {'min_price': 100.0},
                    'limit': 5
                },
                'request_id': 'req_integration_123',
                'timestamp': '2024-01-01T10:00:00Z'
            }
            
            response = worker._handle_scan_market(request_data)
            response_dict = response.to_dict() if hasattr(response, 'to_dict') else response
            
            # Should succeed with mock data when TradingAgents-CN is not available
            assert response_dict['status'] == 'success'
            assert 'data' in response_dict