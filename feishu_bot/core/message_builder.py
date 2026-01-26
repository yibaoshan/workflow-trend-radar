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
                "value": json.dumps({"action": "view_config"}, ensure_ascii=False)
            },
            {
                "tag": "button",
                "text": {"tag": "plain_text", "content": "暂停推送"},
                "type": "default",
                "value": json.dumps({"action": "pause"}, ensure_ascii=False)
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
                        "content": "**配置命令**\n\n• `/start` - 初始化配置\n• `/keywords` `AI,区块链` - 设置关键词\n• `/sources` `知乎,微博` - 选择数据源\n• `/time` `09:00,18:00` - 设置推送时间\n• `/mode` `current` - 设置报告模式"
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


def build_status_card(keywords: list, platform_names: list, push_times: list, report_mode: str, enabled: bool) -> Dict:
    """构建状态卡片（增强版，带编辑按钮）"""
    # 构建配置信息
    keywords_text = "、".join(keywords) if keywords else "未设置"
    sources_text = "、".join(platform_names) if platform_names else "未设置"
    times_text = "、".join(push_times) if push_times else "未设置"

    mode_map = {
        'daily': '当日汇总',
        'current': '当前榜单',
        'incremental': '增量监控'
    }
    mode_text = mode_map.get(report_mode, report_mode)
    status_text = "✅ 启用" if enabled else "⏸️ 已暂停"

    elements = [
        {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": f"**关键词**\n{keywords_text}"
            }
        },
        {
            "tag": "action",
            "actions": [
                {
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": "✏️ 编辑关键词"},
                    "type": "default",
                    "value": json.dumps({"action": "show_keywords_menu"}, ensure_ascii=False)
                }
            ]
        },
        {"tag": "hr"},
        {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": f"**数据源**\n{sources_text}"
            }
        },
        {
            "tag": "action",
            "actions": [
                {
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": "✏️ 编辑数据源"},
                    "type": "default",
                    "value": json.dumps({"action": "show_sources_menu"}, ensure_ascii=False)
                }
            ]
        },
        {"tag": "hr"},
        {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": f"**推送时间**\n每天 {times_text}"
            }
        },
        {
            "tag": "action",
            "actions": [
                {
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": "✏️ 编辑时间"},
                    "type": "default",
                    "value": json.dumps({"action": "show_time_menu"}, ensure_ascii=False)
                }
            ]
        },
        {"tag": "hr"},
        {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": f"**报告模式**\n{mode_text}"
            }
        },
        {"tag": "hr"},
        {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": f"**状态**\n{status_text}"
            }
        },
        {"tag": "hr"},
        {
            "tag": "action",
            "actions": [
                {
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": "⏸️ 暂停推送" if enabled else "▶️ 恢复推送"},
                    "type": "danger" if enabled else "primary",
                    "value": json.dumps({"action": "toggle_enabled"}, ensure_ascii=False)
                },
                {
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": "🔙 返回主菜单"},
                    "type": "default",
                    "value": json.dumps({"action": "show_main_menu"}, ensure_ascii=False)
                }
            ]
        }
    ]

    return {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": "📋 当前配置"
                },
                "template": "green"
            },
            "elements": elements
        }
    }


def build_main_menu_card(enabled: bool = True) -> Dict:
    """构建主菜单卡片"""
    status_text = "✅ 已启用" if enabled else "⏸️ 已暂停"

    return {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": "🏠 热点推送助手"
                },
                "template": "blue"
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**当前状态**: {status_text}\n\n请选择要配置的项目："
                    }
                },
                {"tag": "hr"},
                {
                    "tag": "action",
                    "actions": [
                        {
                            "tag": "button",
                            "text": {"tag": "plain_text", "content": "📝 管理关键词"},
                            "type": "primary",
                            "value": json.dumps({"action": "show_keywords_menu"}, ensure_ascii=False)
                        },
                        {
                            "tag": "button",
                            "text": {"tag": "plain_text", "content": "📊 选择数据源"},
                            "type": "primary",
                            "value": json.dumps({"action": "show_sources_menu"}, ensure_ascii=False)
                        }
                    ]
                },
                {
                    "tag": "action",
                    "actions": [
                        {
                            "tag": "button",
                            "text": {"tag": "plain_text", "content": "⏰ 设置推送时间"},
                            "type": "primary",
                            "value": json.dumps({"action": "show_time_menu"}, ensure_ascii=False)
                        },
                        {
                            "tag": "button",
                            "text": {"tag": "plain_text", "content": "📋 查看配置"},
                            "type": "default",
                            "value": json.dumps({"action": "show_status"}, ensure_ascii=False)
                        }
                    ]
                }
            ]
        }
    }


