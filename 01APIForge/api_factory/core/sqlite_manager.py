#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SQLite管理器 - 本地数据存储
核心设计理念：数据隔离、轻量级存储、事务管理
"""

import aiosqlite
import logging
import os
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
from pathlib import Path
from ..config.settings import SQLiteConfig

logger = logging.getLogger(__name__)


class SQLiteManager:
    """SQLite管理器 - 本地数据存储"""

    def __init__(self, config: SQLiteConfig):
        self.config = config
        self.db_path = config.database_path
        self.backup_path = config.backup_path
        self.connection: Optional[aiosqlite.Connection] = None

        # 统计信息
        self.stats = {
            "queries_executed": 0,
            "transactions_committed": 0,
            "errors": 0,
            "start_time": None,
        }

    async def initialize(self):
        """初始化SQLite数据库"""
        try:
            # 确保数据目录存在
            db_dir = Path(self.db_path).parent
            db_dir.mkdir(parents=True, exist_ok=True)

            # 确保备份目录存在
            if self.backup_path:
                Path(self.backup_path).mkdir(parents=True, exist_ok=True)

            # 连接数据库
            self.connection = await aiosqlite.connect(self.db_path)

            # 启用外键约束
            await self.connection.execute("PRAGMA foreign_keys = ON")

            # 设置WAL模式以提高并发性能
            await self.connection.execute("PRAGMA journal_mode = WAL")

            # 创建基础表结构
            await self._create_tables()

            self.stats["start_time"] = datetime.now()
            logger.info(f"SQLite管理器初始化完成 - 数据库: {self.db_path}")

        except Exception as e:
            logger.error(f"SQLite初始化失败: {e}")
            raise

    async def _create_tables(self):
        """创建基础表结构"""
        try:
            # 租户表 - 数据隔离
            await self.connection.execute(
                """
                CREATE TABLE IF NOT EXISTS tenants (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tenant_id TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    status TEXT DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # API配置表
            await self.connection.execute(
                """
                CREATE TABLE IF NOT EXISTS api_configs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tenant_id TEXT NOT NULL,
                    api_name TEXT NOT NULL,
                    api_type TEXT NOT NULL,
                    endpoint TEXT NOT NULL,
                    config_data TEXT NOT NULL,
                    status TEXT DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id),
                    UNIQUE(tenant_id, api_name)
                )
            """
            )

            # 用户认证表
            await self.connection.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tenant_id TEXT NOT NULL,
                    username TEXT NOT NULL,
                    email TEXT NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT DEFAULT 'user',
                    status TEXT DEFAULT 'active',
                    last_login TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id),
                    UNIQUE(tenant_id, username),
                    UNIQUE(tenant_id, email)
                )
            """
            )

            # API密钥表
            await self.connection.execute(
                """
                CREATE TABLE IF NOT EXISTS api_keys (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tenant_id TEXT NOT NULL,
                    user_id INTEGER NOT NULL,
                    key_name TEXT NOT NULL,
                    key_hash TEXT NOT NULL,
                    permissions TEXT NOT NULL,
                    expires_at TIMESTAMP,
                    last_used TIMESTAMP,
                    status TEXT DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id),
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """
            )

            # API调用日志表
            await self.connection.execute(
                """
                CREATE TABLE IF NOT EXISTS api_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tenant_id TEXT NOT NULL,
                    user_id INTEGER,
                    api_name TEXT NOT NULL,
                    method TEXT NOT NULL,
                    endpoint TEXT NOT NULL,
                    status_code INTEGER NOT NULL,
                    response_time REAL NOT NULL,
                    request_size INTEGER DEFAULT 0,
                    response_size INTEGER DEFAULT 0,
                    error_message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id),
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """
            )

            # 配额管理表
            await self.connection.execute(
                """
                CREATE TABLE IF NOT EXISTS quotas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tenant_id TEXT NOT NULL,
                    user_id INTEGER,
                    api_name TEXT NOT NULL,
                    quota_type TEXT NOT NULL,
                    limit_value INTEGER NOT NULL,
                    window_seconds INTEGER NOT NULL,
                    current_usage INTEGER DEFAULT 0,
                    reset_at TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id),
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """
            )

            # 集群节点表
            await self.connection.execute(
                """
                CREATE TABLE IF NOT EXISTS cluster_nodes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    node_id TEXT UNIQUE NOT NULL,
                    node_name TEXT NOT NULL,
                    host TEXT NOT NULL,
                    port INTEGER NOT NULL,
                    status TEXT DEFAULT 'active',
                    health_score REAL DEFAULT 1.0,
                    last_heartbeat TIMESTAMP,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # 创建索引
            await self._create_indexes()

            await self.connection.commit()
            logger.info("数据库表结构创建完成")

        except Exception as e:
            logger.error(f"创建表结构失败: {e}")
            raise

    async def _create_indexes(self):
        """创建数据库索引"""
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_api_configs_tenant ON api_configs(tenant_id)",
            "CREATE INDEX IF NOT EXISTS idx_users_tenant ON users(tenant_id)",
            "CREATE INDEX IF NOT EXISTS idx_api_keys_tenant ON api_keys(tenant_id)",
            "CREATE INDEX IF NOT EXISTS idx_api_logs_tenant ON api_logs(tenant_id)",
            "CREATE INDEX IF NOT EXISTS idx_api_logs_created ON api_logs(created_at)",
            "CREATE INDEX IF NOT EXISTS idx_quotas_tenant ON quotas(tenant_id)",
            "CREATE INDEX IF NOT EXISTS idx_cluster_nodes_status ON cluster_nodes(status)",
        ]

        for index_sql in indexes:
            await self.connection.execute(index_sql)

    async def execute_query(
        self, query: str, params: Tuple = ()
    ) -> List[Dict[str, Any]]:
        """执行查询语句"""
        try:
            if not self.connection:
                raise RuntimeError("数据库连接未初始化")

            async with self.connection.execute(query, params) as cursor:
                columns = [description[0] for description in cursor.description]
                rows = await cursor.fetchall()

                result = []
                for row in rows:
                    result.append(dict(zip(columns, row)))

                self.stats["queries_executed"] += 1
                logger.debug(f"查询执行完成 - 返回 {len(result)} 行")

                return result

        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"执行查询失败: {e}")
            raise

    async def execute_update(self, query: str, params: Tuple = ()) -> int:
        """执行更新语句"""
        try:
            if not self.connection:
                raise RuntimeError("数据库连接未初始化")

            cursor = await self.connection.execute(query, params)
            affected_rows = cursor.rowcount
            await self.connection.commit()

            self.stats["queries_executed"] += 1
            self.stats["transactions_committed"] += 1
            logger.debug(f"更新执行完成 - 影响 {affected_rows} 行")

            return affected_rows

        except Exception as e:
            self.stats["errors"] += 1
            await self.connection.rollback()
            logger.error(f"执行更新失败: {e}")
            raise

    async def insert_record(self, table: str, data: Dict[str, Any]) -> int:
        """插入记录"""
        try:
            columns = list(data.keys())
            placeholders = ["?" for _ in columns]
            values = list(data.values())

            query = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({', '.join(placeholders)})"

            cursor = await self.connection.execute(query, values)
            await self.connection.commit()

            self.stats["queries_executed"] += 1
            self.stats["transactions_committed"] += 1

            return cursor.lastrowid

        except Exception as e:
            self.stats["errors"] += 1
            await self.connection.rollback()
            logger.error(f"插入记录失败: {e}")
            raise

    async def update_record(
        self,
        table: str,
        data: Dict[str, Any],
        where_clause: str,
        where_params: Tuple = (),
    ) -> int:
        """更新记录"""
        try:
            set_clauses = [f"{col} = ?" for col in data.keys()]
            values = list(data.values()) + list(where_params)

            query = f"UPDATE {table} SET {', '.join(set_clauses)} WHERE {where_clause}"

            return await self.execute_update(query, values)

        except Exception as e:
            logger.error(f"更新记录失败: {e}")
            raise

    async def delete_record(
        self, table: str, where_clause: str, where_params: Tuple = ()
    ) -> int:
        """删除记录"""
        try:
            query = f"DELETE FROM {table} WHERE {where_clause}"
            return await self.execute_update(query, where_params)

        except Exception as e:
            logger.error(f"删除记录失败: {e}")
            raise

    async def get_records(
        self,
        table: str,
        where_clause: str = "",
        where_params: Tuple = (),
        order_by: str = "",
        limit: int = 0,
    ) -> List[Dict[str, Any]]:
        """获取记录"""
        try:
            query = f"SELECT * FROM {table}"

            if where_clause:
                query += f" WHERE {where_clause}"

            if order_by:
                query += f" ORDER BY {order_by}"

            if limit > 0:
                query += f" LIMIT {limit}"

            return await self.execute_query(query, where_params)

        except Exception as e:
            logger.error(f"获取记录失败: {e}")
            raise

    async def begin_transaction(self):
        """开始事务"""
        if self.connection:
            await self.connection.execute("BEGIN")

    async def commit_transaction(self):
        """提交事务"""
        if self.connection:
            await self.connection.commit()
            self.stats["transactions_committed"] += 1

    async def rollback_transaction(self):
        """回滚事务"""
        if self.connection:
            await self.connection.rollback()

    async def backup_database(self) -> str:
        """备份数据库"""
        try:
            if not self.backup_path:
                raise ValueError("备份路径未配置")

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = Path(self.backup_path) / f"api_factory_backup_{timestamp}.db"

            # 创建备份
            backup_conn = await aiosqlite.connect(str(backup_file))
            await self.connection.backup(backup_conn)
            await backup_conn.close()

            logger.info(f"数据库备份完成: {backup_file}")
            return str(backup_file)

        except Exception as e:
            logger.error(f"数据库备份失败: {e}")
            raise

    async def health_check(self) -> bool:
        """健康检查"""
        try:
            if not self.connection:
                return False

            # 执行简单查询
            await self.connection.execute("SELECT 1")
            return True

        except Exception as e:
            logger.error(f"SQLite健康检查失败: {e}")
            return False

    async def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        try:
            # 获取数据库文件大小
            db_size = 0
            if os.path.exists(self.db_path):
                db_size = os.path.getsize(self.db_path)

            # 获取表统计信息
            table_stats = {}
            tables = [
                "tenants",
                "api_configs",
                "users",
                "api_keys",
                "api_logs",
                "quotas",
                "cluster_nodes",
            ]

            for table in tables:
                try:
                    result = await self.execute_query(
                        f"SELECT COUNT(*) as count FROM {table}"
                    )
                    table_stats[table] = result[0]["count"] if result else 0
                except Exception:
                    table_stats[table] = 0

            uptime = None
            if self.stats["start_time"]:
                uptime = (datetime.now() - self.stats["start_time"]).total_seconds()

            return {
                **self.stats,
                "uptime_seconds": uptime,
                "database_size_bytes": db_size,
                "table_counts": table_stats,
            }

        except Exception as e:
            logger.error(f"获取SQLite统计信息失败: {e}")
            return self.stats

    async def cleanup(self):
        """清理资源"""
        try:
            if self.connection:
                await self.connection.close()

            logger.info("SQLite管理器已清理")

        except Exception as e:
            logger.error(f"SQLite清理失败: {e}")


# 数据库表名常量


class Tables:
    """数据库表名定义"""

    TENANTS = "tenants"
    API_CONFIGS = "api_configs"
    USERS = "users"
    API_KEYS = "api_keys"
    API_LOGS = "api_logs"
    QUOTAS = "quotas"
    CLUSTER_NODES = "cluster_nodes"
