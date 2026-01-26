"""
配置管理
"""

import os
from typing import Optional


class Settings:
    """从环境变量加载配置"""

    # 飞书凭证（必须从环境变量获取）
    FEISHU_APP_ID: str = os.getenv('FEISHU_APP_ID', '')
    FEISHU_APP_SECRET: str = os.getenv('FEISHU_APP_SECRET', '')

    # 服务配置
    HOST: str = os.getenv('HOST', '0.0.0.0')
    PORT: int = int(os.getenv('PORT', '9001'))

    # 数据库路径
    DATABASE_PATH: str = os.getenv('DATABASE_PATH', '/data/feishu_bot.db')

    # 日志级别
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')

    def validate(self):
        """验证必需配置"""
        if not self.FEISHU_APP_ID:
            raise ValueError("FEISHU_APP_ID 环境变量未设置")
        if not self.FEISHU_APP_SECRET:
            raise ValueError("FEISHU_APP_SECRET 环境变量未设置")


settings = Settings()
