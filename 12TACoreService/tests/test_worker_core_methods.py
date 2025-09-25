"""Tests for Worker core business methods."""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# 添加项目根目录到Python路径
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tacoreservice.workers.tradingagents_adapter import TradingAgentsAdapter


@pytest.mark.unit
class TestWorkerCoreMethods:
    """Test Worker core business methods."""

    @pytest.fixture
    def adapter(self):
        """Create TradingAgentsAdapter instance for testing."""
        return TradingAgentsAdapter()

    @pytest.fixture
    def mock_tradingagents_available(self, adapter):
        """Mock TradingAgents-CN availability."""
        # Set the required attributes to simulate TradingAgents availability
        adapter.interface = {"mock": True}
        adapter.stock_utils = Mock()
        with patch.object(TradingAgentsAdapter, '_is_tradingagents_available', return_value=True):
            yield

    @pytest.fixture
    def mock_tradingagents_unavailable(self, adapter):
        """Mock TradingAgents-CN unavailability."""
        # Remove the interface and stock_utils attributes to simulate unavailability
        if hasattr(adapter, 'interface'):
            delattr(adapter, 'interface')
        if hasattr(adapter, 'stock_utils'):
            delattr(adapter, 'stock_utils')
        with patch.object(TradingAgentsAdapter, '_is_tradingagents_available', return_value=False):
            yield

    @pytest.fixture
    def sample_market_scan_params(self):
        """Sample parameters for market scan."""
        return {
            "market_type": "stock",
            "filters": {
                "min_price": 10.0,
                "max_price": 500.0,
                "min_volume": 100000,
                "sectors": ["Technology", "Healthcare"]
            },
            "limit": 50
        }

    @pytest.fixture
    def sample_order_params(self):
        """Sample parameters for order execution."""
        return {
            "symbol": "AAPL",
            "side": "buy",
            "quantity": 100,
            "order_type": "market",
            "price": 150.0,
            "client_order_id": "test_order_123"
        }

    @pytest.fixture
    def sample_risk_params(self):
        """Sample parameters for risk evaluation."""
        return {
            "portfolio": {
                "AAPL": {"quantity": 100, "avg_price": 150.0},
                "GOOGL": {"quantity": 50, "avg_price": 2500.0}
            },
            "market_data": {
                "AAPL": {"current_price": 155.0, "volatility": 0.25},
                "GOOGL": {"current_price": 2450.0, "volatility": 0.30}
            },
            "risk_tolerance": "moderate"
        }


class TestScanMarket(TestWorkerCoreMethods):
    """Test scan_market method."""

    def test_scan_market_with_tradingagents_success(self, adapter, mock_tradingagents_available, sample_market_scan_params):
        """Test successful market scan with TradingAgents-CN."""
        # Mock TradingAgents components
        mock_market_scanner = Mock()
        mock_market_data = Mock()
        
        mock_scan_result = {
            "symbols": ["AAPL", "MSFT", "GOOGL"],
            "market_cap": [3000000000000, 2800000000000, 1800000000000],
            "sectors": ["Technology", "Technology", "Technology"]
        }
        
        mock_market_info = {
            "market_status": "open",
            "trading_session": "regular",
            "timezone": "US/Eastern"
        }
        
        mock_stock_data = {
            "AAPL": {"price": 155.0, "volume": 50000000, "change_percent": 2.5},
            "MSFT": {"price": 380.0, "volume": 30000000, "change_percent": 1.8},
            "GOOGL": {"price": 2450.0, "volume": 25000000, "change_percent": -0.5}
        }
        
        with patch.object(adapter, '_get_market_scanner', return_value=mock_market_scanner), \
             patch.object(adapter, '_get_market_data_provider', return_value=mock_market_data), \
             patch.object(adapter, '_get_market_info_safe', return_value=mock_market_info), \
             patch.object(adapter, '_get_stock_data_with_retry', return_value=mock_stock_data):
            
            mock_market_scanner.scan_market.return_value = mock_scan_result
            
            result = adapter.scan_market(
                market_type=sample_market_scan_params["market_type"],
                symbols=None,
                filters=sample_market_scan_params["filters"]
            )
            
            assert result["success"] is True
            assert "opportunities" in result
            assert "summary" in result
            assert len(result["opportunities"]) > 0
            assert result["summary"]["total_symbols"] == 5
            assert result["summary"]["success_rate"] == 1.0

    def test_scan_market_with_invalid_params(self, adapter):
        """Test market scan with invalid parameters."""
        invalid_params = {
            "market_type": "INVALID",
            "filters": "not_a_dict"
        }
        
        result = adapter.scan_market(
            market_type=invalid_params["market_type"],
            symbols=None,
            filters=invalid_params["filters"]
        )
        
        assert result["success"] is False
        assert "error" in result
        assert "validation" in result["error"]["type"]

    def test_scan_market_without_tradingagents(self, adapter, mock_tradingagents_unavailable, sample_market_scan_params):
        """Test market scan fallback when TradingAgents-CN is unavailable."""
        result = adapter.scan_market(
            market_type=sample_market_scan_params["market_type"],
            symbols=None,
            filters=sample_market_scan_params["filters"]
        )
        
        assert result["success"] is True
        assert "opportunities" in result
        assert result["summary"]["total_symbols"] > 0
        assert "mock_data" in result["summary"]["note"]

    def test_scan_market_exception_handling(self, adapter, mock_tradingagents_available, sample_market_scan_params):
        """Test market scan exception handling."""
        with patch.object(adapter, '_get_market_scanner', side_effect=Exception("Scanner error")):
            result = adapter.scan_market(
                market_type=sample_market_scan_params["market_type"],
                symbols=None,
                filters=sample_market_scan_params["filters"]
            )
            
            assert result["success"] is False
            assert "error" in result
            assert "Scanner error" in result["error"]["message"]


