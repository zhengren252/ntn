"""总控模块数据库管理

数据库管理模块

严格按照数据隔离与环境管理规范V1.0实现：
- 三环境隔离：development, staging, production
- 数据库文件按环境分离
- 自动创建数据目录结构
"""

import aiosqlite
from typing import Optional, Dict, Any, List
from pathlib import Path
from .config import settings


class DatabaseManager:
    """数据库管理器 - 支持环境隔离和异步操作"""

    def __init__(self):
        """初始化数据库管理器"""
        # 从database_url中提取路径
        self.database_path = settings.database_path
        self._ensure_data_directory()
        self._connection_pool = {}

    def _ensure_data_directory(self):
        """确保数据目录存在"""
        data_dir = Path(self.database_path).parent
        data_dir.mkdir(parents=True, exist_ok=True)

    async def initialize(self):
        """初始化数据库"""
        await self._create_base_tables()
        await self._init_base_data()

        # 仅在开发环境插入模拟数据
        if settings.get_mock_data_enabled():
            await self._insert_mock_data()

    async def _create_base_tables(self):
        """创建基础表结构"""
        async with aiosqlite.connect(self.database_path) as db:
            # 系统状态表
            await db.execute("""
                CREATE TABLE IF NOT EXISTS system_status (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    module_name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    last_heartbeat TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 记忆网络事件表
            await db.execute("""
                CREATE TABLE IF NOT EXISTS memory_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    event_date DATE NOT NULL,
                    summary TEXT NOT NULL,
                    details TEXT,
                    impact_score REAL DEFAULT 0.0,
                    tags TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 控制指令表
            await db.execute("""
                CREATE TABLE IF NOT EXISTS control_commands (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    command_type TEXT NOT NULL,
                    payload TEXT,
                    target_module TEXT,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    executed_at TIMESTAMP,
                    result TEXT
                )
            """)

            # 指令日志表
            await db.execute("""
                CREATE TABLE IF NOT EXISTS command_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    command_id INTEGER,
                    log_level TEXT NOT NULL,
                    message TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (command_id) REFERENCES
                    control_commands (id)
                )
            """)

            # 风险评估表
            await db.execute("""
                CREATE TABLE IF NOT EXISTS risk_assessments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    assessment_type TEXT NOT NULL,
                    risk_level TEXT NOT NULL,
                    risk_score REAL NOT NULL,
                    factors TEXT,
                    recommendations TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 风险因子表
            await db.execute("""
                CREATE TABLE IF NOT EXISTS risk_factors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    factor_name TEXT NOT NULL,
                    factor_value REAL NOT NULL,
                    weight REAL DEFAULT 1.0,
                    category TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 创建索引
            await db.execute(
                "CREATE INDEX IF NOT EXISTS idx_system_status_module "
                "ON system_status(module_name)"
            )
            await db.execute(
                "CREATE INDEX IF NOT EXISTS idx_memory_events_type "
                "ON memory_events(event_type)"
            )
            await db.execute(
                "CREATE INDEX IF NOT EXISTS idx_memory_events_date "
                "ON memory_events(event_date)"
            )
            await db.execute(
                "CREATE INDEX IF NOT EXISTS idx_control_commands_type "
                "ON control_commands(command_type)"
            )
            await db.execute(
                "CREATE INDEX IF NOT EXISTS idx_control_commands_status "
                "ON control_commands(status)"
            )
            await db.execute(
                "CREATE INDEX IF NOT EXISTS idx_risk_assessments_type "
                "ON risk_assessments(assessment_type)"
            )
            await db.execute(
                "CREATE INDEX IF NOT EXISTS idx_risk_factors_name "
                "ON risk_factors(factor_name)"
            )

            await db.commit()

    async def _init_base_data(self):
        """初始化基础数据"""
        async with aiosqlite.connect(self.database_path) as db:
            # 插入系统状态初始记录
            await db.execute(
                "INSERT OR IGNORE INTO system_status "
                "(module_name, status) VALUES (?, ?)",
                ("master_control", "initializing")
            )
            await db.commit()

    async def _insert_mock_data(self):
        """插入模拟数据（仅开发环境）"""
        async with aiosqlite.connect(self.database_path) as db:
            # 插入模拟记忆事件
            mock_events = [
                (
                    "market_crash", "2022-05-09",
                    "LUNA崩盘事件",
                    "Terra生态系统崩溃，LUNA和UST价格暴跌99%",
                    9.5, "crypto,stablecoin,depeagging"
                ),
                (
                    "market_crash", "2020-03-12",
                    "COVID-19黑色星期四",
                    "全球股市因疫情恐慌暴跌，美股熔断",
                    9.0, "pandemic,stocks,volatility"
                )
            ]

            for event in mock_events:
                await db.execute(
                    "INSERT OR IGNORE INTO memory_events "
                    "(event_type, event_date, summary, details, "
                    "impact_score, tags) VALUES (?, ?, ?, ?, ?, ?)",
                    event
                )

            await db.commit()

    async def get_connection(self):
        """获取数据库连接"""
        return await aiosqlite.connect(self.database_path)

    async def execute_query(
        self, query: str, params: tuple = ()
    ) -> List[Dict[str, Any]]:
        """执行查询并返回结果"""
        async with aiosqlite.connect(self.database_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(query, params) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def execute_update(
        self, query: str, params: tuple = ()
    ) -> int:
        """执行更新操作并返回影响的行数"""
        async with aiosqlite.connect(self.database_path) as db:
            cursor = await db.execute(query, params)
            await db.commit()
            return cursor.rowcount

    async def get_system_status(
        self, module_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """获取系统状态"""
        if module_name:
            query = (
                "SELECT * FROM system_status WHERE module_name = ? "
                "ORDER BY updated_at DESC"
            )
            params = (module_name,)
        else:
            query = "SELECT * FROM system_status ORDER BY updated_at DESC"
            params = ()

        return await self.execute_query(query, params)

    async def update_system_status(
        self, module_name: str, status: str, metadata: Optional[str] = None
    ) -> bool:
        """更新系统状态"""
        query = """
            INSERT OR REPLACE INTO system_status
            (module_name, status, metadata, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        """
        params = (module_name, status, metadata)
        affected_rows = await self.execute_update(query, params)
        return affected_rows > 0


# 全局数据库管理器实例
db_manager: Optional[DatabaseManager] = None


async def init_database() -> DatabaseManager:
    """初始化数据库管理器"""
    global db_manager
    if db_manager is None:
        db_manager = DatabaseManager()
        await db_manager.initialize()
    return db_manager


def get_db_manager() -> DatabaseManager:
    """获取数据库管理器实例"""
    if db_manager is None:
        raise RuntimeError("数据库管理器未初始化，请先调用 init_database()")
    return db_manager


async def close_database():
    """关闭数据库连接"""
    global db_manager
    if db_manager is not None:
        # 清理连接池
        if hasattr(db_manager, '_connection_pool'):
            db_manager._connection_pool.clear()
        db_manager = None