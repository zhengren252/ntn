#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
端到端测试 (End-to-End Testing)
验证【人工审核模组】与【前端管理界面】的协同工作能力

测试用例：E2E-REVIEW-01 - 人工审核完整操作流程
"""

import pytest
import requests
import time
import json
import zmq
import threading
from datetime import datetime
from typing import Dict, Any, List


class TestE2EReview:
    """端到端测试类"""
    
    @pytest.fixture(scope="class")
    def setup_e2e_env(self):
        """设置端到端测试环境"""
        # 测试配置
        config = {
            "frontend_url": "http://localhost:3000",
            "backend_url": "http://localhost:8000",
            "zmq_pub_port": 5556,
            "zmq_sub_port": 5555
        }
        
        # 验证服务是否运行
        self._verify_services_running(config)
        
        yield config
    
    def _verify_services_running(self, config: Dict[str, Any]):
        """验证所有必要的服务是否正在运行"""
        try:
            # 检查后端API
            response = requests.get(f"{config['backend_url']}/health", timeout=5)
            assert response.status_code == 200, "后端服务未运行"
            
            # 检查前端服务
            response = requests.get(config["frontend_url"], timeout=5)
            assert response.status_code == 200, "前端服务未运行"
            
        except requests.exceptions.RequestException as e:
            pytest.skip(f"服务未运行，跳过E2E测试: {e}")
    
    def test_e2e_review_01_complete_manual_review_flow(self, setup_e2e_env):
        """
        E2E-REVIEW-01: 人工审核完整操作流程
        
        测试步骤：
        1. 模拟策略优化模组发布需要人工审核的策略
        2. 通过前端API验证待审列表中显示该策略
        3. 模拟前端提交审核决策
        4. 验证审核历史记录
        5. 验证下游系统收到批准的策略消息
        """
        config = setup_e2e_env
        
        # 步骤1: 模拟策略优化模组发布策略
        strategy_data = self._simulate_strategy_from_optimizer(config)
        
        # 等待系统处理
        time.sleep(2)
        
        # 步骤2: 验证待审列表中显示该策略
        pending_reviews = self._get_pending_reviews(config)
        assert len(pending_reviews) > 0, "待审列表中应该有策略"
        
        # 找到我们刚才发布的策略
        target_review = None
        for review in pending_reviews:
            if review.get("strategy_id") == strategy_data["strategy_id"]:
                target_review = review
                break
        
        assert target_review is not None, "在待审列表中未找到目标策略"
        assert target_review["status"] == "pending", "策略状态应为pending"
        
        # 步骤3: 启动ZMQ订阅者监听下游消息
        received_messages = []
        subscriber_thread = self._start_zmq_subscriber(config, received_messages)
        
        # 步骤4: 模拟前端提交审核决策
        decision_response = self._submit_review_decision(
            config, 
            target_review["id"], 
            {
                "decision": "approve",
                "reason": "策略风险可控，批准执行",
                "risk_adjustment": {
                    "position_limit": 0.8
                }
            }
        )
        
        assert decision_response.status_code == 200, "提交审核决策应该成功"
        
        # 等待消息传播
        time.sleep(3)
        
        # 步骤5: 验证审核历史记录
        review_history = self._get_review_history(config, target_review["id"])
        assert len(review_history) > 0, "应该有审核历史记录"
        
        latest_decision = review_history[0]
        assert latest_decision["decision"] == "approve", "最新决策应为approve"
        assert latest_decision["reason"] == "策略风险可控，批准执行", "决策原因应匹配"
        
        # 步骤6: 验证下游系统收到批准的策略消息
        assert len(received_messages) > 0, "下游系统应该收到批准的策略消息"
        
        approved_message = received_messages[-1]
        assert approved_message["strategy_id"] == strategy_data["strategy_id"], "消息中的策略ID应匹配"
        assert "review_info" in approved_message, "消息应包含review_info字段"
        assert approved_message["review_info"]["status"] == "approved", "审核状态应为approved"
        assert approved_message["review_info"]["reviewer"] != "auto", "审核者不应为auto"
        
        # 清理：停止订阅者线程
        subscriber_thread.join(timeout=1)
        
        print("✅ E2E-REVIEW-01 测试通过：人工审核完整操作流程验证成功")
    
    def _simulate_strategy_from_optimizer(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """模拟策略优化模组发布策略"""
        strategy_data = {
            "strategy_id": f"test_strategy_{int(time.time())}",
            "strategy_type": "momentum",
            "parameters": {
                "symbol": "BTCUSDT",
                "timeframe": "1h",
                "risk_level": "high",  # 高风险，触发人工审核
                "position_size": 0.5,
                "stop_loss": 0.02,
                "take_profit": 0.05
            },
            "backtest_results": {
                "total_return": 0.15,
                "sharpe_ratio": 1.2,
                "max_drawdown": 0.08
            },
            "timestamp": datetime.now().isoformat()
        }
        
        # 通过ZMQ发布策略（模拟策略优化模组）
        context = zmq.Context()
        publisher = context.socket(zmq.PUB)
        publisher.connect(f"tcp://localhost:{config['zmq_sub_port']}")
        
        # 等待连接建立
        time.sleep(1)
        
        # 发布策略消息
        topic = "optimizer.pool.trading"
        message = json.dumps(strategy_data)
        publisher.send_multipart([topic.encode(), message.encode()])
        
        publisher.close()
        context.term()
        
        return strategy_data
    
    def _get_pending_reviews(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """获取待审核列表"""
        response = requests.get(
            f"{config['backend_url']}/api/reviews",
            params={"status": "pending"}
        )
        
        if response.status_code == 200:
            return response.json().get("reviews", [])
        else:
            return []
    
    def _start_zmq_subscriber(self, config: Dict[str, Any], received_messages: List[Dict[str, Any]]) -> threading.Thread:
        """启动ZMQ订阅者监听下游消息"""
        def subscriber_worker():
            context = zmq.Context()
            subscriber = context.socket(zmq.SUB)
            subscriber.connect(f"tcp://localhost:{config['zmq_pub_port']}")
            subscriber.setsockopt(zmq.SUBSCRIBE, b"review.pool.approved")
            
            # 设置超时
            subscriber.setsockopt(zmq.RCVTIMEO, 5000)  # 5秒超时
            
            try:
                while True:
                    try:
                        topic, message = subscriber.recv_multipart()
                        data = json.loads(message.decode())
                        received_messages.append(data)
                    except zmq.Again:
                        # 超时，退出循环
                        break
            except Exception as e:
                print(f"ZMQ订阅者错误: {e}")
            finally:
                subscriber.close()
                context.term()
        
        thread = threading.Thread(target=subscriber_worker)
        thread.daemon = True
        thread.start()
        return thread
    
    def _submit_review_decision(self, config: Dict[str, Any], review_id: str, decision_data: Dict[str, Any]) -> requests.Response:
        """提交审核决策"""
        return requests.post(
            f"{config['backend_url']}/api/reviews/{review_id}/decision",
            json=decision_data,
            headers={"Content-Type": "application/json"}
        )
    
    def _get_review_history(self, config: Dict[str, Any], review_id: str) -> List[Dict[str, Any]]:
        """获取审核历史记录"""
        response = requests.get(
            f"{config['backend_url']}/api/reviews/{review_id}/decisions"
        )
        
        if response.status_code == 200:
            return response.json().get("decisions", [])
        else:
            return []


if __name__ == "__main__":
    # 运行端到端测试
    pytest.main(["-v", __file__])