def build_keywords_menu_card(keywords: list) -> Dict:
    """构建关键词管理卡片"""
    elements = [
        {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": f"**当前关键词** ({len(keywords)}/10)"
            }
        },
        {"tag": "hr"}
    ]

    # 显示关键词列表
    if keywords:
        for keyword in keywords:
            elements.append({
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": f"🔖 {keyword}"},
                        "type": "default",
                        "value": json.dumps({"action": "noop"}, ensure_ascii=False)
                    },
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "🗑️ 删除"},
                        "type": "danger",
                        "value": json.dumps({"action": "remove_keyword", "keyword": keyword}, ensure_ascii=False)
                    }
                ]
            })
    else:
        elements.append({
            "tag": "div",
            "text": {
                "tag": "plain_text",
                "content": "暂无关键词，请添加"
            }
        })

    elements.append({"tag": "hr"})

    # 操作按钮
    actions = [
        {
            "tag": "button",
            "text": {"tag": "plain_text", "content": "🔙 返回主菜单"},
            "type": "default",
            "value": json.dumps({"action": "show_main_menu"}, ensure_ascii=False)
        }
    ]

    if len(keywords) < 10:
        actions.insert(0, {
            "tag": "button",
            "text": {"tag": "plain_text", "content": "➕ 添加关键词"},
            "type": "primary",
            "value": json.dumps({"action": "add_keyword_prompt"}, ensure_ascii=False)
        })

    elements.append({
        "tag": "action",
        "actions": actions
    })

    return {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": "📝 关键词管理"
                },
                "template": "blue"
            },
            "elements": elements
        }
    }


def build_sources_menu_card(selected_sources: list) -> Dict:
    """构建数据源选择卡片"""
    from ..config.user_config import PLATFORM_MAPPING

    elements = [
        {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": f"**已选择**: {len(selected_sources)} 个数据源\n\n点击按钮切换选中状态："
            }
        },
        {"tag": "hr"}
    ]

    # 数据源按钮（每行2个）
    sources_list = list(PLATFORM_MAPPING.items())
    for i in range(0, len(sources_list), 2):
        actions = []
        for j in range(2):
            if i + j < len(sources_list):
                name, platform_id = sources_list[i + j]
                is_selected = platform_id in selected_sources
                button_text = f"✅ {name}" if is_selected else f"⬜ {name}"

                actions.append({
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": button_text},
                    "type": "primary" if is_selected else "default",
                    "value": json.dumps({"action": "toggle_source", "source": platform_id}, ensure_ascii=False)
                })

        elements.append({
            "tag": "action",
            "actions": actions
        })

    elements.append({"tag": "hr"})

    # 底部按钮
    elements.append({
        "tag": "action",
        "actions": [
            {
                "tag": "button",
                "text": {"tag": "plain_text", "content": "💾 保存"},
                "type": "primary",
                "value": json.dumps({"action": "save_sources"}, ensure_ascii=False)
            },
            {
                "tag": "button",
                "text": {"tag": "plain_text", "content": "🔙 返回主菜单"},
                "type": "default",
                "value": json.dumps({"action": "show_main_menu"}, ensure_ascii=False)
            }
        ]
    })

    return {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": "📊 选择数据源"
                },
                "template": "blue"
            },
            "elements": elements
        }
    }


