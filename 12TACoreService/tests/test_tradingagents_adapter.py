"""Tests for TradingAgentsAdapter integration."""

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


@pytest.mark.integration
class TestTradingAgentsAdapter:
    """Test TradingAgentsAdapter integration functionality."""

    @pytest.fixture
    def adapter(self):
        """Create TradingAgentsAdapter instance for testing."""
        return TradingAgentsAdapter()

    @pytest.fixture
    def mock_tradingagents_components(self):
        """Mock all TradingAgents-CN components."""
        components = {
            'market_scanner': Mock(),
            'order_executor': Mock(),
            'risk_evaluator': Mock(),
            'stock_analyzer': Mock(),
            'market_data_provider': Mock()
        }
        
        # Set up default return values
        components['market_scanner'].scan_market.return_value = {
            'symbols': ['AAPL', 'MSFT', 'GOOGL'],
            'scores': [85.5, 78.2, 92.1],
            'sectors': ['Technology', 'Technology', 'Technology']
        }
        
        components['order_executor'].execute_order.return_value = {
            'order_id': 'ORD123456789',
            'status': 'FILLED',
            'executed_price': 154.95,
            'executed_quantity': 100,
            'commission': 1.0,
            'timestamp': '2024-01-01T10:30:00Z'
        }
        
        components['risk_evaluator'].evaluate_portfolio_risk.return_value = {
            'var_95': 0.05,
            'expected_shortfall': 0.08,
            'sharpe_ratio': 1.25,
            'max_drawdown': 0.15,
            'beta': 1.1,
            'volatility': 0.18
        }
        
        components['stock_analyzer'].analyze_stock.return_value = {
            'sma_20': 150.5,
            'sma_50': 148.2,
            'rsi': 65.8,
            'macd': 2.5,
            'bollinger_upper': 155.0,
            'bollinger_lower': 145.0
        }
        
        components['market_data_provider'].get_market_data.return_value = {
            'AAPL': {
                'price': 155.0,
                'volume': 50000000,
                'change': 2.5,
                'change_percent': 1.64,
                'bid': 154.95,
                'ask': 155.05
            }
        }
        
        return components

    def test_adapter_initialization(self, adapter):
        """Test adapter initialization."""
        assert adapter is not None
        assert hasattr(adapter, 'scan_market')
        assert hasattr(adapter, 'execute_order')
        assert hasattr(adapter, 'evaluate_risk')

    def test_tradingagents_availability_check(self, adapter):
        """Test TradingAgents-CN availability check."""
        # Test when available
        with patch('importlib.util.find_spec', return_value=Mock()):
            assert adapter._is_tradingagents_available() is True
        
        # Test when unavailable
        with patch('importlib.util.find_spec', return_value=None):
            assert adapter._is_tradingagents_available() is False

    def test_get_market_scanner_success(self, adapter):
        """Test successful market scanner retrieval."""
        with patch.object(adapter, '_is_tradingagents_available', return_value=True):
            scanner = adapter._get_market_scanner()
            
            # Should return a RealMarketScanner wrapper
            assert scanner is not None
            assert hasattr(scanner, 'scan_market')
            assert hasattr(scanner, 'adapter')

    def test_get_market_scanner_failure(self, adapter):
        """Test market scanner retrieval failure."""
        with patch.object(adapter, '_is_tradingagents_available', return_value=False):
            scanner = adapter._get_market_scanner()
            assert scanner is None

    def test_get_order_executor_success(self, adapter):
        """Test successful order executor retrieval."""
        with patch.object(adapter, '_is_tradingagents_available', return_value=True):
            executor = adapter._get_order_executor()
            
            # Should return a RealOrderExecutor wrapper
            assert executor is not None
            assert hasattr(executor, 'execute_order')
            assert hasattr(executor, 'adapter')

    def test_get_risk_evaluator_success(self, adapter):
        """Test successful risk evaluator retrieval."""
        with patch.object(adapter, '_is_tradingagents_available', return_value=True):
            evaluator = adapter._get_risk_evaluator()
            
            # Should return a RealRiskEvaluator wrapper
            assert evaluator is not None
            assert hasattr(evaluator, 'evaluate_risk')
            assert hasattr(evaluator, 'adapter')

    def test_get_market_info_safe_success(self, adapter, mock_tradingagents_components):
        """Test safe market info retrieval."""
        mock_market_data = mock_tradingagents_components['market_data_provider']
        mock_market_data.get_market_info.return_value = {
            'market_status': 'open',
            'trading_session': 'regular',
            'timezone': 'US/Eastern',
            'last_updated': '2024-01-01T10:30:00Z'
        }
        
        with patch.object(adapter, '_get_market_data_provider', return_value=mock_market_data):
            market_info = adapter._get_market_info_safe('US')
            
            assert market_info is not None
            assert market_info['market_status'] == 'open'
            assert 'trading_session' in market_info

    def test_get_market_info_safe_failure(self, adapter):
        """Test safe market info retrieval with failure."""
        with patch.object(adapter, '_get_market_data_provider', side_effect=Exception("API Error")):
            market_info = adapter._get_market_info_safe('US')
            
            assert market_info is not None
            assert market_info['market_status'] == 'unknown'
            assert 'error' in market_info

    def test_get_stock_data_with_retry_success(self, adapter, mock_tradingagents_components):
        """Test stock data retrieval with retry mechanism."""
        mock_market_data = mock_tradingagents_components['market_data_provider']
        symbols = ['AAPL', 'MSFT']
        
        expected_data = {
            'AAPL': {'price': 155.0, 'volume': 50000000},
            'MSFT': {'price': 380.0, 'volume': 30000000}
        }
        
        mock_market_data.get_stock_data.return_value = expected_data
        
        with patch.object(adapter, '_get_market_data_provider', return_value=mock_market_data):
            stock_data = adapter._get_stock_data_with_retry(symbols)
            
            assert stock_data == expected_data
            mock_market_data.get_stock_data.assert_called_once_with(symbols)

    def test_get_stock_data_with_retry_failure(self, adapter):
        """Test stock data retrieval with retry failure."""
        symbols = ['AAPL', 'MSFT']
        
        with patch.object(adapter, '_get_market_data_provider', side_effect=Exception("Network Error")):
            stock_data = adapter._get_stock_data_with_retry(symbols)
            
            assert stock_data == {}

    def test_analyze_opportunity_success(self, adapter, mock_tradingagents_components):
        """Test opportunity analysis."""
        symbol = 'AAPL'
        stock_data = {'price': 155.0, 'volume': 50000000, 'change_percent': 2.5}
        market_info = {'market_status': 'open', 'is_china': False}
        filters = {'min_volume': 1000000, 'min_confidence': 0.5}
        
        mock_analyzer = mock_tradingagents_components['stock_analyzer']
        
        with patch.object(adapter, '_get_stock_analyzer', return_value=mock_analyzer):
            opportunity = adapter._analyze_opportunity(symbol, stock_data, market_info, filters)
            
            assert opportunity is not None
            assert opportunity['symbol'] == symbol
            assert 'signal' in opportunity
            assert 'confidence' in opportunity
            assert 'current_price' in opportunity

    def test_analyze_opportunity_failure(self, adapter):
        """Test opportunity analysis failure."""
        symbol = 'AAPL'
        stock_data = {'price': 155.0, 'volume': 50000000}
        market_info = {'market_status': 'open', 'is_china': False}
        filters = {'min_volume': 1000000, 'min_confidence': 0.5}
        
        # Test with invalid stock data
        invalid_stock_data = {}
        opportunity = adapter._analyze_opportunity(symbol, invalid_stock_data, market_info, filters)
        
        assert opportunity is None  # Should return None for invalid data

    def test_get_current_market_price_success(self, adapter, mock_tradingagents_components):
        """Test current market price retrieval."""
        symbol = 'AAPL'
        market_info = {'is_china': False}
        
        # Mock the _get_stock_data_with_retry method to return expected data
        with patch.object(adapter, '_get_stock_data_with_retry', return_value={'close': 155.0}):
            price = adapter._get_current_market_price(symbol, market_info)
            
            assert price == 155.0

    def test_get_current_market_price_failure(self, adapter):
        """Test current market price retrieval failure."""
        symbol = 'AAPL'
        market_info = {'is_china': False}
        
        # Mock the _get_stock_data_with_retry method to return None (failure)
        with patch.object(adapter, '_get_stock_data_with_retry', return_value=None):
            price = adapter._get_current_market_price(symbol, market_info)
            
            assert price is None

    def test_calculate_execution_price_market_order(self, adapter):
        """Test execution price calculation for market order."""
        order_type = 'market'
        order_price = None
        market_price = 155.0
        
        execution_price = adapter._calculate_execution_price(order_type, order_price, market_price)
        
        # Market order should execute at market price with some slippage
        assert execution_price is not None
        assert abs(execution_price - market_price) <= market_price * 0.001  # Max 0.1% slippage

    def test_calculate_execution_price_limit_order(self, adapter):
        """Test execution price calculation for limit order."""
        order_type = 'limit'
        order_price = 154.0
        market_price = 155.0
        
        execution_price = adapter._calculate_execution_price(order_type, order_price, market_price)
        
        # Limit order should execute at limit price or better
        assert execution_price == order_price

    def test_calculate_comprehensive_risk_factors(self, adapter):
        """Test comprehensive risk factors calculation."""
        portfolio = {
            'AAPL': {'quantity': 100, 'avg_price': 150.0},
            'MSFT': {'quantity': 50, 'avg_price': 350.0}
        }
        
        market_data = {
            'AAPL': {'current_price': 155.0, 'volatility': 0.25},
            'MSFT': {'current_price': 380.0, 'volatility': 0.20}
        }
        
        market_info = {
            'volatility_index': 18.5,
            'market_status': 'open'
        }
        
        risk_factors = adapter._calculate_comprehensive_risk_factors(portfolio, market_data, market_info)
        
        assert isinstance(risk_factors, dict)
        assert 'market_volatility' in risk_factors
        assert 'position_size' in risk_factors
        assert 'sector_concentration' in risk_factors
        assert 'liquidity' in risk_factors
        assert 'technical' in risk_factors
        assert 'correlation' in risk_factors
        
        # All risk factors should be between 0 and 1
        for factor_name, factor_value in risk_factors.items():
            assert 0 <= factor_value <= 1, f"Risk factor {factor_name} out of range: {factor_value}"

    def test_calculate_market_volatility_risk(self, adapter):
        """Test market volatility risk calculation."""
        market_data = {
            'AAPL': {'volatility': 0.25},
            'MSFT': {'volatility': 0.20},
            'TSLA': {'volatility': 0.80}  # High volatility
        }
        
        market_info = {'volatility_index': 25.0}  # Elevated VIX
        
        volatility_risk = adapter._calculate_market_volatility(market_data, market_info)
        
        assert isinstance(volatility_risk, float)
        assert 0 <= volatility_risk <= 1
        assert volatility_risk > 0.3  # Should be elevated due to high VIX and TSLA

    def test_calculate_position_size_risk(self, adapter):
        """Test position size risk calculation."""
        portfolio = {
            'AAPL': {'quantity': 1000, 'avg_price': 150.0},  # Large position
            'MSFT': {'quantity': 10, 'avg_price': 350.0}     # Small position
        }
        
        market_data = {
            'AAPL': {'current_price': 155.0},
            'MSFT': {'current_price': 380.0}
        }
        
        position_risk = adapter._calculate_position_size_risk(portfolio, market_data)
        
        assert isinstance(position_risk, float)
        assert 0 <= position_risk <= 1
        assert position_risk > 0.5  # Should be high due to concentrated AAPL position

    def test_calculate_sector_concentration_risk(self, adapter):
        """Test sector concentration risk calculation."""
        portfolio = {
            'AAPL': {'quantity': 100, 'avg_price': 150.0},   # Technology
            'MSFT': {'quantity': 50, 'avg_price': 350.0},    # Technology
            'GOOGL': {'quantity': 20, 'avg_price': 2500.0}   # Technology
        }
        
        market_data = {
            'AAPL': {'current_price': 155.0},
            'MSFT': {'current_price': 380.0},
            'GOOGL': {'current_price': 2450.0}
        }
        
        concentration_risk = adapter._calculate_sector_concentration_risk(portfolio, market_data)
        
        assert isinstance(concentration_risk, float)
        assert 0 <= concentration_risk <= 1
        assert concentration_risk > 0.7  # Should be high due to tech concentration

    def test_generate_risk_recommendations(self, adapter):
        """Test risk recommendations generation."""
        risk_factors = {
            'market_volatility': 0.6,
            'position_size': 0.8,
            'sector_concentration': 0.9,
            'liquidity': 0.3,
            'technical': 0.4,
            'correlation': 0.7
        }
        
        risk_score = 75.0
        risk_level = 'HIGH'
        
        recommendations = adapter._generate_risk_recommendations(risk_factors, risk_score, risk_level)
        
        assert isinstance(recommendations, list)
        assert len(recommendations) > 0
        
        # Should contain specific recommendations for high-risk factors
        recommendation_text = ' '.join(recommendations)
        assert 'diversification' in recommendation_text.lower() or 'reduce' in recommendation_text.lower()

    def test_calculate_risk_adjusted_position_size(self, adapter):
        """Test risk-adjusted position size calculation."""
        current_position = 1000
        risk_score = 80.0  # High risk
        risk_tolerance = 'conservative'
        
        adjusted_size = adapter._calculate_risk_adjusted_position_size(
            current_position, risk_score, risk_tolerance
        )
        
        assert isinstance(adjusted_size, int)
        assert adjusted_size < current_position  # Should be reduced due to high risk
        assert adjusted_size > 0

    def test_integration_scan_to_execute_workflow(self, adapter, mock_tradingagents_components):
        """Test integrated workflow from scan to execute."""
        # First scan the market
        scan_params = {
            'market_type': 'US',
            'filters': {'min_price': 100.0, 'max_price': 200.0},
            'limit': 10
        }
        
        with patch.object(adapter, '_is_tradingagents_available', return_value=True), \
             patch.object(adapter, '_get_market_scanner', return_value=mock_tradingagents_components['market_scanner']), \
             patch.object(adapter, '_get_market_data_provider', return_value=mock_tradingagents_components['market_data_provider']), \
             patch.object(adapter, '_get_market_info_safe', return_value={'market_status': 'open'}), \
             patch.object(adapter, '_get_stock_data_with_retry', return_value={'price': 155.0, 'volume': 50000000}):
            
            scan_result = adapter.scan_market(
            market_type=scan_params['market_type'],
            symbols=None,
            filters=scan_params['filters']
        )
            
            assert scan_result['success'] is True
            assert len(scan_result['opportunities']) > 0
            
            # Use scan result to execute order
            symbol = scan_result['opportunities'][0]['symbol']
            
            order_params = {
                'symbol': symbol,
                'side': 'buy',
                'quantity': 100,
                'order_type': 'market'
            }
            
            with patch.object(adapter, '_get_order_executor', return_value=mock_tradingagents_components['order_executor']), \
                 patch.object(adapter, '_get_current_market_price', return_value=155.0):
                
                execute_result = adapter.execute_order(order_params)
                
                assert execute_result['success'] is True
                assert execute_result['execution']['order_id'] is not None