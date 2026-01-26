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
            # 导入 trendradar 核心模块
            from trendradar.context import AppContext
            from trendradar.crawler import DataFetcher

            # 创建上下文（只需要 config 参数）
            context = AppContext(config_dict)

            # 调试：打印平台配置
            logger.info(f"平台配置: {context.platforms}")
            logger.info(f"平台ID列表: {context.platform_ids}")

            # 准备平台 ID 列表
            ids = []
            for platform in context.platforms:
                if "name" in platform:
                    ids.append((platform["id"], platform["name"]))
                else:
                    ids.append(platform["id"])

            logger.info(f"准备抓取的平台: {ids}")

            # 创建数据抓取器
            proxy_url = config_dict.get('PROXY_URL')
            fetcher = DataFetcher(proxy_url)

            # 抓取数据
            request_interval = config_dict.get('REQUEST_INTERVAL', 1000)
            crawl_results, id_to_name, failed_ids = fetcher.crawl_websites(ids, request_interval)

            logger.info(f"抓取结果: 成功={len(crawl_results)}, 失败={len(failed_ids)}")

            if not crawl_results:
                logger.warning("抓取结果为空")
                return None

            # 检测新增标题
            new_titles = context.detect_new_titles(context.platform_ids)

            # 加载频率词配置
            word_groups, filter_words, global_filters = context.load_frequency_words()

            # 对于 current 模式，不需要加载历史数据
            # 因为这是飞书机器人的实时推送，每次都是独立的
            title_info = None

            # 统计分析
            stats, total_titles = context.count_frequency(
                results=crawl_results,
                word_groups=word_groups,
                filter_words=filter_words,
                id_to_name=id_to_name,
                title_info=title_info,
                new_titles=new_titles,
                mode=config_dict.get('REPORT_MODE', 'current'),
                global_filters=global_filters,
                quiet=True,
            )

            logger.info(f"统计分析完成: stats数量={len(stats)}, total_titles={total_titles}")

            # 构建结果
            results = {
                'hotlist': {},
                'new_items': []
            }

            # 将统计结果转换为飞书卡片需要的格式
            for stat in stats:
                keyword = stat['word']
                titles = stat.get('titles', [])

                logger.info(f"处理关键词: {keyword}, 标题数量={len(titles)}")

                if titles:
                    results['hotlist'][keyword] = []
                    for title_data in titles:
                        news_item = {
                            'title': title_data['title'],
                            'url': title_data.get('url', '#'),
                            'platform': title_data.get('source_name', '未知'),
                            'is_new': title_data.get('is_new', False)
                        }
                        results['hotlist'][keyword].append(news_item)

                        # 如果是新增，也添加到 new_items
                        if title_data.get('is_new', False):
                            results['new_items'].append({
                                'title': title_data['title'],
                                'url': title_data.get('url', '#'),
                                'platform': title_data.get('source_name', '未知')
                            })

            logger.info(f"构建结果完成: hotlist关键词数={len(results['hotlist'])}, new_items数={len(results['new_items'])}")

            return results

        except Exception as e:
            logger.error(f"抓取分析异常: {e}", exc_info=True)
            return None
