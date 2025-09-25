# 规则引擎 - 核心执行器
# 严格遵循全局规范：数据隔离与环境管理规范 (V1.0)

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import structlog

from .base import BaseRule
from .black_horse import BlackHorseDetector
from .potential_finder import PotentialFinder
from .three_high import ThreeHighRules

logger = structlog.get_logger(__name__)


@dataclass
class RuleResult:
    """规则执行结果"""

    rule_name: str
    passed: bool
    score: float
    metadata: Dict[str, Any]
    message: Optional[str] = None


class RuleEngine:
    """规则引擎 - 统一管理和执行所有扫描规则"""

    def __init__(self):
        self.rules: List[BaseRule] = []
        self._initialize_rules()
        logger.info("Rule engine initialized", rules_count=len(self.rules))

    def _initialize_rules(self):
        """初始化所有规则"""
        try:
            # 添加三高规则
            three_high_config = {
                "volatility_threshold": 0.05,
                "volume_threshold": 1000000,
                "correlation_threshold": 0.8,
            }
            self.rules.append(ThreeHighRules(three_high_config))

            # 添加黑马规则
            black_horse_config = {
                "min_score": 0.7,
                "news_weight": 0.4,
                "technical_weight": 0.6,
            }
            self.rules.append(BlackHorseDetector(black_horse_config))

            # 添加潜力挖掘规则
            potential_config = {
                "max_market_cap": 100000000,
                "max_price": 1.0,
                "min_volume": 50000,
            }
            self.rules.append(PotentialFinder(potential_config))

            logger.info("All rules initialized successfully")
        except Exception as e:
            logger.error("Failed to initialize rules", error=str(e))
            raise

    def execute_rules(self, symbol_data: Dict[str, Any]) -> List[RuleResult]:
        """执行所有规则"""
        results = []

        for rule in self.rules:
            try:
                result = rule.evaluate(symbol_data)
                results.append(result)
                logger.debug(
                    "Rule executed",
                    rule=rule.__class__.__name__,
                    passed=result.passed,
                    score=result.score,
                )
            except Exception as e:
                logger.error(
                    "Rule execution failed", rule=rule.__class__.__name__, error=str(e)
                )
                # 创建失败结果
                results.append(
                    RuleResult(
                        rule_name=rule.__class__.__name__,
                        passed=False,
                        score=0.0,
                        metadata={"error": str(e)},
                        message=f"Rule execution failed: {str(e)}",
                    )
                )

        return results

    def get_rule_by_name(self, rule_name: str) -> Optional[BaseRule]:
        """根据名称获取规则"""
        for rule in self.rules:
            if rule.__class__.__name__ == rule_name:
                return rule
        return None

    def add_rule(self, rule: BaseRule):
        """添加新规则"""
        self.rules.append(rule)
        logger.info("Rule added", rule=rule.__class__.__name__)

    def remove_rule(self, rule_name: str) -> bool:
        """移除规则"""
        for i, rule in enumerate(self.rules):
            if rule.__class__.__name__ == rule_name:
                del self.rules[i]
                logger.info("Rule removed", rule=rule_name)
                return True
        return False

    def get_rules_summary(self) -> Dict[str, Any]:
        """获取规则摘要"""
        return {
            "total_rules": len(self.rules),
            "rules": [rule.__class__.__name__ for rule in self.rules],
        }
