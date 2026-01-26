"""
消息构建器
"""

import json
from typing import Dict, List, Any
from datetime import datetime


def build_message_card(results: Dict, user_config: Any, news_count: int = 0) -> Dict:
    """
    构建飞书消息卡片

    Args:
        results: trendradar 分析结果
        user_config: 用户配置
        news_count: 新闻总数

    Returns:
        dict: 飞书消息卡片
    """
    # 卡片头部
    header = {
        "title": {
            "tag": "plain_text",
            "content": f"📊 热点推送 ({news_count} 条)"
        },
        "template": "red"
    }

    # 卡片内容
    elements = []

    # 时间戳
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    elements.append({
        "tag": "div",
        "text": {
            "tag": "lark_md",
            "content": f"**推送时间**: {now}"
        }
    })

    elements.append({"tag": "hr"})

    # 新增热点区域
    new_items = results.get('new_items', [])
    if new_items:
        elements.append({
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": f"**🆕 新增热点 ({len(new_items)} 条)**"
            }
        })

        for item in new_items[:5]:  # 最多显示 5 条
            title = item.get('title', '无标题')
            url = item.get('url', '#')
            platform = item.get('platform', '未知')

            elements.append({
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"• [{title}]({url}) - {platform}"
                }
            })

        elements.append({"tag": "hr"})

    # 关键词匹配区域
    hotlist = results.get('hotlist', {})
    if hotlist:
        for keyword, news_list in list(hotlist.items())[:5]:  # 最多显示 5 个关键词
            elements.append({
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"**🔥 {keyword} ({len(news_list)} 条)**"
                }
            })

            for item in news_list[:3]:  # 每个关键词最多显示 3 条
                title = item.get('title', '无标题')
                url = item.get('url', '#')
                platform = item.get('platform', '未知')

                elements.append({
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"• [{title}]({url}) - {platform}"
                    }
                })

            elements.append({"tag": "hr"})

    # 如果没有内容
    if not new_items and not hotlist:
        elements.append({
            "tag": "div",
            "text": {
                "tag": "plain_text",
                "content": "暂无匹配的热点新闻"
            }
        })

    # 底部操作按钮
    elements.append({
        "tag": "action",
        "actions": [
            {
                "tag": "button",
                "text": {"tag": "plain_text", "content": "查看配置"},
                "type": "primary",
                "value": {"action": "view_config"}
            },
            {
                "tag": "button",
                "text": {"tag": "plain_text", "content": "暂停推送"},
                "type": "default",
                "value": {"action": "pause"}
            }
        ]
    })

    return {
        "msg_type": "interactive",
        "card": {
            "header": header,
            "elements": elements
        }
    }


def build_welcome_card() -> Dict:
    """构建欢迎卡片"""
    return {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": "👋 欢迎使用热点推送助手"
                },
                "template": "blue"
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": "**功能介绍**\n\n个性化热点资讯推送机器人，支持：\n• 自定义关键词订阅\n• 多数据源选择\n• 自定义推送时间"
                    }
                },
                {"tag": "hr"},
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": "**快速开始**\n\n1. 设置关键词：`/keywords AI,区块链,新能源`\n2. 选择数据源：`/sources 知乎,微博,百度`\n3. 设置推送时间：`/time 09:00,18:00`\n4. 查看配置：`/status`\n5. 测试推送：`/test`"
                    }
                },
                {"tag": "hr"},
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": "**更多命令**\n\n• `/help` - 查看帮助\n• `/pause` - 暂停推送\n• `/resume` - 恢复推送"
                    }
                }
            ]
        }
    }


def build_help_card() -> Dict:
    """构建帮助卡片"""
    return {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": "📖 命令帮助"
                },
                "template": "blue"
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": "**配置命令**\n\n• `/start` - 初始化配置\n• `/keywords AI,区块链` - 设置关键词\n• `/sources 知乎,微博` - 选择数据源\n• `/time 09:00,18:00` - 设置推送时间\n• `/mode current` - 设置报告模式"
                    }
                },
                {"tag": "hr"},
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": "**查询命令**\n\n• `/status` - 查看当前配置\n• `/test` - 立即推送测试"
                    }
                },
                {"tag": "hr"},
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": "**控制命令**\n\n• `/pause` - 暂停推送\n• `/resume` - 恢复推送\n• `/help` - 查看帮助"
                    }
                },
                {"tag": "hr"},
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": "**可用数据源**\n\n知乎、微博、百度、抖音、今日头条、B站、贴吧、澎湃、华尔街见闻、财联社、凤凰网"
                    }
                }
            ]
        }
    }
