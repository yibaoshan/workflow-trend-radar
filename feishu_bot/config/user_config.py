"""
用户配置生成器
"""

import os
import tempfile
from typing import Dict, Tuple
import yaml

from ..storage.models import UserConfig


# 平台映射表
PLATFORM_MAPPING = {
    "知乎": "zhihu",
    "微博": "weibo",
    "百度": "baidu",
    "抖音": "douyin",
    "今日头条": "toutiao",
    "B站": "bilibili-hot-search",
    "贴吧": "tieba",
    "澎湃": "thepaper",
    "华尔街见闻": "wallstreetcn-hot",
    "财联社": "cls-hot",
    "凤凰网": "ifeng",
}

# 反向映射
PLATFORM_NAME_MAPPING = {v: k for k, v in PLATFORM_MAPPING.items()}


def generate_user_config(user_config: UserConfig, base_config_path: str) -> Tuple[Dict, str]:
    """
    基于用户配置生成 trendradar 配置字典

    Args:
        user_config: 用户配置对象
        base_config_path: 基础配置文件路径

    Returns:
        tuple: (配置字典, 临时关键词文件路径)
    """
    # 加载基础配置
    with open(base_config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    # 获取用户配置
    keywords = user_config.get_keywords()
    platforms = user_config.get_platforms()

    # 覆盖用户配置
    config['app']['timezone'] = user_config.timezone
    config['report']['mode'] = user_config.report_mode

    # 配置平台
    config['platforms']['sources'] = [
        {"id": pid, "name": PLATFORM_NAME_MAPPING.get(pid, pid)}
        for pid in platforms
        if pid in PLATFORM_NAME_MAPPING.values()
    ]

    # 禁用通知（由机器人自己发送）
    config['notification']['enabled'] = False

    # 禁用 AI 分析（节省成本，可选）
    config['ai_analysis']['enabled'] = False

    # 禁用 AI 翻译
    config['ai_translation']['enabled'] = False

    # 写入临时关键词文件
    temp_keywords_file = os.path.join(tempfile.gettempdir(), f"keywords_{user_config.user_id}.txt")
    with open(temp_keywords_file, 'w', encoding='utf-8') as f:
        for keyword in keywords:
            f.write(f"{keyword}\n")

    return config, temp_keywords_file


def cleanup_temp_files(keywords_file: str):
    """清理临时文件"""
    if os.path.exists(keywords_file):
        os.remove(keywords_file)
