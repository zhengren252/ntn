"""策略管理器模块

该模块提供策略管理功能，包括策略配置、性能监控和使用统计。
"""

import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class StrategyManagerData:
    """策略管理器数据"""

    strategies: Dict[str, "StrategyConfig"] = field(default_factory=dict)
    performance_history: Dict[str, List[Dict]] = field(default_factory=dict)
    usage_stats: Dict[str, Dict] = field(default_factory=dict)


@dataclass
class StrategyConfig:
    """
    策略配置数据类
    """

    strategy_id: str
    name: str
    version: str
    description: str
    parameters: Dict[str, Any]
    risk_limits: Dict[str, float]
    performance_metrics: Dict[str, float]
    is_active: bool = True
    created_at: str = None
    updated_at: str = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()
        if self.updated_at is None:
            self.updated_at = datetime.now().isoformat()


class StrategyManager:
    """
    策略管理器

    负责：
    1. 策略注册和管理
    2. 策略参数验证
    3. 策略性能跟踪
    4. 策略版本控制
    """

    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)

        # 使用数据类管理策略相关数据
        self.data = StrategyManagerData()

    async def initialize(self):
        """
        初始化策略管理器
        """
        self.logger.info("正在初始化策略管理器...")

        try:
            # 注册默认策略
            await self._register_default_strategies()

            # 加载策略性能历史
            await self._load_performance_history()

            self.logger.info("策略管理器初始化完成，已注册 %s 个策略", len(self.data.strategies))

        except Exception as e:
            self.logger.error("策略管理器初始化失败: %s", e)
            raise

    async def _register_default_strategies(self):
        """
        注册默认策略
        """
        # 网格策略 v1.2
        grid_strategy = StrategyConfig(
            strategy_id="grid_v1.2",
            name="网格交易策略",
            version="1.2",
            description="基于价格网格的自动交易策略，适用于震荡市场",
            parameters={
                "grid_num": {"type": "int", "min": 5, "max": 50, "default": 20},
                "profit_ratio": {
                    "type": "float",
                    "min": 0.005,
                    "max": 0.1,
                    "default": 0.02,
                },
                "stop_loss": {
                    "type": "float",
                    "min": 0.01,
                    "max": 0.2,
                    "default": 0.05,
                },
                "grid_spacing": {
                    "type": "float",
                    "min": 0.001,
                    "max": 0.05,
                    "default": 0.01,
                },
                "max_position": {
                    "type": "float",
                    "min": 0.1,
                    "max": 1.0,
                    "default": 0.5,
                },
            },
            risk_limits={
                "max_drawdown": 0.15,
                "max_position_size": 0.3,
                "daily_loss_limit": 0.05,
            },
            performance_metrics={
                "expected_return": 0.12,
                "sharpe_ratio": 1.2,
                "max_drawdown": 0.08,
                "win_rate": 0.65,
            },
        )

        # 均线交叉策略 v1.0
        ma_cross_strategy = StrategyConfig(
            strategy_id="ma_cross_v1.0",
            name="均线交叉策略",
            version="1.0",
            description="基于快慢均线交叉的趋势跟踪策略",
            parameters={
                "fast_period": {"type": "int", "min": 5, "max": 50, "default": 10},
                "slow_period": {"type": "int", "min": 10, "max": 200, "default": 30},
                "signal_threshold": {
                    "type": "float",
                    "min": 0.001,
                    "max": 0.05,
                    "default": 0.02,
                },
                "stop_loss": {
                    "type": "float",
                    "min": 0.01,
                    "max": 0.2,
                    "default": 0.03,
                },
                "take_profit": {
                    "type": "float",
                    "min": 0.02,
                    "max": 0.5,
                    "default": 0.06,
                },
            },
            risk_limits={
                "max_drawdown": 0.12,
                "max_position_size": 0.4,
                "daily_loss_limit": 0.04,
            },
            performance_metrics={
                "expected_return": 0.15,
                "sharpe_ratio": 1.5,
                "max_drawdown": 0.06,
                "win_rate": 0.58,
            },
        )

        # RSI反转策略 v1.1
        rsi_strategy = StrategyConfig(
            strategy_id="rsi_reversal_v1.1",
            name="RSI反转策略",
            version="1.1",
            description="基于RSI指标的反转交易策略",
            parameters={
                "rsi_period": {"type": "int", "min": 10, "max": 30, "default": 14},
                "oversold_threshold": {
                    "type": "float",
                    "min": 20,
                    "max": 40,
                    "default": 30,
                },
                "overbought_threshold": {
                    "type": "float",
                    "min": 60,
                    "max": 80,
                    "default": 70,
                },
                "stop_loss": {
                    "type": "float",
                    "min": 0.01,
                    "max": 0.15,
                    "default": 0.04,
                },
                "take_profit": {
                    "type": "float",
                    "min": 0.02,
                    "max": 0.3,
                    "default": 0.08,
                },
            },
            risk_limits={
                "max_drawdown": 0.10,
                "max_position_size": 0.25,
                "daily_loss_limit": 0.03,
            },
            performance_metrics={
                "expected_return": 0.18,
                "sharpe_ratio": 1.8,
                "max_drawdown": 0.05,
                "win_rate": 0.72,
            },
        )

        # 注册策略
        await self.register_strategy(grid_strategy)
        await self.register_strategy(ma_cross_strategy)
        await self.register_strategy(rsi_strategy)

    async def _load_performance_history(self):
        """
        加载策略性能历史（从数据库或文件）
        """
        # 这里可以从数据库加载历史数据
        # 目前使用模拟数据
        for strategy_id in self.data.strategies.keys():
            self.data.performance_history[strategy_id] = []
            self.data.usage_stats[strategy_id] = {
                "total_uses": 0,
                "success_count": 0,
                "failure_count": 0,
                "avg_return": 0.0,
                "last_used": None,
            }

    async def register_strategy(self, strategy) -> str:
        """
        注册新策略

        Args:
            strategy: 策略配置（StrategyConfig对象或字典）

        Returns:
            str: 策略ID
        """
        try:
            print(f"DEBUG: 开始注册策略: {strategy}")
            self.logger.info("开始注册策略: %s", strategy)
            
            # 如果是字典，转换为StrategyConfig对象
            if isinstance(strategy, dict):
                print("DEBUG: 正在转换策略配置...")
                self.logger.info("转换字典为StrategyConfig对象")
                strategy = self._dict_to_strategy_config(strategy)
            
            # 验证策略配置
            self._validate_strategy_config(strategy)

            # 检查策略是否已存在
            if strategy.strategy_id in self.data.strategies:
                raise ValueError(f"策略已存在: {strategy.strategy_id}")

            # 注册策略
            self.data.strategies[strategy.strategy_id] = strategy

            # 初始化性能历史
            self.data.performance_history[strategy.strategy_id] = []

            # 初始化使用统计
            self.data.usage_stats[strategy.strategy_id] = {
                "total_uses": 0,
                "success_count": 0,
                "failure_count": 0,
                "avg_return": 0.0,
                "last_used": None,
                "created_at": datetime.now().isoformat(),
            }

            print(f"DEBUG: 策略注册成功: {strategy.strategy_id}")
            self.logger.info("策略注册成功: %s", strategy.strategy_id)
            return strategy.strategy_id

        except Exception as e:
            print(f"DEBUG: 策略注册失败: {e}")
            self.logger.error("策略注册失败: %s", e)
            raise

    def _validate_strategy_config(self, strategy: StrategyConfig):
        """
        验证策略配置

        Args:
            strategy: 策略配置
        """
        if not strategy.strategy_id:
            raise ValueError("策略ID不能为空")

        if not strategy.name:
            raise ValueError("策略名称不能为空")

        if not strategy.parameters:
            raise ValueError("策略参数不能为空")

        # 验证参数格式和值
        for param_name, param_config in strategy.parameters.items():
            if not isinstance(param_config, dict):
                raise ValueError(f"参数配置格式错误: {param_name}")

            required_fields = ["type", "min", "max", "default"]
            for field in required_fields:
                if field not in param_config:
                    raise ValueError(f"参数 {param_name} 缺少必需字段: {field}")
            
            # 验证默认值
            default_value = param_config["default"]
            param_type = param_config["type"]
            min_value = param_config["min"]
            max_value = param_config["max"]
            
            # 检查类型匹配
            if param_type == "int":
                if not isinstance(default_value, int):
                    if isinstance(default_value, str):
                        try:
                            default_value = int(default_value)
                        except ValueError:
                            raise ValueError(f"参数类型无效: {param_name} = {default_value} (期望整数类型)")
                    else:
                        raise ValueError(f"参数类型无效: {param_name} = {default_value} (期望整数类型)")
                
                # 检查范围
                if default_value < min_value or default_value > max_value:
                    raise ValueError(f"参数值超出范围: {param_name} = {default_value} (范围: {min_value}-{max_value})")
                
                # 检查负数
                if default_value < 0:
                    raise ValueError(f"参数值无效: {param_name} = {default_value} (不能为负数)")
                    
            elif param_type == "float":
                if not isinstance(default_value, (int, float)):
                    if isinstance(default_value, str):
                        try:
                            default_value = float(default_value)
                        except ValueError:
                            raise ValueError(f"参数类型无效: {param_name} = {default_value} (期望浮点数类型)")
                    else:
                        raise ValueError(f"参数类型无效: {param_name} = {default_value} (期望浮点数类型)")
                
                # 检查范围
                if default_value < min_value or default_value > max_value:
                    raise ValueError(f"参数值超出范围: {param_name} = {default_value} (范围: {min_value}-{max_value})")
                
                # 检查负数
                if default_value < 0:
                    raise ValueError(f"参数值无效: {param_name} = {default_value} (不能为负数)")

    def _dict_to_strategy_config(self, strategy_dict: Dict[str, Any]) -> StrategyConfig:
        """
        将字典转换为StrategyConfig对象
        
        Args:
            strategy_dict: 策略配置字典
            
        Returns:
            StrategyConfig对象
        """
        # 验证必需字段
        required_fields = ["name", "type", "parameters"]
        for field in required_fields:
            if field not in strategy_dict:
                raise ValueError(f"策略配置缺少必需字段: {field}")
        
        # 验证参数格式
        parameters = strategy_dict["parameters"]
        for param_name, param_value in parameters.items():
            # 检查参数值类型和范围
            if isinstance(param_value, (int, float)):
                if param_value < 0:
                    raise ValueError(f"参数值无效: {param_name} = {param_value} (不能为负数)")
            elif isinstance(param_value, str):
                # 检查字符串是否可以转换为数字
                try:
                    float(param_value)
                except ValueError:
                    if param_name.endswith("_period") or param_name in ["fast_period", "slow_period"]:
                        raise ValueError(f"参数类型无效: {param_name} = {param_value} (期望数字类型)")
            else:
                # 其他类型的参数值检查
                if param_name.endswith("_period") or param_name in ["fast_period", "slow_period"]:
                    raise ValueError(f"参数类型无效: {param_name} = {param_value} (期望数字类型)")
        
        return StrategyConfig(
            strategy_id=strategy_dict.get("name", "unknown_strategy"),
            name=strategy_dict["name"],
            version=strategy_dict.get("version", "1.0"),
            description=strategy_dict.get("description", ""),
            parameters=self._normalize_parameters(parameters),
            risk_limits=strategy_dict.get("risk_limits", {}),
            performance_metrics=strategy_dict.get("performance_metrics", {}),
            is_active=strategy_dict.get("is_active", True)
        )
    
    def _normalize_parameters(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        标准化参数格式
        
        Args:
            parameters: 原始参数字典
            
        Returns:
            标准化后的参数字典
        """
        normalized = {}
        for param_name, param_value in parameters.items():
            if isinstance(param_value, (int, float, str)):
                # 简单值，需要转换为标准格式
                if isinstance(param_value, int):
                    # 验证整数值
                    if param_value < 0:
                        raise ValueError(f"参数值无效: {param_name} = {param_value} (不能为负数)")
                    normalized[param_name] = {
                        "type": "int",
                        "min": 1,
                        "max": 1000,
                        "default": param_value
                    }
                elif isinstance(param_value, float):
                    # 验证浮点数值
                    if param_value < 0:
                        raise ValueError(f"参数值无效: {param_name} = {param_value} (不能为负数)")
                    normalized[param_name] = {
                        "type": "float",
                        "min": 0.0,
                        "max": 1.0,
                        "default": param_value
                    }
                else:
                    # 验证字符串值
                    if param_name.endswith("_period") or param_name in ["fast_period", "slow_period"]:
                        try:
                            float(param_value)
                        except ValueError:
                            raise ValueError(f"参数类型无效: {param_name} = {param_value} (期望数字类型)")
                    normalized[param_name] = {
                        "type": "string",
                        "default": param_value
                    }
            else:
                # 已经是标准格式
                normalized[param_name] = param_value
        return normalized

    async def get_strategy(self, strategy_id: str) -> Optional[StrategyConfig]:
        """
        获取策略配置

        Args:
            strategy_id: 策略ID

        Returns:
            策略配置或None
        """
        return self.data.strategies.get(strategy_id)

    async def get_all_strategies(self) -> List[StrategyConfig]:
        """
        获取所有策略配置

        Returns:
            策略配置列表
        """
        return list(self.data.strategies.values())

    async def get_active_strategies(self) -> List[StrategyConfig]:
        """
        获取所有活跃策略

        Returns:
            活跃策略配置列表
        """
        return [
            strategy for strategy in self.data.strategies.values() if strategy.is_active
        ]

    async def validate_parameters(
        self, strategy_id: str, parameters: Dict[str, Any]
    ) -> bool:
        """
        验证策略参数

        Args:
            strategy_id: 策略ID
            parameters: 参数字典

        Returns:
            验证结果
        """
        strategy = await self.get_strategy(strategy_id)
        if not strategy:
            self.logger.error("策略不存在: %s", strategy_id)
            return False

        try:
            for param_name, value in parameters.items():
                if param_name not in strategy.parameters:
                    self.logger.warning("未知参数: %s", param_name)
                    continue

                param_config = strategy.parameters[param_name]
                param_type = param_config["type"]
                min_val = param_config["min"]
                max_val = param_config["max"]

                # 类型检查
                if param_type == "int" and not isinstance(value, int):
                    self.logger.error("参数类型错误: %s 应为整数", param_name)
                    return False
                elif param_type == "float" and not isinstance(value, (int, float)):
                    self.logger.error("参数类型错误: %s 应为浮点数", param_name)
                    return False

                # 范围检查
                if value < min_val or value > max_val:
                    self.logger.error(
                        "参数超出范围: %s = %s, 范围: [%s, %s]",
                        param_name,
                        value,
                        min_val,
                        max_val,
                    )
                    return False

            return True

        except Exception as e:
            self.logger.error("参数验证失败: %s", e)
            return False

    async def record_performance(
        self, strategy_id: str, performance_data: Dict[str, Any]
    ):
        """
        记录策略性能

        Args:
            strategy_id: 策略ID
            performance_data: 性能数据
        """
        try:
            if strategy_id not in self.data.strategies:
                self.logger.error("策略不存在: %s", strategy_id)
                return

            # 添加时间戳
            performance_data["timestamp"] = datetime.now().isoformat()

            # 记录性能历史
            self.data.performance_history[strategy_id].append(performance_data)

            # 更新使用统计
            stats = self.data.usage_stats[strategy_id]
            stats["total_uses"] += 1
            stats["last_used"] = performance_data["timestamp"]

            # 更新成功/失败计数
            if performance_data.get("return", 0) > 0:
                stats["success_count"] += 1
            else:
                stats["failure_count"] += 1

            # 更新平均收益
            total_return = sum(
                p.get("return", 0) for p in self.data.performance_history[strategy_id]
            )
            stats["avg_return"] = total_return / len(
                self.data.performance_history[strategy_id]
            )

            # 限制历史记录数量
            if len(self.data.performance_history[strategy_id]) > 1000:
                self.data.performance_history[
                    strategy_id
                ] = self.data.performance_history[strategy_id][-1000:]

            self.logger.debug("已记录策略性能: %s", strategy_id)

        except Exception as e:
            self.logger.error("记录策略性能失败: %s", e)

    async def get_strategy_performance(self, strategy_id: str) -> Dict[str, Any]:
        """
        获取策略性能统计

        Args:
            strategy_id: 策略ID

        Returns:
            性能统计数据
        """
        if strategy_id not in self.data.strategies:
            return {}

        history = self.data.performance_history.get(strategy_id, [])
        stats = self.data.usage_stats.get(strategy_id, {})

        if not history:
            return stats

        # 计算性能指标
        returns = [p.get("return", 0) for p in history]

        performance = {
            "usage_stats": stats,
            "total_trades": len(history),
            "avg_return": sum(returns) / len(returns) if returns else 0,
            "max_return": max(returns) if returns else 0,
            "min_return": min(returns) if returns else 0,
            "win_rate": stats["success_count"] / stats["total_uses"]
            if stats["total_uses"] > 0
            else 0,
            "recent_performance": history[-10:] if len(history) >= 10 else history,
        }

        return performance

    async def get_recommended_strategies(
        self, market_condition: str = None
    ) -> List[str]:
        """
        获取推荐策略

        Args:
            market_condition: 市场状况 ('trending', 'ranging', 'volatile')

        Returns:
            推荐策略ID列表
        """
        active_strategies = await self.get_active_strategies()

        # 根据市场状况推荐策略
        if market_condition == "ranging":
            # 震荡市场推荐网格策略
            return [s.strategy_id for s in active_strategies if "grid" in s.strategy_id]
        elif market_condition == "trending":
            # 趋势市场推荐均线策略
            return [
                s.strategy_id for s in active_strategies if "ma_cross" in s.strategy_id
            ]
        elif market_condition == "volatile":
            # 波动市场推荐RSI策略
            return [s.strategy_id for s in active_strategies if "rsi" in s.strategy_id]
        else:
            # 默认返回所有活跃策略，按性能排序
            strategy_performance = []
            for strategy in active_strategies:
                perf = await self.get_strategy_performance(strategy.strategy_id)
                strategy_performance.append(
                    {
                        "strategy_id": strategy.strategy_id,
                        "avg_return": perf.get("avg_return", 0),
                        "win_rate": perf.get("win_rate", 0),
                    }
                )

            # 按综合评分排序
            strategy_performance.sort(
                key=lambda x: x["avg_return"] * 0.6 + x["win_rate"] * 0.4, reverse=True
            )

            return [s["strategy_id"] for s in strategy_performance]

    async def update_strategy_status(self, strategy_id: str, is_active: bool):
        """
        更新策略状态

        Args:
            strategy_id: 策略ID
            is_active: 是否活跃
        """
        if strategy_id in self.data.strategies:
            self.data.strategies[strategy_id].is_active = is_active
            self.data.strategies[strategy_id].updated_at = datetime.now().isoformat()
            self.logger.info(
                "策略状态已更新: %s -> %s", strategy_id, "活跃" if is_active else "停用"
            )
        else:
            self.logger.error("策略不存在: %s", strategy_id)

    def get_stats(self) -> Dict[str, Any]:
        """
        获取策略管理器统计信息

        Returns:
            统计信息字典
        """
        active_count = len([s for s in self.data.strategies.values() if s.is_active])
        total_uses = sum(
            stats["total_uses"] for stats in self.data.usage_stats.values()
        )

        return {
            "total_strategies": len(self.data.strategies),
            "active_strategies": active_count,
            "inactive_strategies": len(self.data.strategies) - active_count,
            "total_strategy_uses": total_uses,
            "strategy_list": list(self.data.strategies.keys()),
        }
