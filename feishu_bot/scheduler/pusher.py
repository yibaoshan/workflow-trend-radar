"""
推送执行器
"""

import logging
import os
import tempfile
from typing import Dict, Optional
import yaml

from ..storage.database import Database
from ..storage.models import UserConfig
from ..core.feishu_client import FeishuClient
from ..core.message_builder import build_message_card
from ..config.user_config import generate_user_config, cleanup_temp_files

logger = logging.getLogger(__name__)


class Pusher:
    """推送执行器"""

    def __init__(self, db: Database, feishu_client: FeishuClient, base_config_path: str):
        self.db = db
        self.feishu_client = feishu_client
        self.base_config_path = base_config_path

    async def push_to_user(self, user_id: str) -> bool:
        """
        执行单个用户推送

        Args:
            user_id: 用户 ID

        Returns:
            bool: 是否推送成功
        """
        keywords_file = None

        try:
            # 1. 获取用户配置
            user_config = self.db.get_user_config(user_id)
            if not user_config or not user_config.enabled:
                logger.info(f"用户未启用或不存在: user_id={user_id}")
                return False

            # 检查配置完整性
            keywords = user_config.get_keywords()
            platforms = user_config.get_platforms()

            if not keywords or not platforms:
                logger.warning(f"用户配置不完整: user_id={user_id}")
                self.feishu_client.send_text_message(
                    user_id,
                    "⚠️ 配置不完整，无法推送\n请设置关键词和数据源：\n• /keywords AI,区块链\n• /sources 知乎,微博"
                )
                return False

            # 2. 生成临时配置
            config_dict, keywords_file = generate_user_config(user_config, self.base_config_path)

            # 3. 调用 trendradar 核心抓取
            results = await self._fetch_and_analyze(config_dict, keywords_file)

            if not results:
                logger.warning(f"抓取结果为空: user_id={user_id}")
                self.db.log_push(user_id, 0, 'success')
                return True

            # 4. 统计新闻数量
            news_count = 0
            hotlist = results.get('hotlist', {})
            for news_list in hotlist.values():
                news_count += len(news_list)

            new_items = results.get('new_items', [])
            news_count += len(new_items)

            # 5. 构建飞书消息卡片
            card = build_message_card(results, user_config, news_count)

            # 6. 发送消息
            success = self.feishu_client.send_card_message(user_id, card)

            if success:
                self.db.log_push(user_id, news_count, 'success')
                logger.info(f"推送成功: user_id={user_id}, news_count={news_count}")
            else:
                self.db.log_push(user_id, 0, 'failed', '消息发送失败')
                logger.error(f"推送失败: user_id={user_id}")

            return success

        except Exception as e:
            logger.error(f"推送异常: user_id={user_id}, error={e}", exc_info=True)
            self.db.log_push(user_id, 0, 'failed', str(e))
            return False

        finally:
            # 清理临时文件
            if keywords_file:
                cleanup_temp_files(keywords_file)

    async def _fetch_and_analyze(self, config_dict: Dict, keywords_file: str) -> Optional[Dict]:
        """
        调用 trendradar 核心进行抓取和分析

        Args:
            config_dict: 配置字典
            keywords_file: 关键词文件路径

        Returns:
            dict: 分析结果
        """
        try:
            # 写入临时配置文件
            temp_config_file = os.path.join(tempfile.gettempdir(), f"config_{os.getpid()}.yaml")
            with open(temp_config_file, 'w', encoding='utf-8') as f:
                yaml.dump(config_dict, f, allow_unicode=True)

            # 导入 trendradar 核心模块
            from trendradar.context import AppContext
            from trendradar.crawler import DataFetcher
            from trendradar.core.analyzer import analyze_news

            # 创建上下文
            context = AppContext(config_dict, keywords_file)

            # 抓取数据
            fetcher = DataFetcher(context)
            crawl_results = fetcher.fetch_all()

            if not crawl_results:
                logger.warning("抓取结果为空")
                return None

            # 分析数据
            results = analyze_news(context, crawl_results)

            # 清理临时配置文件
            if os.path.exists(temp_config_file):
                os.remove(temp_config_file)

            return results

        except Exception as e:
            logger.error(f"抓取分析异常: {e}", exc_info=True)
            return None
