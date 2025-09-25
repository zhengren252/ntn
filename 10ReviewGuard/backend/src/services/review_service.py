#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ReviewGuard人工审核模组 - 审核服务

负责处理策略审核的核心业务逻辑：
1. 接收来自ZeroMQ的策略数据
2. 执行自动审核规则
3. 管理人工审核流程
4. 发布审核结果
"""

import os
import json
import asyncio
import logging
import uuid
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import asdict

try:
    from ..models.database import StrategyReview, ReviewDecision, AuditRule
except ImportError:
    from models.database import StrategyReview, ReviewDecision, AuditRule
from .database_service import DatabaseService
from .redis_service import RedisService
from .zeromq_service import ZeroMQService
try:
    from ..utils.risk_calculator import RiskCalculator
except ImportError:
    from utils.risk_calculator import RiskCalculator
try:
    from ..utils.logger import setup_logger
except ImportError:
    from utils.logger import setup_logger
from .report_generator import ReportGenerator

logger = setup_logger(__name__)

class ReviewStatus(Enum):
    """审核状态枚举"""
    PENDING = "pending"
    PROCESSING = "processing"
    APPROVED = "approved"
    REJECTED = "rejected"
    DEFERRED = "deferred"

class RiskLevel(Enum):
    """风险等级枚举"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class DecisionType(Enum):
    """决策类型枚举"""
    APPROVE = "approve"
    REJECT = "reject"
    DEFER = "defer"