class TestExecuteOrder(TestWorkerCoreMethods):
    """Test execute_order method."""

    def test_execute_order_with_tradingagents_success(self, adapter, mock_tradingagents_available, sample_order_params):
        """Test successful order execution with TradingAgents-CN."""
        # Mock TradingAgents components
        mock_order_executor = Mock()
        mock_market_data = Mock()
        
        mock_market_info = {
            "market_status": "open",
            "trading_session": "regular"
        }
        
        mock_market_price = 155.0
        
        with patch.object(adapter, '_get_order_executor', return_value=mock_order_executor), \
             patch.object(adapter, '_get_market_data_provider', return_value=mock_market_data), \
             patch.object(adapter, '_get_market_info_safe', return_value=mock_market_info), \
             patch.object(adapter, '_get_current_market_price', return_value=mock_market_price):
            
            mock_order_executor.execute_order.return_value = {
                "order_id": "ORD123456",
                "status": "FILLED",
                "executed_price": 154.95,
                "executed_quantity": 100,
                "commission": 1.0
            }
            
            result = adapter.execute_order(sample_order_params)
            
            assert result["success"] is True
            assert "execution" in result
            assert result["execution"]["order_id"] == "ORD123456"
            assert result["execution"]["status"] == "FILLED"
            assert result["execution"]["executed_price"] == 154.95

    def test_execute_order_with_invalid_params(self, adapter):
        """Test order execution with invalid parameters."""
        invalid_params = {
            "symbol": "",  # Empty symbol
            "side": "invalid_side",
            "quantity": -100  # Negative quantity
        }
        
        result = adapter.execute_order(invalid_params)
        
        assert result["success"] is False
        assert "error" in result
        assert "validation" in result["error"]["type"]

    def test_execute_order_market_closed(self, adapter, mock_tradingagents_available, sample_order_params):
        """Test order execution when market is closed."""
        mock_market_info = {
            "market_status": "closed",
            "trading_session": "after_hours"
        }
        
        with patch.object(adapter, '_get_market_info_safe', return_value=mock_market_info):
            result = adapter.execute_order(sample_order_params)
            
            assert result["success"] is False
            assert "market_closed" in result["error"]["type"]

    def test_execute_order_without_tradingagents(self, adapter, mock_tradingagents_unavailable, sample_order_params):
        """Test order execution fallback when TradingAgents-CN is unavailable."""
        result = adapter.execute_order(sample_order_params)
        
        assert result["success"] is True
        assert "execution" in result
        assert "mock_execution" in result["execution"]["note"]

    def test_execute_order_exception_handling(self, adapter, mock_tradingagents_available, sample_order_params):
        """Test order execution exception handling."""
        with patch.object(adapter, '_get_order_executor', side_effect=Exception("Executor error")):
            result = adapter.execute_order(sample_order_params)
            
            assert result["success"] is False
            assert "error" in result
            assert "Executor error" in result["error"]["message"]


