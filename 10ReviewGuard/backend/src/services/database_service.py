#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库服务

负责ReviewGuard模组的SQLite数据库操作：
1. 数据库初始化和表创建
2. 策略审核记录管理
3. 用户和权限管理
4. 审核规则配置
"""

import os
import sqlite3
import asyncio
import aiosqlite
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from contextlib import asynccontextmanager

try:
    from ..utils.logger import setup_logger
except ImportError:
    from utils.logger import setup_logger

logger = setup_logger(__name__)

class DatabaseService:
    """数据库服务类"""
    
    def __init__(self):
        self.db_path = os.getenv("DATABASE_PATH", "./data/reviewguard.db")
        self.connection = None
        
        # 确保数据目录存在
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
    
    async def initialize(self):
        """初始化数据库"""
        try:
            logger.info(f"正在初始化数据库: {self.db_path}")
            
            # 创建数据库连接
            self.connection = await aiosqlite.connect(self.db_path)
            
            # 启用外键约束
            await self.connection.execute("PRAGMA foreign_keys = ON")
            
            # 创建表结构
            await self._create_tables()
            
            # 插入初始数据
            await self._insert_initial_data()
            
            logger.info("数据库初始化完成")
            
        except Exception as e:
            logger.error(f"数据库初始化失败: {e}")
            raise
    
    async def close(self):
        """关闭数据库连接"""
        if self.connection:
            await self.connection.close()
            logger.info("数据库连接已关闭")
    
    def is_connected(self) -> bool:
        """检查数据库连接状态"""
        return self.connection is not None
    
    @asynccontextmanager
    async def transaction(self):
        """数据库事务上下文管理器"""
        if not self.connection:
            raise RuntimeError("数据库未连接")
        
        try:
            await self.connection.execute("BEGIN")
            yield self.connection
            await self.connection.commit()
        except Exception:
            await self.connection.rollback()
            raise
    
    async def _create_tables(self):
        """创建数据库表"""
        
        # 用户表
        await self.connection.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT DEFAULT 'reviewer' CHECK (role IN ('admin', 'reviewer', 'readonly')),
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 策略审核表
        await self.connection.execute("""
            CREATE TABLE IF NOT EXISTS strategy_reviews (
                id TEXT PRIMARY KEY,
                strategy_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                strategy_type TEXT NOT NULL,
                expected_return REAL,
                max_drawdown REAL,
                risk_level TEXT CHECK (risk_level IN ('low', 'medium', 'high')),
                status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'approved', 'rejected', 'deferred')),
                raw_data TEXT, -- JSON格式存储原始策略数据
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 审核决策表
        await self.connection.execute("""
            CREATE TABLE IF NOT EXISTS review_decisions (
                id TEXT PRIMARY KEY,
                strategy_review_id TEXT NOT NULL,
                reviewer_id TEXT NOT NULL,
                decision TEXT NOT NULL CHECK (decision IN ('approve', 'reject', 'defer')),
                reason TEXT,
                risk_adjustment TEXT, -- JSON格式存储风险调整参数
                decision_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (strategy_review_id) REFERENCES strategy_reviews(id),
                FOREIGN KEY (reviewer_id) REFERENCES users(id)
            )
        """)
        
        # 风险评估表
        await self.connection.execute("""
            CREATE TABLE IF NOT EXISTS risk_assessments (
                id TEXT PRIMARY KEY,
                strategy_review_id TEXT NOT NULL,
                volatility_score REAL,
                liquidity_score REAL,
                correlation_risk REAL,
                detailed_metrics TEXT, -- JSON格式存储详细指标
                assessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (strategy_review_id) REFERENCES strategy_reviews(id)
            )
        """)
        
        # 审核规则表
        await self.connection.execute("""
            CREATE TABLE IF NOT EXISTS audit_rules (
                id TEXT PRIMARY KEY,
                rule_name TEXT NOT NULL,
                rule_type TEXT NOT NULL CHECK (rule_type IN ('auto_approve', 'auto_reject', 'require_review')),
                conditions TEXT NOT NULL, -- JSON格式存储规则条件
                action TEXT NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 创建索引
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_strategy_reviews_status ON strategy_reviews(status)",
            "CREATE INDEX IF NOT EXISTS idx_strategy_reviews_created_at ON strategy_reviews(created_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_review_decisions_strategy_id ON review_decisions(strategy_review_id)",
            "CREATE INDEX IF NOT EXISTS idx_review_decisions_reviewer_id ON review_decisions(reviewer_id)",
            "CREATE INDEX IF NOT EXISTS idx_risk_assessments_strategy_id ON risk_assessments(strategy_review_id)"
        ]
        
        for index_sql in indexes:
            await self.connection.execute(index_sql)
        
        await self.connection.commit()
        logger.info("数据库表创建完成")
    
    async def _insert_initial_data(self):
        """插入初始数据"""
        
        # 检查是否已有数据
        cursor = await self.connection.execute("SELECT COUNT(*) FROM users")
        user_count = (await cursor.fetchone())[0]
        
        if user_count == 0:
            # 插入默认用户
            import hashlib
            
            admin_password = hashlib.sha256(os.getenv("ADMIN_DEFAULT_PASSWORD", "admin123").encode()).hexdigest()
            reviewer_password = hashlib.sha256(os.getenv("REVIEWER_DEFAULT_PASSWORD", "reviewer123").encode()).hexdigest()
            
            await self.connection.execute("""
                INSERT INTO users (id, username, email, password_hash, role) VALUES 
                ('admin_001', 'admin', 'admin@neurotrade.com', ?, 'admin'),
                ('reviewer_001', 'reviewer1', 'reviewer1@neurotrade.com', ?, 'reviewer')
            """, (admin_password, reviewer_password))
            
            logger.info("已插入默认用户")
        
        # 检查审核规则
        cursor = await self.connection.execute("SELECT COUNT(*) FROM audit_rules")
        rule_count = (await cursor.fetchone())[0]
        
        if rule_count == 0:
            # 插入默认审核规则
            import json
            
            rules = [
                ('rule_001', '低风险自动通过', 'auto_approve', 
                 json.dumps({"risk_level": "low", "max_drawdown": {"<": 0.05}}), 'approve'),
                ('rule_002', '高风险强制审核', 'require_review', 
                 json.dumps({"risk_level": "high"}), 'manual_review'),
                ('rule_003', '超大仓位拒绝', 'auto_reject', 
                 json.dumps({"position_size": {">=": 0.5}}), 'reject')
            ]
            
            await self.connection.executemany("""
                INSERT INTO audit_rules (id, rule_name, rule_type, conditions, action) 
                VALUES (?, ?, ?, ?, ?)
            """, rules)
            
            logger.info("已插入默认审核规则")
        
        await self.connection.commit()
    
    # 策略审核相关方法
    async def create_strategy_review(self, strategy_data: Dict[str, Any]) -> str:
        """创建策略审核记录"""
        import uuid
        import json
        
        review_id = f"review_{uuid.uuid4().hex[:8]}"
        
        await self.connection.execute("""
            INSERT INTO strategy_reviews (
                id, strategy_id, symbol, strategy_type, expected_return, 
                max_drawdown, risk_level, raw_data
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            review_id,
            strategy_data.get('strategy_id'),
            strategy_data.get('symbol'),
            strategy_data.get('strategy_type'),
            strategy_data.get('expected_return'),
            strategy_data.get('max_drawdown'),
            strategy_data.get('risk_level'),
            json.dumps(strategy_data)
        ))
        
        await self.connection.commit()
        logger.info(f"已创建策略审核记录: {review_id}")
        return review_id
    
    async def get_pending_reviews(self, limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
        """获取待审核策略列表"""
        cursor = await self.connection.execute("""
            SELECT * FROM strategy_reviews 
            WHERE status IN ('pending', 'processing')
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """, (limit, offset))
        
        rows = await cursor.fetchall()
        columns = [description[0] for description in cursor.description]
        
        return [dict(zip(columns, row)) for row in rows]
    
    async def update_review_status(self, review_id: str, status: str, reviewer_id: str = None):
        """更新审核状态"""
        await self.connection.execute("""
            UPDATE strategy_reviews 
            SET status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (status, review_id))
        
        await self.connection.commit()
        logger.info(f"已更新审核状态: {review_id} -> {status}")
    
    async def create_review_decision(self, decision_data: Dict[str, Any]) -> str:
        """创建审核决策记录"""
        import uuid
        import json
        
        decision_id = f"decision_{uuid.uuid4().hex[:8]}"
        
        await self.connection.execute("""
            INSERT INTO review_decisions (
                id, strategy_review_id, reviewer_id, decision, reason, risk_adjustment
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            decision_id,
            decision_data.get('strategy_review_id'),
            decision_data.get('reviewer_id'),
            decision_data.get('decision'),
            decision_data.get('reason'),
            json.dumps(decision_data.get('risk_adjustment', {}))
        ))
        
        await self.connection.commit()
        logger.info(f"已创建审核决策记录: {decision_id}")
        return decision_id
    
    async def get_review_history(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """获取审核历史"""
        cursor = await self.connection.execute("""
            SELECT sr.*, rd.decision, rd.reason, rd.decision_time, u.username as reviewer_name
            FROM strategy_reviews sr
            LEFT JOIN review_decisions rd ON sr.id = rd.strategy_review_id
            LEFT JOIN users u ON rd.reviewer_id = u.id
            WHERE sr.status IN ('approved', 'rejected')
            ORDER BY sr.updated_at DESC
            LIMIT ? OFFSET ?
        """, (limit, offset))
        
        rows = await cursor.fetchall()
        columns = [description[0] for description in cursor.description]
        
        return [dict(zip(columns, row)) for row in rows]
    
    async def get_audit_rules(self) -> List[Dict[str, Any]]:
        """获取审核规则"""
        cursor = await self.connection.execute("""
            SELECT * FROM audit_rules WHERE is_active = TRUE ORDER BY created_at
        """)
        
        rows = await cursor.fetchall()
        columns = [description[0] for description in cursor.description]
        
        return [dict(zip(columns, row)) for row in rows]