class ReviewService:
    """审核服务类"""
    
    def __init__(self, database_service: DatabaseService, redis_service: RedisService, zeromq_service: ZeroMQService):
        self.db = database_service
        self.redis = redis_service
        self.zmq = zeromq_service
        self.risk_calculator = RiskCalculator()
        self.report_generator = ReportGenerator()
        
        # 审核配置
        self.auto_approve_threshold = float(os.getenv("AUTO_APPROVE_THRESHOLD", "0.8"))
        self.auto_reject_threshold = float(os.getenv("AUTO_REJECT_THRESHOLD", "0.3"))
        self.max_position_size = float(os.getenv("MAX_POSITION_SIZE", "0.1"))
        self.max_risk_level = os.getenv("MAX_RISK_LEVEL", "medium")
        
        # 审核规则缓存
        self._audit_rules_cache = None
        self._cache_expire_time = None
    
    async def initialize(self):
        """初始化审核服务"""
        logger.info("正在初始化审核服务")
        
        # 加载审核规则
        await self._load_audit_rules()
        
        logger.info("审核服务初始化完成")
    
    async def _load_audit_rules(self):
        """加载审核规则到缓存"""
        try:
            # 检查缓存是否过期
            if (self._cache_expire_time and 
                datetime.now() < self._cache_expire_time and 
                self._audit_rules_cache):
                return
            
            # 从数据库加载规则
            rules = await self.db.get_audit_rules()
            self._audit_rules_cache = rules
            self._cache_expire_time = datetime.now() + timedelta(minutes=10)
            
            logger.info(f"已加载 {len(rules)} 条审核规则")
            
        except Exception as e:
            logger.error(f"加载审核规则失败: {e}")
            self._audit_rules_cache = []
    
    async def submit_strategy_for_review(self, strategy_data: Dict[str, Any]) -> str:
        """提交策略进行审核"""
        try:
            logger.info(f"收到策略审核请求: {strategy_data.get('strategy_id')}")
            
            # 数据验证
            if not self._validate_strategy_data(strategy_data):
                raise ValueError("策略数据验证失败")
            
            # 风险评估
            risk_assessment = await self._assess_strategy_risk(strategy_data)
            strategy_data['risk_assessment'] = risk_assessment
            
            # 创建审核记录
            review_id = await self.db.create_strategy_review(strategy_data)
            
            # 缓存策略数据
            await self.redis.cache_strategy_data(
                strategy_data.get('strategy_id'), 
                strategy_data
            )
            
            # 执行自动审核
            auto_decision = await self._auto_review(review_id, strategy_data)
            
            if auto_decision:
                # 自动审核通过，直接处理结果
                await self._process_review_decision(
                    review_id, 
                    auto_decision['decision'], 
                    auto_decision['reason'],
                    reviewer_id="system"
                )
            else:
                # 需要人工审核，加入队列
                await self._queue_for_manual_review(review_id, strategy_data)
            
            # 更新统计
            await self.redis.increment_counter("total_reviews")
            
            logger.info(f"策略审核请求已处理: {review_id}")
            return review_id
            
        except Exception as e:
            logger.error(f"提交策略审核失败: {e}")
            raise
    
    def _validate_strategy_data(self, strategy_data: Dict[str, Any]) -> bool:
        """验证策略数据"""
        required_fields = [
            'strategy_id', 'symbol', 'strategy_type', 
            'expected_return', 'max_drawdown'
        ]
        
        for field in required_fields:
            if field not in strategy_data:
                logger.error(f"缺少必需字段: {field}")
                return False
        
        # 数值范围验证
        if not (0 <= strategy_data.get('expected_return', 0) <= 1):
            logger.error("预期收益率超出有效范围")
            return False
        
        if not (0 <= strategy_data.get('max_drawdown', 0) <= 1):
            logger.error("最大回撤超出有效范围")
            return False
        
        return True
    
    async def _assess_strategy_risk(self, strategy_data: Dict[str, Any]) -> Dict[str, Any]:
        """评估策略风险"""
        try:
            # 基础风险指标
            expected_return = strategy_data.get('expected_return', 0)
            max_drawdown = strategy_data.get('max_drawdown', 0)
            position_size = strategy_data.get('position_size', 0.05)
            
            # 计算风险评分
            volatility_score = self._calculate_volatility_score(strategy_data)
            liquidity_score = self._calculate_liquidity_score(strategy_data)
            correlation_risk = self._calculate_correlation_risk(strategy_data)
            
            # 综合风险评分
            risk_score = (
                volatility_score * 0.4 + 
                liquidity_score * 0.3 + 
                correlation_risk * 0.3
            )
            
            # 确定风险等级
            if risk_score >= 0.7:
                risk_level = RiskLevel.HIGH.value
            elif risk_score >= 0.4:
                risk_level = RiskLevel.MEDIUM.value
            else:
                risk_level = RiskLevel.LOW.value
            
            risk_assessment = {
                'risk_score': risk_score,
                'risk_level': risk_level,
                'volatility_score': volatility_score,
                'liquidity_score': liquidity_score,
                'correlation_risk': correlation_risk,
                'position_size': position_size,
                'sharpe_ratio': expected_return / max(max_drawdown, 0.01),
                'assessed_at': datetime.now().isoformat()
            }
            
            logger.info(f"风险评估完成: {risk_level} (评分: {risk_score:.3f})")
            return risk_assessment
            
        except Exception as e:
            logger.error(f"风险评估失败: {e}")
            return {
                'risk_score': 0.5,
                'risk_level': RiskLevel.MEDIUM.value,
                'error': str(e)
            }
    
    def _calculate_volatility_score(self, strategy_data: Dict[str, Any]) -> float:
        """计算波动率评分"""
        max_drawdown = strategy_data.get('max_drawdown', 0)
        
        # 基于最大回撤计算波动率评分
        if max_drawdown > 0.2:
            return 0.9
        elif max_drawdown > 0.1:
            return 0.6
        elif max_drawdown > 0.05:
            return 0.3
        else:
            return 0.1
    
    def _calculate_liquidity_score(self, strategy_data: Dict[str, Any]) -> float:
        """计算流动性评分"""
        symbol = strategy_data.get('symbol', '')
        
        # 主要货币对流动性较好
        major_pairs = ['EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'AUDUSD', 'USDCAD']
        
        if symbol in major_pairs:
            return 0.1
        elif 'USD' in symbol:
            return 0.3
        else:
            return 0.7
    
    def _calculate_correlation_risk(self, strategy_data: Dict[str, Any]) -> float:
        """计算相关性风险"""
        # 简化的相关性风险计算
        # 实际应用中需要与现有持仓进行相关性分析
        strategy_type = strategy_data.get('strategy_type', '')
        
        if strategy_type in ['trend_following', 'momentum']:
            return 0.6
        elif strategy_type in ['mean_reversion', 'arbitrage']:
            return 0.3
        else:
            return 0.5
    
    async def _auto_review(self, review_id: str, strategy_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """自动审核逻辑"""
        try:
            await self._load_audit_rules()
            
            risk_assessment = strategy_data.get('risk_assessment', {})
            risk_score = risk_assessment.get('risk_score', 0.5)
            risk_level = risk_assessment.get('risk_level', 'medium')
            position_size = strategy_data.get('position_size', 0.05)
            
            # 应用审核规则
            for rule in self._audit_rules_cache:
                if not rule.get('is_active', True):
                    continue
                
                try:
                    conditions = json.loads(rule.get('conditions', '{}'))
                    
                    if self._evaluate_rule_conditions(conditions, strategy_data, risk_assessment):
                        rule_type = rule.get('rule_type')
                        action = rule.get('action')
                        
                        if rule_type == 'auto_approve':
                            return {
                                'decision': DecisionType.APPROVE.value,
                                'reason': f"自动通过: {rule.get('rule_name')}",
                                'rule_id': rule.get('id')
                            }
                        elif rule_type == 'auto_reject':
                            return {
                                'decision': DecisionType.REJECT.value,
                                'reason': f"自动拒绝: {rule.get('rule_name')}",
                                'rule_id': rule.get('id')
                            }
                        elif rule_type == 'require_review':
                            # 需要人工审核，返回None
                            return None
                            
                except Exception as e:
                    logger.error(f"规则评估失败 {rule.get('id')}: {e}")
                    continue
            
            # 默认阈值检查
            if risk_score <= self.auto_approve_threshold and risk_level == 'low':
                return {
                    'decision': DecisionType.APPROVE.value,
                    'reason': f"低风险自动通过 (评分: {risk_score:.3f})"
                }
            elif risk_score >= self.auto_reject_threshold or position_size > self.max_position_size:
                return {
                    'decision': DecisionType.REJECT.value,
                    'reason': f"高风险自动拒绝 (评分: {risk_score:.3f}, 仓位: {position_size:.3f})"
                }
            
            # 需要人工审核
            return None
            
        except Exception as e:
            logger.error(f"自动审核失败: {e}")
            return None
    
    def _evaluate_rule_conditions(self, conditions: Dict[str, Any], 
                                 strategy_data: Dict[str, Any], 
                                 risk_assessment: Dict[str, Any]) -> bool:
        """评估规则条件"""
        try:
            # 合并数据用于条件评估
            eval_data = {**strategy_data, **risk_assessment}
            
            for field, condition in conditions.items():
                if field not in eval_data:
                    continue
                
                value = eval_data[field]
                
                if isinstance(condition, dict):
                    # 复杂条件 (如 {">": 0.5, "<": 0.8})
                    for op, threshold in condition.items():
                        if not self._evaluate_condition(value, op, threshold):
                            return False
                else:
                    # 简单相等条件
                    if value != condition:
                        return False
            
            return True
            
        except Exception as e:
            logger.error(f"条件评估失败: {e}")
            return False
    
    def _evaluate_condition(self, value: Any, operator: str, threshold: Any) -> bool:
        """评估单个条件"""
        try:
            if operator == ">":
                return float(value) > float(threshold)
            elif operator == ">=":
                return float(value) >= float(threshold)
            elif operator == "<":
                return float(value) < float(threshold)
            elif operator == "<=":
                return float(value) <= float(threshold)
            elif operator == "==":
                return value == threshold
            elif operator == "!=":
                return value != threshold
            elif operator == "in":
                return value in threshold
            elif operator == "not_in":
                return value not in threshold
            else:
                return False
        except (ValueError, TypeError):
            return False
    
    async def _queue_for_manual_review(self, review_id: str, strategy_data: Dict[str, Any]):
        """加入人工审核队列"""
        try:
            # 更新状态为处理中
            await self.db.update_review_status(review_id, ReviewStatus.PROCESSING.value)
            
            # 加入Redis队列
            queue_item = {
                'review_id': review_id,
                'strategy_id': strategy_data.get('strategy_id'),
                'priority': self._calculate_review_priority(strategy_data),
                'queued_at': datetime.now().isoformat()
            }
            
            await self.redis.push_to_queue("pending_reviews", queue_item)
            
            logger.info(f"策略已加入人工审核队列: {review_id}")
            
        except Exception as e:
            logger.error(f"加入审核队列失败: {e}")
            raise
    
    def _calculate_review_priority(self, strategy_data: Dict[str, Any]) -> int:
        """计算审核优先级"""
        risk_assessment = strategy_data.get('risk_assessment', {})
        risk_score = risk_assessment.get('risk_score', 0.5)
        position_size = strategy_data.get('position_size', 0.05)
        
        # 高风险和大仓位优先审核
        priority = int(risk_score * 50 + position_size * 100)
        return min(priority, 100)
    
    async def _process_review_decision(self, review_id: str, decision: str, 
                                     reason: str, reviewer_id: str = "system",
                                     risk_adjustment: Dict[str, Any] = None):
        """处理审核决策"""
        try:
            # 创建决策记录
            decision_data = {
                'strategy_review_id': review_id,
                'reviewer_id': reviewer_id,
                'decision': decision,
                'reason': reason,
                'risk_adjustment': risk_adjustment or {}
            }
            
            decision_id = await self.db.create_review_decision(decision_data)
            
            # 更新审核状态
            if decision == DecisionType.APPROVE.value:
                await self.db.update_review_status(review_id, ReviewStatus.APPROVED.value)
                await self.redis.increment_counter("approved_reviews")
            elif decision == DecisionType.REJECT.value:
                await self.db.update_review_status(review_id, ReviewStatus.REJECTED.value)
                await self.redis.increment_counter("rejected_reviews")
            else:
                await self.db.update_review_status(review_id, ReviewStatus.DEFERRED.value)
            
            # 缓存审核结果
            result = {
                'review_id': review_id,
                'decision': decision,
                'reason': reason,
                'decision_id': decision_id,
                'processed_at': datetime.now().isoformat()
            }
            
            await self.redis.cache_review_result(review_id, result)
            
            # 当为自动/系统批准时，发布到下游模组（附带报告）
            if decision == DecisionType.APPROVE.value:
                try:
                    review = await self.db.get_strategy_review(review_id)
                    report_data = None
                    try:
                        raw = json.loads(review.raw_data) if getattr(review, 'raw_data', None) else {}
                        params = json.loads(review.parameters) if getattr(review, 'parameters', None) else raw.get('parameters', {})
                        input_data = {
                            'strategy_id': review.strategy_id,
                            'strategy_name': review.strategy_name,
                            'strategy_type': getattr(review, 'strategy_type', None) or raw.get('strategy_type', 'unknown'),
                            'parameters': params,
                            'expected_return': getattr(review, 'expected_return', None) or raw.get('expected_return'),
                            'risk_assessment': {
                                'risk_level': getattr(review, 'risk_level', None) or raw.get('risk_level'),
                                'max_drawdown': getattr(review, 'max_drawdown', None) or raw.get('max_drawdown')
                            },
                            'performance': raw.get('performance')
                        }
                        report_obj = self.report_generator.generate(input_data)
                        report_html = self.report_generator.generate_html(report_obj)
                        report_data = {'report': report_obj, 'report_html': report_html}
                    except Exception as gen_err:
                        logger.error(f"生成报告失败: {gen_err}")
                        report_data = None
            
                    await self.zmq.publish_approved_strategy(review, decision_data, report_data)
                except Exception as pub_err:
                    logger.error(f"发布批准策略到ZMQ失败: {pub_err}")
            
            logger.info(f"审核决策已处理: {review_id} -> {decision}")
            return result
            
        except Exception as e:
            logger.error(f"处理审核决策失败: {e}")
            raise
    
    async def manual_review(self, review_id: str, reviewer_id: str, 
                           decision: str, reason: str, 
                           risk_adjustment: Dict[str, Any] = None) -> Dict[str, Any]:
        """人工审核"""
        try:
            logger.info(f"开始人工审核: {review_id} by {reviewer_id}")
            
            # 验证决策类型
            if decision not in [d.value for d in DecisionType]:
                raise ValueError(f"无效的决策类型: {decision}")
            
            # 处理审核决策
            result = await self._process_review_decision(
                review_id, decision, reason, reviewer_id, risk_adjustment
            )
            
            logger.info(f"人工审核完成: {review_id}")
            return result
            
        except Exception as e:
            logger.error(f"人工审核失败: {e}")
            raise
    
    async def process_incoming_strategy(self, strategy_data: Dict[str, Any]) -> bool:
        """处理来自优化模组的策略数据"""
        try:
            logger.info(f"处理新策略: {strategy_data.get('strategy_id')}")
            
            # 创建策略审核记录
            review = StrategyReview(
                strategy_id=strategy_data['strategy_id'],
                strategy_name=strategy_data['strategy_name'],
                strategy_type=strategy_data.get('strategy_type', 'unknown'),
                parameters=json.dumps(strategy_data.get('parameters', {})),
                expected_return=strategy_data.get('expected_return', 0.0),
                risk_level=strategy_data.get('risk_level', 'medium'),
                max_drawdown=strategy_data.get('max_drawdown', 0.0),
                status='pending',
                raw_data=json.dumps(strategy_data),
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            # 保存到数据库
            if await self.db.create_strategy_review(review):
                logger.info(f"策略审核记录已创建: {review.strategy_id}")
                
                # 缓存到Redis
                await self.redis.cache_strategy_review(review)
                
                # 执行自动审核规则
                await self.apply_auto_review_rules(review)
                
                return True
            else:
                logger.error(f"创建策略审核记录失败: {strategy_data.get('strategy_id')}")
                return False
                
        except Exception as e:
            logger.error(f"处理策略数据时发生错误: {e}")
            return False
    
    async def apply_auto_review_rules(self, review: StrategyReview) -> None:
        """应用自动审核规则"""
        try:
            logger.info(f"应用自动审核规则: {review.strategy_id}")
            
            # 获取审核规则
            rules = await self.db.get_active_audit_rules()
            
            auto_approved = False
            auto_rejected = False
            rejection_reason = None
            approval_reason = None
            
            for rule in rules:
                rule_config = json.loads(rule.rule_config)
                
                # 检查风险等级规则
                if rule.rule_type == 'risk_level':
                    if self._check_risk_level_rule(review, rule_config):
                        if rule_config.get('action') == 'auto_approve':
                            auto_approved = True
                            approval_reason = f"自动审核通过: {rule.rule_name}"
                        elif rule_config.get('action') == 'auto_reject':
                            auto_rejected = True
                            rejection_reason = f"自动拒绝: {rule.rule_name}"
                
                # 检查收益率规则
                elif rule.rule_type == 'return_threshold':
                    if self._check_return_threshold_rule(review, rule_config):
                        if rule_config.get('action') == 'auto_reject':
                            auto_rejected = True
                            rejection_reason = f"自动拒绝: {rule.rule_name}"
                
                # 检查回撤规则
                elif rule.rule_type == 'drawdown_limit':
                    if self._check_drawdown_rule(review, rule_config):
                        if rule_config.get('action') == 'auto_reject':
                            auto_rejected = True
                            rejection_reason = f"自动拒绝: {rule.rule_name}"
            
            # 执行自动决策
            if auto_rejected:
                await self._auto_reject_strategy(review, rejection_reason)
            elif auto_approved:
                await self._auto_approve_strategy(review, approval_reason)
            else:
                # 需要人工审核
                await self._mark_for_manual_review(review)
                
        except Exception as e:
            logger.error(f"应用自动审核规则时发生错误: {e}")
    
    async def _auto_approve_strategy(self, review: StrategyReview, reason: str = '自动审核通过') -> None:
        """自动批准策略"""
        try:
            # 更新状态：数据库以审核记录id为键
            await self.db.update_strategy_review_status(review.strategy_id, 'approved')
            
            # 创建决策记录
            decision = ReviewDecision(
                id=f"decision_{uuid.uuid4().hex[:8]}",
                strategy_review_id=review.id,
                reviewer_id='system',
                decision='approve',
                reason=reason
            )
            await self.db.create_review_decision(decision)
            
            # 生成三页式报告（容错）
            report_data = None
            try:
                raw = json.loads(review.raw_data) if getattr(review, 'raw_data', None) else {}
                params = json.loads(review.parameters) if getattr(review, 'parameters', None) else raw.get('parameters', {})
                input_data = {
                    'strategy_id': review.strategy_id,
                    'strategy_name': review.strategy_name,
                    'strategy_type': getattr(review, 'strategy_type', None) or raw.get('strategy_type', 'unknown'),
                    'parameters': params,
                    'expected_return': getattr(review, 'expected_return', None) or raw.get('expected_return'),
                    'risk_assessment': {
                        'risk_level': getattr(review, 'risk_level', None) or raw.get('risk_level'),
                        'max_drawdown': getattr(review, 'max_drawdown', None) or raw.get('max_drawdown')
                    },
                    'performance': raw.get('performance')
                }
                report_obj = self.report_generator.generate(input_data)
                report_html = self.report_generator.generate_html(report_obj)
                report_data = {'report': report_obj, 'report_html': report_html}
            except Exception as gen_err:
                logger.error(f"生成报告失败: {gen_err}")
                report_data = None
            
            # 发布到下游模组（携带报告）
            await self.zmq.publish_approved_strategy(review, asdict(decision), report_data)
            
            logger.info(f"策略自动批准: {review.strategy_id}")
            
        except Exception as e:
            logger.error(f"自动批准策略时发生错误: {e}")
    
    async def _auto_reject_strategy(self, review: StrategyReview, reason: str) -> None:
        """自动拒绝策略"""
        try:
            # 更新状态
            await self.db.update_strategy_review_status(review.strategy_id, 'rejected')
            
            # 创建决策记录
            decision = ReviewDecision(
                id=f"decision_{uuid.uuid4().hex[:8]}",
                strategy_review_id=review.id,
                reviewer_id='system',
                decision='reject',
                reason=reason
            )
            await self.db.create_review_decision(decision)
            
            logger.info(f"策略自动拒绝: {review.strategy_id}, 原因: {reason}")
            
        except Exception as e:
            logger.error(f"自动拒绝策略时发生错误: {e}")
    
    async def _mark_for_manual_review(self, review: StrategyReview) -> None:
        """标记为需要人工审核"""
        try:
            # 更新状态为处理中
            await self.db.update_strategy_review_status(review.strategy_id, 'processing')
            
            # 添加到Redis队列
            await self.redis.add_to_review_queue(review)
            
            logger.info(f"策略标记为人工审核: {review.strategy_id}")
            
        except Exception as e:
            logger.error(f"标记人工审核时发生错误: {e}")
    
    async def submit_manual_decision(self, strategy_id: str, reviewer_id: str, decision: str, reason: str = None, risk_adjustment: Dict = None) -> bool:
        """提交人工审核决策
        
        参数:
            strategy_id: 这里表示审核记录ID（review_id），保持与API路径参数一致；为兼容旧命名暂不改名。
        返回：
            True 表示提交成功；False 表示失败/不存在
        """
        try:
            logger.info(f"提交人工审核决策: {strategy_id}, 决策: {decision}")
            
            # 获取策略审核记录（兼容不同实现）
            review_getter = None
            if hasattr(self.db, 'get_strategy_review_by_id'):
                review_getter = getattr(self.db, 'get_strategy_review_by_id')
            elif hasattr(self.db, 'get_strategy_review'):
                review_getter = getattr(self.db, 'get_strategy_review')
            else:
                logger.error("数据库接口缺少获取审核记录方法: get_strategy_review_by_id/get_strategy_review")
                return False

            review = review_getter(strategy_id) if not asyncio.iscoroutinefunction(review_getter) else await review_getter(strategy_id)
            if not review:
                logger.error(f"策略审核记录不存在: {strategy_id}")
                return False
            
            # 创建决策记录
            review_decision = ReviewDecision(
                id=f"decision_{uuid.uuid4().hex[:8]}",
                strategy_review_id=strategy_id,
                reviewer_id=reviewer_id,
                decision=decision,
                reason=reason,
                risk_adjustment=json.dumps(risk_adjustment) if risk_adjustment else None
            )
            
            # 保存决策
            created = await self.db.create_review_decision(review_decision)
            if not created:
                logger.error(f"保存审核决策失败: {strategy_id}")
                return False

            # 更新策略状态
            new_status = 'approved' if decision == 'approve' else 'rejected' if decision == 'reject' else 'deferred'
            await self.db.update_strategy_review_status(strategy_id, new_status)
            
            # 如果批准，发布到下游模组（附带报告）
            if decision == 'approve':
                report_data = None
                try:
                    raw = json.loads(review.raw_data) if getattr(review, 'raw_data', None) else {}
                    params = json.loads(review.parameters) if getattr(review, 'parameters', None) else raw.get('parameters', {})
                    input_data = {
                        'strategy_id': getattr(review, 'strategy_id', None) or (review.get('strategy_id') if isinstance(review, dict) else None),
                        'strategy_name': getattr(review, 'strategy_name', None) or (review.get('strategy_name') if isinstance(review, dict) else None),
                        'strategy_type': getattr(review, 'strategy_type', None) or (review.get('strategy_type') if isinstance(review, dict) else 'unknown'),
                        'parameters': params,
                        'expected_return': getattr(review, 'expected_return', None) or (review.get('expected_return') if isinstance(review, dict) else None),
                        'risk_assessment': {
                            'risk_level': getattr(review, 'risk_level', None) or (review.get('risk_level') if isinstance(review, dict) else None),
                            'max_drawdown': getattr(review, 'max_drawdown', None) or (review.get('max_drawdown') if isinstance(review, dict) else None)
                        },
                        'performance': (review.get('performance') if isinstance(review, dict) else None)
                    }
                    report_obj = self.report_generator.generate(input_data)
                    report_html = self.report_generator.generate_html(report_obj)
                    report_data = {'report': report_obj, 'report_html': report_html}
                except Exception as gen_err:
                    logger.error(f"生成报告失败: {gen_err}")
                    report_data = None

                await self.zmq.publish_approved_strategy(review, asdict(review_decision), report_data)
            
            return True
            
        except Exception as e:
            logger.error(f"提交人工审核决策时发生错误: {e}")
            return False
    
    async def get_pending_reviews(self, page: int = 1, limit: int = 20, filters: Dict = None) -> Dict[str, Any]:
        """获取待审核策略列表"""
        try:
            offset = (page - 1) * limit
            
            # 从数据库获取待审核策略
            reviews = await self.db.get_strategy_reviews(
                status='processing',
                limit=limit,
                offset=offset,
                filters=filters
            )
            
            # 获取总数
            total = await self.db.count_strategy_reviews(status='processing', filters=filters)
            
            return {
                'reviews': [asdict(review) for review in reviews],
                'total': total,
                'page': page,
                'limit': limit,
                'total_pages': (total + limit - 1) // limit
            }
            
        except Exception as e:
            logger.error(f"获取待审核策略列表时发生错误: {e}")
            return {'reviews': [], 'total': 0, 'page': page, 'limit': limit, 'total_pages': 0}
    
    async def get_review_history(self, page: int = 1, limit: int = 20, filters: Dict = None) -> Dict[str, Any]:
        """获取审核历史"""
        try:
            offset = (page - 1) * limit
            
            # 从数据库获取审核历史
            decisions = await self.db.get_review_decisions(
                limit=limit,
                offset=offset,
                filters=filters
            )
            
            # 获取总数
            total = await self.db.count_review_decisions(filters=filters)
            
            return {
                'decisions': [asdict(decision) for decision in decisions],
                'total': total,
                'page': page,
                'limit': limit,
                'total_pages': (total + limit - 1) // limit
            }
            
        except Exception as e:
            logger.error(f"获取审核历史时发生错误: {e}")
            return {'decisions': [], 'total': 0, 'page': page, 'limit': limit, 'total_pages': 0}
    
    async def get_system_statistics(self) -> Dict[str, Any]:
        """获取系统统计信息"""
        try:
            # 获取各状态的策略数量
            pending_count = await self.db.count_strategy_reviews(status='pending')
            processing_count = await self.db.count_strategy_reviews(status='processing')
            approved_count = await self.db.count_strategy_reviews(status='approved')
            rejected_count = await self.db.count_strategy_reviews(status='rejected')
            
            # 获取今日统计
            today = datetime.now().date()
            today_approved = await self.db.count_strategy_reviews(
                status='approved',
                date_filter={'start': today, 'end': today + timedelta(days=1)}
            )
            today_rejected = await self.db.count_strategy_reviews(
                status='rejected',
                date_filter={'start': today, 'end': today + timedelta(days=1)}
            )
            
            return {
                'total_reviews': pending_count + processing_count + approved_count + rejected_count,
                'pending_reviews': pending_count,
                'processing_reviews': processing_count,
                'approved_reviews': approved_count,
                'rejected_reviews': rejected_count,
                'today_approved': today_approved,
                'today_rejected': today_rejected,
                'approval_rate': approved_count / max(approved_count + rejected_count, 1) * 100
            }
            
        except Exception as e:
            logger.error(f"获取系统统计信息时发生错误: {e}")
            return {}
    
    async def get_pending_reviews_old(self, limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
        """获取待审核策略列表（旧版本）"""
        try:
            # 从数据库获取待审核策略
            reviews = await self.db.get_strategy_reviews(
                status='processing',
                limit=limit,
                offset=offset
            )
            
            return [asdict(review) for review in reviews]
            
        except Exception as e:
            logger.error(f"获取待审核策略列表时发生错误: {e}")
            return []
    
    def _check_risk_level_rule(self, review: StrategyReview, rule_config: Dict[str, Any]) -> bool:
        """检查风险等级规则"""
        try:
            # 解析策略数据
            strategy_data = json.loads(review.raw_data) if review.raw_data else {}
            risk_assessment = strategy_data.get('risk_assessment', {})
            
            # 检查风险等级
            if 'risk_level' in rule_config:
                required_risk_level = rule_config['risk_level']
                actual_risk_level = risk_assessment.get('risk_level', review.risk_level)
                if actual_risk_level != required_risk_level:
                    return False
            
            # 检查仓位大小
            if 'position_size_max' in rule_config:
                max_position = rule_config['position_size_max']
                actual_position = strategy_data.get('position_size', 0.05)
                if actual_position > max_position:
                    return False
            
            if 'position_size_min' in rule_config:
                min_position = rule_config['position_size_min']
                actual_position = strategy_data.get('position_size', 0.05)
                if actual_position < min_position:
                    return False
            
            # 检查风险评分
            if 'risk_score_max' in rule_config:
                max_score = rule_config['risk_score_max']
                actual_score = risk_assessment.get('risk_score', 0.5)
                if actual_score > max_score:
                    return False
            
            # 检查策略类型
            if 'strategy_type' in rule_config:
                required_type = rule_config['strategy_type']
                actual_type = strategy_data.get('strategy_type', review.strategy_type)
                if actual_type != required_type:
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"检查风险等级规则时发生错误: {e}")
            return False
    
    def _check_return_threshold_rule(self, review: StrategyReview, rule_config: Dict[str, Any]) -> bool:
        """检查收益率阈值规则"""
        try:
            strategy_data = json.loads(review.raw_data) if review.raw_data else {}
            
            if 'min_return' in rule_config:
                min_return = rule_config['min_return']
                actual_return = review.expected_return or strategy_data.get('expected_return', 0)
                if actual_return < min_return:
                    return True  # 触发规则（通常是拒绝）
            
            return False
            
        except Exception as e:
            logger.error(f"检查收益率阈值规则时发生错误: {e}")
            return False
    
    def _check_drawdown_rule(self, review: StrategyReview, rule_config: Dict[str, Any]) -> bool:
        """检查回撤规则"""
        try:
            strategy_data = json.loads(review.raw_data) if review.raw_data else {}
            
            if 'max_drawdown' in rule_config:
                max_allowed_drawdown = rule_config['max_drawdown']
                actual_drawdown = review.max_drawdown or strategy_data.get('max_drawdown', 0)
                if actual_drawdown > max_allowed_drawdown:
                    return True  # 触发规则（通常是拒绝）
            
            return False
            
        except Exception as e:
            logger.error(f"检查回撤规则时发生错误: {e}")
            return False