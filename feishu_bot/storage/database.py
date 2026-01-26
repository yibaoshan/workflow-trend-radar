"""
数据库操作
"""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Optional
import logging

from .models import UserConfig, PushLog

logger = logging.getLogger(__name__)


class Database:
    """数据库管理类"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_database()

    def _init_database(self):
        """初始化数据库表"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 创建用户配置表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_configs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL UNIQUE,
                user_name TEXT,
                keywords TEXT NOT NULL,
                platforms TEXT NOT NULL,
                push_times TEXT NOT NULL,
                timezone TEXT DEFAULT 'Asia/Shanghai',
                report_mode TEXT DEFAULT 'current',
                enabled INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 创建索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_id ON user_configs(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_enabled ON user_configs(enabled)")

        # 创建推送日志表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS push_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                push_time TIMESTAMP NOT NULL,
                news_count INTEGER DEFAULT 0,
                status TEXT NOT NULL,
                error_msg TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_push ON push_logs(user_id, push_time)")

        conn.commit()
        conn.close()

        logger.info(f"数据库初始化完成: {self.db_path}")

    def get_connection(self):
        """获取数据库连接"""
        return sqlite3.connect(self.db_path)

    def get_user_config(self, user_id: str) -> Optional[UserConfig]:
        """获取用户配置"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM user_configs WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return UserConfig(
                id=row[0],
                user_id=row[1],
                user_name=row[2],
                keywords=row[3],
                platforms=row[4],
                push_times=row[5],
                timezone=row[6],
                report_mode=row[7],
                enabled=row[8],
                created_at=row[9],
                updated_at=row[10]
            )
        return None

    def save_user_config(self, config: UserConfig):
        """保存用户配置"""
        conn = self.get_connection()
        cursor = conn.cursor()

        now = datetime.now().isoformat()

        if config.id:
            # 更新
            cursor.execute("""
                UPDATE user_configs
                SET user_name = ?, keywords = ?, platforms = ?, push_times = ?,
                    timezone = ?, report_mode = ?, enabled = ?, updated_at = ?
                WHERE user_id = ?
            """, (
                config.user_name, config.keywords, config.platforms, config.push_times,
                config.timezone, config.report_mode, config.enabled, now, config.user_id
            ))
        else:
            # 插入
            cursor.execute("""
                INSERT INTO user_configs (user_id, user_name, keywords, platforms, push_times,
                                         timezone, report_mode, enabled, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                config.user_id, config.user_name, config.keywords, config.platforms, config.push_times,
                config.timezone, config.report_mode, config.enabled, now, now
            ))

        conn.commit()
        conn.close()

        logger.info(f"用户配置已保存: user_id={config.user_id}")

    def get_enabled_users(self) -> List[UserConfig]:
        """获取所有启用的用户"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM user_configs WHERE enabled = 1")
        rows = cursor.fetchall()
        conn.close()

        users = []
        for row in rows:
            users.append(UserConfig(
                id=row[0],
                user_id=row[1],
                user_name=row[2],
                keywords=row[3],
                platforms=row[4],
                push_times=row[5],
                timezone=row[6],
                report_mode=row[7],
                enabled=row[8],
                created_at=row[9],
                updated_at=row[10]
            ))

        return users

    def log_push(self, user_id: str, news_count: int, status: str, error_msg: Optional[str] = None):
        """记录推送日志"""
        conn = self.get_connection()
        cursor = conn.cursor()

        now = datetime.now().isoformat()

        cursor.execute("""
            INSERT INTO push_logs (user_id, push_time, news_count, status, error_msg, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, now, news_count, status, error_msg, now))

        conn.commit()
        conn.close()

        logger.info(f"推送日志已记录: user_id={user_id}, status={status}")

    def get_push_logs(self, user_id: str, limit: int = 10) -> List[PushLog]:
        """获取用户推送日志"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM push_logs
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (user_id, limit))

        rows = cursor.fetchall()
        conn.close()

        logs = []
        for row in rows:
            logs.append(PushLog(
                id=row[0],
                user_id=row[1],
                push_time=row[2],
                news_count=row[3],
                status=row[4],
                error_msg=row[5],
                created_at=row[6]
            ))

        return logs
