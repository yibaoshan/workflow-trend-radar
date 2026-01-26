"""
数据模型定义
"""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional
import json


@dataclass
class UserConfig:
    """用户配置模型"""
    id: Optional[int] = None
    user_id: str = ""
    user_name: str = ""
    keywords: str = "[]"  # JSON array
    platforms: str = "[]"  # JSON array
    push_times: str = "[]"  # JSON array
    timezone: str = "Asia/Shanghai"
    report_mode: str = "current"
    enabled: int = 1
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def get_keywords(self) -> List[str]:
        """获取关键词列表"""
        return json.loads(self.keywords)

    def get_platforms(self) -> List[str]:
        """获取平台列表"""
        return json.loads(self.platforms)

    def get_push_times(self) -> List[str]:
        """获取推送时间列表"""
        return json.loads(self.push_times)

    def set_keywords(self, keywords: List[str]):
        """设置关键词列表"""
        self.keywords = json.dumps(keywords, ensure_ascii=False)

    def set_platforms(self, platforms: List[str]):
        """设置平台列表"""
        self.platforms = json.dumps(platforms, ensure_ascii=False)

    def set_push_times(self, push_times: List[str]):
        """设置推送时间列表"""
        self.push_times = json.dumps(push_times, ensure_ascii=False)


@dataclass
class PushLog:
    """推送日志模型"""
    id: Optional[int] = None
    user_id: str = ""
    push_time: Optional[datetime] = None
    news_count: int = 0
    status: str = "success"  # success/failed
    error_msg: Optional[str] = None
    created_at: Optional[datetime] = None