def build_time_menu_card(push_times: list) -> Dict:
    """构建时间配置卡片"""
    elements = [
        {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": f"**当前推送时间** ({len(push_times)} 个)"
            }
        },
        {"tag": "hr"}
    ]

    # 显示当前时间列表
    if push_times:
        for time_str in push_times:
            elements.append({
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": f"⏰ {time_str}"},
                        "type": "default",
                        "value": json.dumps({"action": "noop"}, ensure_ascii=False)
                    },
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "🗑️ 删除"},
                        "type": "danger",
                        "value": json.dumps({"action": "remove_time", "time": time_str}, ensure_ascii=False)
                    }
                ]
            })
    else:
        elements.append({
            "tag": "div",
            "text": {
                "tag": "plain_text",
                "content": "暂无推送时间，请添加"
            }
        })

    elements.append({"tag": "hr"})

    # 预设时间按钮
    elements.append({
        "tag": "div",
        "text": {
            "tag": "lark_md",
            "content": "**快速添加**"
        }
    })

    preset_times = ["09:00", "12:00", "18:00", "21:00"]
    for i in range(0, len(preset_times), 2):
        actions = []
        for j in range(2):
            if i + j < len(preset_times):
                time_str = preset_times[i + j]
                is_added = time_str in push_times

                actions.append({
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": f"{'✅' if is_added else '➕'} {time_str}"},
                    "type": "default" if is_added else "primary",
                    "value": json.dumps({"action": "add_preset_time", "time": time_str}, ensure_ascii=False)
                })

        elements.append({
            "tag": "action",
            "actions": actions
        })

    elements.append({"tag": "hr"})

    # 底部按钮
    elements.append({
        "tag": "action",
        "actions": [
            {
                "tag": "button",
                "text": {"tag": "plain_text", "content": "➕ 自定义时间"},
                "type": "primary",
                "value": json.dumps({"action": "add_custom_time_prompt"}, ensure_ascii=False)
            },
            {
                "tag": "button",
                "text": {"tag": "plain_text", "content": "🔙 返回主菜单"},
                "type": "default",
                "value": json.dumps({"action": "show_main_menu"}, ensure_ascii=False)
            }
        ]
    })

    return {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": "⏰ 推送时间设置"
                },
                "template": "blue"
            },
            "elements": elements
        }
    }


def build_input_card(prompt_text: str, action_type: str, placeholder: str = "") -> Dict:
    """
    构建通用输入框卡片

    注意：飞书卡片的 input 组件在某些客户端版本可能存在兼容性问题
    如果输入框无法使用，建议降级为文本消息交互方式
    """
    return {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": "✍️ 输入信息"
                },
                "template": "blue"
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": prompt_text
                    }
                },
                {"tag": "hr"},
                {
                    "tag": "input",
                    "name": "user_input",
                    "required": True,
                    "placeholder": {"tag": "plain_text", "content": placeholder} if placeholder else {"tag": "plain_text", "content": "请输入内容"},
                    "default_value": "",
                    "width": "default",
                    "max_length": 100
                },
                {"tag": "hr"},
                {
                    "tag": "action",
                    "actions": [
                        {
                            "tag": "button",
                            "text": {"tag": "plain_text", "content": "✅ 确认"},
                            "type": "primary",
                            "value": json.dumps({"action": action_type}, ensure_ascii=False)
                        },
                        {
                            "tag": "button",
                            "text": {"tag": "plain_text", "content": "❌ 取消"},
                            "type": "default",
                            "value": json.dumps({"action": "show_main_menu"}, ensure_ascii=False)
                        }
                    ]
                }
            ]
        }
    }


def build_text_prompt_card(prompt_text: str, example: str = "") -> Dict:
    """
    构建文本提示卡片（降级方案）

    当 input 组件不可用时，使用此卡片提示用户直接发送文本消息
    """
    content = f"{prompt_text}\n\n**例如**: {example}" if example else prompt_text

    return {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": "✍️ 输入信息"
                },
                "template": "blue"
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": content
                    }
                },
                {"tag": "hr"},
                {
                    "tag": "div",
                    "text": {
                        "tag": "plain_text",
                        "content": "💡 请直接在聊天框中发送您要输入的内容"
                    }
                },
                {"tag": "hr"},
                {
                    "tag": "action",
                    "actions": [
                        {
                            "tag": "button",
                            "text": {"tag": "plain_text", "content": "🔙 返回主菜单"},
                            "type": "default",
                            "value": json.dumps({"action": "show_main_menu"}, ensure_ascii=False)
                        }
                    ]
                }
            ]
        }
    }

