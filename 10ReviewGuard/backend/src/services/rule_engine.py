#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
规则引擎模块
负责处理自动审核规则的执行和决策
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import asdict

try:
    from ..models.database import DatabaseManager, StrategyReview, AuditRule
except ImportError:
    from models.database import DatabaseManager, StrategyReview, AuditRule
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


class RuleEngine:
    """规则引擎类"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.rules_cache = {}
        self.cache_timestamp = None
    
    def process_strategy(self, strategy_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理策略数据，执行规则引擎逻辑"""
        try:
            logger.info(f"开始处理策略: {strategy_data.get('strategy_id')}")
            
            # 创建策略审核记录
            review = self._create_strategy_review(strategy_data)
            
            # 获取适用的审核规则
            applicable_rules = self._get_applicable_rules(strategy_data)
            
            # 执行规则评估
            decision = self._evaluate_rules(strategy_data, applicable_rules)
            
            # 处理决策结果
            result = self._process_decision(review, decision, strategy_data)
            
            logger.info(f"策略处理完成: {strategy_data.get('strategy_id')}, 决策: {decision['action']}")
            return result
            
        except Exception as e:
            logger.error(f"处理策略失败: {e}")
            raise
    
    def _create_strategy_review(self, strategy_data: Dict[str, Any]) -> StrategyReview:
        """创建策略审核记录"""
        review = StrategyReview(
            id=f"review_{strategy_data.get('strategy_id')}_{int(datetime.now().timestamp())}",
            strategy_id=strategy_data.get('strategy_id'),
            symbol=strategy_data.get('symbol'),
            strategy_type=strategy_data.get('strategy_type'),
            expected_return=strategy_data.get('expected_return', 0.0),
            max_drawdown=strategy_data.get('max_drawdown', 0.0),
            risk_level=strategy_data.get('risk_level', 'medium'),
            status='pending',
            raw_data=strategy_data
        )
        
        # 保存到数据库
        created_review = self.db_manager.create_strategy_review(review)
        return created_review
    
    def _get_applicable_rules(self, strategy_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """获取适用于当前策略的审核规则"""
        try:
            # 从数据库获取所有活跃规则
            all_rules = self.db_manager.get_audit_rules()
            applicable_rules = []
            
            for rule in all_rules:
                if self._rule_matches_strategy(rule, strategy_data):
                    applicable_rules.append(rule)
            
            logger.info(f"找到 {len(applicable_rules)} 条适用规则")
            return applicable_rules
            
        except Exception as e:
            logger.error(f"获取审核规则失败: {e}")
            return []
    
    def _rule_matches_strategy(self, rule: Dict[str, Any], strategy_data: Dict[str, Any]) -> bool:
        """检查规则是否适用于策略"""
        try:
            conditions = rule.get('conditions', {})
            
            # 检查每个条件
            for field, expected_value in conditions.items():
                strategy_value = strategy_data.get(field)
                
                if isinstance(expected_value, dict):
                    # 处理范围条件
                    if 'min' in expected_value and strategy_value < expected_value['min']:
                        return False
                    if 'max' in expected_value and strategy_value > expected_value['max']:
                        return False
                elif strategy_value != expected_value:
                    # 处理精确匹配条件
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"规则匹配检查失败: {e}")
            return False
    
    def _evaluate_rules(self, strategy_data: Dict[str, Any], rules: List[Dict[str, Any]]) -> Dict[str, Any]:
        """评估规则并做出决策"""
        # 按优先级排序规则
        sorted_rules = sorted(rules, key=lambda x: x.get('priority', 0), reverse=True)
        
        for rule in sorted_rules:
            action = rule.get('action')
            
            if action == 'approve':
                return {
                    'action': 'approve',
                    'reason': f"符合自动批准规则: {rule.get('name')}",
                    'rule_id': rule.get('id'),
                    'reviewer': 'auto'
                }
            elif action == 'reject':
                return {
                    'action': 'reject',
                    'reason': f"符合自动拒绝规则: {rule.get('name')}",
                    'rule_id': rule.get('id'),
                    'reviewer': 'auto'
                }
            elif action == 'manual_review':
                return {
                    'action': 'manual_review',
                    'reason': f"符合人工审核规则: {rule.get('name')}",
                    'rule_id': rule.get('id'),
                    'status': 'pending_manual_review'
                }
        
        # 默认需要人工审核
        return {
            'action': 'manual_review',
            'reason': '未匹配到自动处理规则，需要人工审核',
            'status': 'pending_manual_review'
        }
    
    def _process_decision(self, review: StrategyReview, decision: Dict[str, Any], strategy_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理决策结果"""
        action = decision['action']
        
        if action == 'approve':
            # 自动批准，发送到下游
            self._send_approved_strategy(strategy_data, decision)
            # 更新审核状态
            self.db_manager.update_strategy_review_status(review.id, 'approved')
            
        elif action == 'reject':
            # 自动拒绝，更新状态
            self.db_manager.update_strategy_review_status(review.id, 'rejected')
            
        elif action == 'manual_review':
            # 需要人工审核，更新状态
            status = decision.get('status', 'pending_manual_review')
            self.db_manager.update_strategy_review_status(review.id, status)
        
        return decision
    
    def _send_approved_strategy(self, strategy_data: Dict[str, Any], decision: Dict[str, Any]):
        """发送已批准的策略到下游系统"""
        try:
            # 添加审核信息
            strategy_with_review = strategy_data.copy()
            strategy_with_review['review_info'] = {
                'reviewer': decision.get('reviewer', 'auto'),
                'action': decision['action'],
                'reason': decision.get('reason'),
                'timestamp': datetime.now().isoformat()
            }
            
            # 这里应该通过ZMQ发送消息，但在测试中会被mock
            logger.info(f"发送已批准策略到下游: {strategy_data.get('strategy_id')}")
            
            # 模拟ZMQ发布，优先使用src路径以匹配测试的patch目标
            try:
                from src.services.zmq_service import ZMQService  # 优先匹配测试桩
            except ImportError:
                try:
                    from ..services.zmq_service import ZMQService  # 包内相对导入
                except Exception:
                    from services.zmq_service import ZMQService  # 直接导入
            
            zmq_service = ZMQService()
            publisher = zmq_service.get_publisher()
            if publisher:
                publisher.send_message('review.pool.approved', strategy_with_review)
            
        except Exception as e:
            logger.error(f"发送已批准策略失败: {e}")
    
    def get_rule_statistics(self) -> Dict[str, Any]:
        """获取规则执行统计信息"""
        try:
            # 这里可以添加规则执行统计逻辑
            return {
                'total_rules': len(self.db_manager.get_audit_rules()),
                'active_rules': len([r for r in self.db_manager.get_audit_rules() if r.get('is_active')]),
                'last_updated': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"获取规则统计失败: {e}")