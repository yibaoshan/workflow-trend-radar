"""
命令处理器
"""

import logging
from typing import Optional, Tuple
import json

from ..storage.database import Database
from ..storage.models import UserConfig
from ..core.feishu_client import FeishuClient
from ..core.message_builder import build_welcome_card, build_help_card, build_status_card
from ..config.user_config import PLATFORM_MAPPING

logger = logging.getLogger(__name__)


class CommandHandler:
    """命令处理器"""

    def __init__(self, db: Database, feishu_client: FeishuClient):
        self.db = db
        self.feishu_client = feishu_client

    def handle_command(self, user_id: str, message: str) -> Tuple[bool, str]:
        """
        处理用户命令

        Args:
            user_id: 用户 ID
            message: 消息内容

        Returns:
            tuple: (是否成功, 响应消息)
        """
        message = message.strip()

        # 如果不是命令格式，自动触发帮助
        if not message.startswith('/'):
            return self._handle_help(user_id, "")

        parts = message.split(maxsplit=1)
        command = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        # 命令路由
        handlers = {
            '/start': self._handle_start,
            '/keywords': self._handle_keywords,
            '/sources': self._handle_sources,
            '/time': self._handle_time,
            '/mode': self._handle_mode,
            '/status': self._handle_status,
            '/test': self._handle_test,
            '/pause': self._handle_pause,
            '/resume': self._handle_resume,
            '/help': self._handle_help,
        }

        handler = handlers.get(command)
        if handler:
            return handler(user_id, args)
        else:
            return False, f"未知命令: {command}\n输入 /help 查看帮助"

    def _handle_start(self, user_id: str, args: str) -> Tuple[bool, str]:
        """处理 /start 命令"""
        config = self.db.get_user_config(user_id)

        if config:
            return True, "您已经初始化过配置了\n输入 /status 查看当前配置\n输入 /help 查看帮助"

        # 创建默认配置
        config = UserConfig(
            user_id=user_id,
            keywords=json.dumps(["AI", "区块链"], ensure_ascii=False),
            platforms=json.dumps(["zhihu", "weibo"], ensure_ascii=False),
            push_times=json.dumps(["09:00"], ensure_ascii=False),
            timezone="Asia/Shanghai",
            report_mode="current",
            enabled=1
        )

        self.db.save_user_config(config)

        # 发送欢迎卡片
        card = build_welcome_card()
        self.feishu_client.send_card_message(user_id, card)

        return True, "初始化成功！已为您设置默认配置\n输入 /status 查看配置"

    def _handle_keywords(self, user_id: str, args: str) -> Tuple[bool, str]:
        """处理 /keywords 命令"""
        if not args:
            return False, "请提供关键词，例如：/keywords AI,区块链,新能源"

        keywords = [k.strip() for k in args.split(',') if k.strip()]

        if not keywords:
            return False, "关键词不能为空"

        if len(keywords) > 10:
            return False, "关键词数量不能超过 10 个"

        config = self.db.get_user_config(user_id)
        if not config:
            config = UserConfig(user_id=user_id)

        config.set_keywords(keywords)
        self.db.save_user_config(config)

        keywords_str = "、".join(keywords)
        return True, f"✅ 关键词已设置：{keywords_str}\n\n下一步：\n• 选择数据源：/sources 知乎,微博\n• 设置推送时间：/time 09:00"

    def _handle_sources(self, user_id: str, args: str) -> Tuple[bool, str]:
        """处理 /sources 命令"""
        if not args:
            available = "、".join(PLATFORM_MAPPING.keys())
            return False, f"请提供数据源，例如：/sources 知乎,微博\n\n可用数据源：{available}"

        source_names = [s.strip() for s in args.split(',') if s.strip()]

        if not source_names:
            return False, "数据源不能为空"

        # 转换为平台 ID
        platform_ids = []
        invalid_sources = []

        for name in source_names:
            pid = PLATFORM_MAPPING.get(name)
            if pid:
                platform_ids.append(pid)
            else:
                invalid_sources.append(name)

        if invalid_sources:
            available = "、".join(PLATFORM_MAPPING.keys())
            return False, f"无效的数据源：{', '.join(invalid_sources)}\n\n可用数据源：{available}"

        config = self.db.get_user_config(user_id)
        if not config:
            config = UserConfig(user_id=user_id)

        config.set_platforms(platform_ids)
        self.db.save_user_config(config)

        sources_str = "、".join(source_names)
        return True, f"✅ 数据源已设置：{sources_str}\n\n下一步：\n• 设置推送时间：/time 09:00,18:00"

    def _handle_time(self, user_id: str, args: str) -> Tuple[bool, str]:
        """处理 /time 命令"""
        if not args:
            return False, "请提供推送时间，例如：/time 09:00,18:00"

        times = [t.strip() for t in args.split(',') if t.strip()]

        if not times:
            return False, "推送时间不能为空"

        # 验证时间格式
        for time_str in times:
            if ':' not in time_str:
                return False, f"时间格式错误：{time_str}，应为 HH:MM 格式"

            parts = time_str.split(':')
            if len(parts) != 2:
                return False, f"时间格式错误：{time_str}，应为 HH:MM 格式"

            try:
                hour = int(parts[0])
                minute = int(parts[1])
                if not (0 <= hour <= 23 and 0 <= minute <= 59):
                    return False, f"时间范围错误：{time_str}"
            except ValueError:
                return False, f"时间格式错误：{time_str}"

        config = self.db.get_user_config(user_id)
        if not config:
            config = UserConfig(user_id=user_id)

        config.set_push_times(times)
        self.db.save_user_config(config)

        times_str = "、".join(times)
        return True, f"✅ 推送时间已设置：每天 {times_str}\n\n配置完成！\n• 查看配置：/status\n• 测试推送：/test"

    def _handle_mode(self, user_id: str, args: str) -> Tuple[bool, str]:
        """处理 /mode 命令"""
        valid_modes = ['daily', 'current', 'incremental']

        if not args or args not in valid_modes:
            return False, f"请提供有效的报告模式：{', '.join(valid_modes)}\n\n• daily - 当日汇总\n• current - 当前榜单\n• incremental - 增量监控"

        config = self.db.get_user_config(user_id)
        if not config:
            config = UserConfig(user_id=user_id)

        config.report_mode = args
        self.db.save_user_config(config)

        mode_desc = {
            'daily': '当日汇总模式',
            'current': '当前榜单模式',
            'incremental': '增量监控模式'
        }

        return True, f"✅ 报告模式已设置：{mode_desc[args]}"

    def _handle_status(self, user_id: str, args: str) -> Tuple[bool, str]:
        """处理 /status 命令"""
        config = self.db.get_user_config(user_id)

        if not config:
            return False, "您还未初始化配置\n输入 /start 开始配置"

        keywords = config.get_keywords()
        platforms = config.get_platforms()
        push_times = config.get_push_times()

        # 转换平台 ID 为名称
        from ..config.user_config import PLATFORM_NAME_MAPPING
        platform_names = [PLATFORM_NAME_MAPPING.get(pid, pid) for pid in platforms]

        # 发送状态卡片
        card = build_status_card(keywords, platform_names, push_times, config.report_mode, config.enabled == 1)
        self.feishu_client.send_card_message(user_id, card)

        return True, ""

    def _handle_test(self, user_id: str, args: str) -> Tuple[bool, str]:
        """处理 /test 命令"""
        config = self.db.get_user_config(user_id)

        if not config:
            return False, "您还未初始化配置\n输入 /start 开始配置"

        keywords = config.get_keywords()
        platforms = config.get_platforms()

        if not keywords or not platforms:
            return False, "配置不完整，请先设置关键词和数据源\n• /keywords AI,区块链\n• /sources 知乎,微博"

        return True, "✅ 测试推送已触发，请稍候..."

    def _handle_pause(self, user_id: str, args: str) -> Tuple[bool, str]:
        """处理 /pause 命令"""
        config = self.db.get_user_config(user_id)

        if not config:
            return False, "您还未初始化配置"

        if config.enabled == 0:
            return True, "推送已经是暂停状态"

        config.enabled = 0
        self.db.save_user_config(config)

        return True, "✅ 推送已暂停\n输入 /resume 恢复推送"

    def _handle_resume(self, user_id: str, args: str) -> Tuple[bool, str]:
        """处理 /resume 命令"""
        config = self.db.get_user_config(user_id)

        if not config:
            return False, "您还未初始化配置"

        if config.enabled == 1:
            return True, "推送已经是启用状态"

        config.enabled = 1
        self.db.save_user_config(config)

        return True, "✅ 推送已恢复"

    def _handle_help(self, user_id: str, args: str) -> Tuple[bool, str]:
        """处理 /help 命令"""
        card = build_help_card()
        self.feishu_client.send_card_message(user_id, card)

        return True, "帮助信息已发送"
