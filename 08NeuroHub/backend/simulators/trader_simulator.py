#!/usr/bin/env python3
"""
NeuroTrade Nexus - 交易员模拟器
模拟交易员模块向Redis写入持仓状态

用于端到端测试中模拟真实交易环境
"""

import redis
import json
import logging
import time
from datetime import datetime
from typing import Dict, Any, List
import random

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TraderSimulator:
    """交易员模拟器"""
    
    def __init__(self, redis_host='localhost', redis_port=6379):
        self.redis_client = redis.Redis(
            host=redis_host,
            port=redis_port,
            decode_responses=True
        )
        self.positions = {}
        self.portfolio_stats = {
            "total_positions": 0,
            "total_unrealized_pnl": 0.0,
            "total_realized_pnl": 0.0,
            "last_update": None
        }
        
    def connect(self) -> bool:
        """连接Redis"""
        try:
            self.redis_client.ping()
            logger.info("✓ 交易员模拟器已连接到Redis")
            return True
        except Exception as e:
            logger.error(f"✗ Redis连接失败: {e}")
            return False
            
    def create_position(self, symbol: str, side: str, size: float, 
                       entry_price: float, current_price: float = None) -> Dict[str, Any]:
        """创建持仓"""
        if current_price is None:
            current_price = entry_price
            
        # 计算未实现盈亏
        if side == "long":
            unrealized_pnl = (current_price - entry_price) * size
        else:  # short
            unrealized_pnl = (entry_price - current_price) * size
            
        position = {
            "symbol": symbol,
            "side": side,
            "size": size,
            "entry_price": entry_price,
            "current_price": current_price,
            "unrealized_pnl": round(unrealized_pnl, 2),
            "status": "ACTIVE",
            "timestamp": datetime.now().isoformat(),
            "trader_id": "trader_001"
        }
        
        return position
        
    def write_position_to_redis(self, position: Dict[str, Any]) -> bool:
        """写入持仓到Redis"""
        try:
            key = f"positions:{position['symbol']}"
            self.redis_client.hset(key, mapping=position)
            
            # 更新本地缓存
            self.positions[position['symbol']] = position
            
            logger.info(f"✓ 写入持仓: {position['symbol']} - {position['side']} {position['size']} @ {position['entry_price']}")
            return True
            
        except Exception as e:
            logger.error(f"✗ 写入持仓失败: {e}")
            return False
            
    def update_position_price(self, symbol: str, new_price: float) -> bool:
        """更新持仓价格"""
        try:
            key = f"positions:{symbol}"
            position_data = self.redis_client.hgetall(key)
            
            if not position_data:
                logger.warning(f"持仓不存在: {symbol}")
                return False
                
            # 重新计算未实现盈亏
            entry_price = float(position_data['entry_price'])
            size = float(position_data['size'])
            side = position_data['side']
            
            if side == "long":
                unrealized_pnl = (new_price - entry_price) * size
            else:
                unrealized_pnl = (entry_price - new_price) * size
                
            # 更新数据
            updates = {
                "current_price": new_price,
                "unrealized_pnl": round(unrealized_pnl, 2),
                "timestamp": datetime.now().isoformat()
            }
            
            self.redis_client.hset(key, mapping=updates)
            logger.info(f"✓ 更新价格: {symbol} -> {new_price}, PnL: {unrealized_pnl:.2f}")
            
            return True
            
        except Exception as e:
            logger.error(f"✗ 更新价格失败: {e}")
            return False
            
    def clear_position(self, symbol: str) -> bool:
        """清空持仓"""
        try:
            key = f"positions:{symbol}"
            
            # 标记为已清空而不是删除
            updates = {
                "size": 0,
                "status": "CLEARED",
                "unrealized_pnl": 0,
                "clear_timestamp": datetime.now().isoformat()
            }
            
            self.redis_client.hset(key, mapping=updates)
            logger.info(f"✓ 清空持仓: {symbol}")
            
            return True
            
        except Exception as e:
            logger.error(f"✗ 清空持仓失败: {e}")
            return False
            
    def clear_all_positions(self) -> bool:
        """清空所有持仓"""
        try:
            position_keys = self.redis_client.keys("positions:*")
            
            if not position_keys:
                logger.info("没有持仓需要清空")
                return True
                
            cleared_count = 0
            for key in position_keys:
                symbol = key.split(":")[1]
                if self.clear_position(symbol):
                    cleared_count += 1
                    
            logger.info(f"✓ 已清空 {cleared_count}/{len(position_keys)} 个持仓")
            return cleared_count == len(position_keys)
            
        except Exception as e:
            logger.error(f"✗ 清空所有持仓失败: {e}")
            return False
            
    def update_portfolio_stats(self) -> bool:
        """更新组合统计"""
        try:
            position_keys = self.redis_client.keys("positions:*")
            
            total_positions = 0
            total_unrealized_pnl = 0.0
            
            for key in position_keys:
                position_data = self.redis_client.hgetall(key)
                if position_data.get('status') == 'ACTIVE':
                    total_positions += 1
                    total_unrealized_pnl += float(position_data.get('unrealized_pnl', 0))
                    
            stats = {
                "total_positions": total_positions,
                "total_unrealized_pnl": round(total_unrealized_pnl, 2),
                "last_update": datetime.now().isoformat(),
                "trader_id": "trader_001"
            }
            
            self.redis_client.hset("portfolio:stats", mapping=stats)
            self.portfolio_stats = stats
            
            logger.info(f"✓ 更新组合统计: {total_positions}个持仓, PnL: {total_unrealized_pnl:.2f}")
            return True
            
        except Exception as e:
            logger.error(f"✗ 更新组合统计失败: {e}")
            return False
            
    def get_all_positions(self) -> Dict[str, Dict[str, Any]]:
        """获取所有持仓"""
        try:
            position_keys = self.redis_client.keys("positions:*")
            positions = {}
            
            for key in position_keys:
                symbol = key.split(":")[1]
                position_data = self.redis_client.hgetall(key)
                positions[symbol] = position_data
                
            return positions
            
        except Exception as e:
            logger.error(f"✗ 获取持仓失败: {e}")
            return {}
            
    def simulate_market_scenario(self, scenario: str = "normal") -> bool:
        """模拟市场场景"""
        logger.info(f"--- 模拟市场场景: {scenario} ---")
        
        if scenario == "normal":
            return self._simulate_normal_trading()
        elif scenario == "volatile":
            return self._simulate_volatile_market()
        elif scenario == "crash":
            return self._simulate_market_crash()
        else:
            logger.error(f"未知场景: {scenario}")
            return False
            
    def _simulate_normal_trading(self) -> bool:
        """模拟正常交易"""
        try:
            # 创建一些正常持仓
            positions = [
                self.create_position("BTC-USDT", "long", 1.5, 45000.0, 45200.0),
                self.create_position("ETH-USDT", "short", 10.0, 3200.0, 3150.0),
                self.create_position("ADA-USDT", "long", 1000.0, 0.5, 0.52),
                self.create_position("SOL-USDT", "long", 50.0, 100.0, 102.0)
            ]
            
            for position in positions:
                self.write_position_to_redis(position)
                
            self.update_portfolio_stats()
            logger.info("✓ 正常交易场景模拟完成")
            return True
            
        except Exception as e:
            logger.error(f"✗ 正常交易模拟失败: {e}")
            return False
            
    def _simulate_volatile_market(self) -> bool:
        """模拟波动市场"""
        try:
            # 创建一些高风险持仓
            positions = [
                self.create_position("BTC-USDT", "long", 2.0, 45000.0, 42000.0),  # 大幅亏损
                self.create_position("ETH-USDT", "short", 15.0, 3200.0, 3500.0),  # 大幅亏损
                self.create_position("LUNA-USDT", "long", 10000.0, 80.0, 0.1),   # 崩盘
                self.create_position("UST-USDT", "long", 50000.0, 1.0, 0.3)      # 脱锚
            ]
            
            for position in positions:
                self.write_position_to_redis(position)
                
            self.update_portfolio_stats()
            logger.info("✓ 波动市场场景模拟完成")
            return True
            
        except Exception as e:
            logger.error(f"✗ 波动市场模拟失败: {e}")
            return False
            
    def _simulate_market_crash(self) -> bool:
        """模拟市场崩盘"""
        try:
            # 创建崩盘前的持仓
            positions = [
                self.create_position("BTC-USDT", "long", 5.0, 45000.0, 30000.0),
                self.create_position("ETH-USDT", "long", 50.0, 3200.0, 2000.0),
                self.create_position("LUNA-USDT", "long", 10000.0, 80.0, 0.001),
                self.create_position("UST-USDT", "long", 100000.0, 1.0, 0.1)
            ]
            
            for position in positions:
                self.write_position_to_redis(position)
                
            self.update_portfolio_stats()
            logger.info("✓ 市场崩盘场景模拟完成")
            return True
            
        except Exception as e:
            logger.error(f"✗ 市场崩盘模拟失败: {e}")
            return False
            
    def cleanup_test_data(self) -> bool:
        """清理测试数据"""
        try:
            # 删除所有持仓数据
            position_keys = self.redis_client.keys("positions:*")
            if position_keys:
                self.redis_client.delete(*position_keys)
                
            # 删除组合统计
            self.redis_client.delete("portfolio:stats")
            
            logger.info("✓ 测试数据已清理")
            return True
            
        except Exception as e:
            logger.error(f"✗ 清理测试数据失败: {e}")
            return False
            
def main():
    """主函数 - 用于独立运行"""
    import argparse
    
    parser = argparse.ArgumentParser(description='交易员模拟器')
    parser.add_argument('--scenario', choices=['normal', 'volatile', 'crash'], 
                       default='normal', help='模拟场景')
    parser.add_argument('--cleanup', action='store_true', help='清理测试数据')
    parser.add_argument('--redis-host', default='localhost', help='Redis主机')
    parser.add_argument('--redis-port', type=int, default=6379, help='Redis端口')
    
    args = parser.parse_args()
    
    # 创建模拟器
    simulator = TraderSimulator(args.redis_host, args.redis_port)
    
    if not simulator.connect():
        logger.error("无法连接到Redis")
        return False
        
    try:
        if args.cleanup:
            return simulator.cleanup_test_data()
        else:
            return simulator.simulate_market_scenario(args.scenario)
            
    except KeyboardInterrupt:
        logger.info("用户中断")
        return True
    except Exception as e:
        logger.error(f"执行失败: {e}")
        return False
        
if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)