class TestEvaluateRisk(TestWorkerCoreMethods):
    """Test evaluate_risk method."""

    def test_evaluate_risk_with_tradingagents_success(self, adapter, mock_tradingagents_available, sample_risk_params):
        """Test successful risk evaluation with TradingAgents-CN."""
        # Mock TradingAgents components
        mock_risk_evaluator = Mock()
        mock_market_data = Mock()
        
        mock_market_info = {
            "market_status": "open",
            "volatility_index": 18.5
        }
        
        with patch.object(adapter, '_get_risk_evaluator', return_value=mock_risk_evaluator), \
             patch.object(adapter, '_get_market_data_provider', return_value=mock_market_data), \
             patch.object(adapter, '_get_market_info_safe', return_value=mock_market_info):
            
            mock_risk_evaluator.evaluate_portfolio_risk.return_value = {
                "var_95": 0.05,
                "expected_shortfall": 0.08,
                "sharpe_ratio": 1.25,
                "max_drawdown": 0.15,
                "beta": 1.1
            }
            
            result = adapter.evaluate_risk(sample_risk_params)
            
            assert result["success"] is True
            assert "risk_assessment" in result
            assert "risk_score" in result["risk_assessment"]
            assert "risk_level" in result["risk_assessment"]
            assert "recommendations" in result["risk_assessment"]
            assert 0 <= result["risk_assessment"]["risk_score"] <= 100

    def test_evaluate_risk_with_invalid_params(self, adapter):
        """Test risk evaluation with invalid parameters."""
        invalid_params = {
            "portfolio": "not_a_dict",
            "market_data": None
        }
        
        result = adapter.evaluate_risk(invalid_params)
        
        assert result["success"] is False
        assert "error" in result
        assert "validation" in result["error"]["type"]

    def test_evaluate_risk_high_risk_scenario(self, adapter, mock_tradingagents_available):
        """Test risk evaluation for high-risk scenario."""
        high_risk_params = {
            "portfolio": {
                "TSLA": {"quantity": 1000, "avg_price": 800.0},  # High volatility stock
                "GME": {"quantity": 500, "avg_price": 200.0}   # Meme stock
            },
            "market_data": {
                "TSLA": {"current_price": 750.0, "volatility": 0.80},
                "GME": {"current_price": 150.0, "volatility": 1.20}
            },
            "risk_tolerance": "conservative"
        }
        
        mock_market_info = {
            "market_status": "open",
            "volatility_index": 35.0  # High market volatility
        }
        
        with patch.object(adapter, '_get_market_info_safe', return_value=mock_market_info):
            result = adapter.evaluate_risk(high_risk_params)
            
            assert result["success"] is True
            assert result["risk_assessment"]["risk_level"] in ["HIGH", "VERY_HIGH"]
            assert result["risk_assessment"]["risk_score"] > 70

    def test_evaluate_risk_without_tradingagents(self, adapter, mock_tradingagents_unavailable, sample_risk_params):
        """Test risk evaluation fallback when TradingAgents-CN is unavailable."""
        result = adapter.evaluate_risk(sample_risk_params)
        
        assert result["success"] is True
        assert "risk_assessment" in result
        assert "mock_assessment" in result["risk_assessment"]["note"]

    def test_evaluate_risk_exception_handling(self, adapter, mock_tradingagents_available, sample_risk_params):
        """Test risk evaluation exception handling."""
        with patch.object(adapter, '_calculate_weighted_risk_score', side_effect=Exception("Risk calculation error")):
            result = adapter.evaluate_risk(sample_risk_params)
            
            assert result["success"] is False
            assert "error" in result
            assert "Risk calculation error" in result["error"]["message"]


class TestHelperMethods(TestWorkerCoreMethods):
    """Test helper methods."""

    def test_get_timestamp(self, adapter):
        """Test timestamp generation."""
        timestamp = adapter._get_timestamp()
        
        assert isinstance(timestamp, str)
        assert "T" in timestamp  # ISO format
        assert timestamp.endswith("Z")  # UTC timezone

    def test_get_default_symbols(self, adapter):
        """Test default symbols generation."""
        us_symbols = adapter._get_default_symbols("US")
        cn_symbols = adapter._get_default_symbols("CN")
        
        assert isinstance(us_symbols, list)
        assert isinstance(cn_symbols, list)
        assert len(us_symbols) > 0
        assert len(cn_symbols) > 0
        assert "AAPL" in us_symbols
        assert "000001.SZ" in cn_symbols

    def test_validate_order_price(self, adapter):
        """Test order price validation."""
        # Valid market order
        assert adapter._validate_order_price("market", None, 150.0) is True
        
        # Valid limit order
        assert adapter._validate_order_price("limit", 155.0, 150.0) is True
        
        # Invalid limit order (no price)
        assert adapter._validate_order_price("limit", None, 150.0) is False
        
        # Invalid price range
        assert adapter._validate_order_price("limit", 200.0, 150.0) is False  # Too high

    def test_calculate_commission(self, adapter):
        """Test commission calculation."""
        commission = adapter._calculate_commission(100, 150.0)
        
        assert isinstance(commission, float)
        assert commission > 0
        assert commission < 100  # Should be reasonable

    def test_determine_execution_status(self, adapter):
        """Test execution status determination."""
        # Market order should fill
        status = adapter._determine_execution_status("market", 150.0, 155.0)
        assert status == "FILLED"
        
        # Limit buy order below market should fill
        status = adapter._determine_execution_status("limit", 145.0, 150.0)
        assert status == "FILLED"
        
        # Limit buy order above market should be pending
        status = adapter._determine_execution_status("limit", 160.0, 150.0)
        assert status == "PENDING"

    def test_calculate_weighted_risk_score(self, adapter):
        """Test weighted risk score calculation."""
        risk_factors = {
            "market_volatility": 0.3,
            "position_size": 0.2,
            "sector_concentration": 0.4,
            "liquidity": 0.1,
            "technical": 0.25,
            "correlation": 0.15
        }
        
        score = adapter._calculate_weighted_risk_score(risk_factors)
        
        assert isinstance(score, float)
        assert 0 <= score <= 100

    def test_determine_risk_level_with_confidence(self, adapter):
        """Test risk level determination with confidence."""
        # Low risk
        level, confidence = adapter._determine_risk_level_with_confidence(25.0)
        assert level == "LOW"
        assert isinstance(confidence, float)
        
        # High risk
        level, confidence = adapter._determine_risk_level_with_confidence(85.0)
        assert level == "HIGH"
        assert isinstance(confidence, float)