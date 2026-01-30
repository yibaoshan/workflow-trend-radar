"""
用户配置生成器
"""

import os
import tempfile
from typing import Dict, Tuple
import yaml

from ..storage.models import UserConfig


# 平台映射表（与 config.yaml 中的 platforms.sources 保持一致）
PLATFORM_MAPPING = {
    "36氪": "36kr",
    "百度": "baidu",
    "哔哩哔哩": "bilibili",
    "参考消息": "cankaoxiaoxi",
    "虫部落": "chongbuluo",
    "豆瓣": "douban",
    "抖音": "douyin",
    "快讯": "fastbull",
    "FreeBuf": "freebuf",
    "格隆汇": "gelonghui",
    "果壳": "ghxi",
    "GitHub": "github",
    "Hacker News": "hackernews",
    "虎扑": "hupu",
    "凤凰网": "ifeng",
    "爱奇艺": "iqiyi",
    "IT之家": "ithome",
    "金十数据": "jin10",
    "稀土掘金": "juejin",
    "靠谱新闻": "kaopu",
    "快手": "kuaishou",
    "Linux.do": "linuxdo",
    "财经新闻": "mktnews",
    "牛客": "nowcoder",
    "远景论坛": "pcbeta",
    "Product Hunt": "producthunt",
    "腾讯视频": "qqvideo",
    "什么值得买": "smzdm",
    "Solidot": "solidot",
    "俄罗斯卫星通讯社": "sputniknewscn",
    "少数派": "sspai",
    "Steam": "steam",
    "腾讯新闻": "tencent",
    "澎湃新闻": "thepaper",
    "贴吧": "tieba",
    "今日头条": "toutiao",
    "V2EX": "v2ex",
    "华尔街见闻": "wallstreetcn",
    "微博": "weibo",
    "雪球": "xueqiu",
    "联合早报": "zaobao",
    "知乎": "zhihu",
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
        config_yaml = yaml.safe_load(f)

    # 获取用户配置
    keywords = user_config.get_keywords()
    platforms = user_config.get_platforms()

    # 覆盖用户配置
    config_yaml['app']['timezone'] = user_config.timezone
    config_yaml['report']['mode'] = user_config.report_mode

    # 配置平台
    config_yaml['platforms']['sources'] = [
        {"id": pid, "name": PLATFORM_NAME_MAPPING.get(pid, pid)}
        for pid in platforms
    ]

    # 禁用通知（由机器人自己发送）
    config_yaml['notification']['enabled'] = False

    # 禁用 AI 分析（节省成本，可选）
    config_yaml['ai_analysis']['enabled'] = False

    # 禁用 AI 翻译
    config_yaml['ai_translation']['enabled'] = False

    # 使用 load_config 的转换逻辑
    from trendradar.core import load_config
    import tempfile

    # 写入临时配置文件
    temp_config_file = os.path.join(tempfile.gettempdir(), f"config_{user_config.user_id}.yaml")
    with open(temp_config_file, 'w', encoding='utf-8') as f:
        yaml.dump(config_yaml, f, allow_unicode=True)

    # 加载并转换配置
    config = load_config(temp_config_file)

    # 清理临时配置文件
    if os.path.exists(temp_config_file):
        os.remove(temp_config_file)

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
