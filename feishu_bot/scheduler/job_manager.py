"""
任务调度管理器
"""

import logging
import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from ..storage.database import Database
from .pusher import Pusher

logger = logging.getLogger(__name__)


class JobManager:
    """任务调度管理器"""

    def __init__(self, db: Database, pusher: Pusher):
        self.db = db
        self.pusher = pusher
        # 使用 UTC 时区的调度器
        self.scheduler = AsyncIOScheduler(timezone='UTC')

    def _sync_push_wrapper(self, user_id: str):
        """
        同步包装函数，用于在定时任务中调用异步的 push_to_user

        APScheduler 在独立线程中执行任务，需要创建新的事件循环
        """
        try:
            # 创建新的事件循环（APScheduler 在独立线程中执行）
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                # 运行异步推送任务
                loop.run_until_complete(self.pusher.push_to_user(user_id))
            finally:
                # 清理事件循环
                loop.close()
        except Exception as e:
            logger.error(f"定时推送执行失败: user_id={user_id}, error={e}", exc_info=True)

    def start(self):
        """启动调度器"""
        self.scheduler.start()
        self.reload_all_jobs()
        logger.info("任务调度器已启动")

    def stop(self):
        """停止调度器"""
        self.scheduler.shutdown()
        logger.info("任务调度器已停止")

    def reload_all_jobs(self):
        """重新加载所有用户任务"""
        self.scheduler.remove_all_jobs()

        users = self.db.get_enabled_users()
        logger.info(f"加载 {len(users)} 个用户的定时任务")

        for user in users:
            self.add_user_jobs(user)

    def add_user_jobs(self, user):
        """为单个用户添加定时任务"""
        push_times = user.get_push_times()
        user_timezone = user.timezone  # 用户所在时区

        for push_time in push_times:
            try:
                hour, minute = push_time.split(':')

                # 将用户时区的时间转换为 UTC 时间
                user_tz = ZoneInfo(user_timezone)
                utc_tz = ZoneInfo('UTC')

                # 创建用户时区的时间（使用今天的日期作为参考）
                now = datetime.now(user_tz)
                user_time = now.replace(hour=int(hour), minute=int(minute), second=0, microsecond=0)

                # 转换为 UTC 时间
                utc_time = user_time.astimezone(utc_tz)
                utc_hour = utc_time.hour
                utc_minute = utc_time.minute

                self.scheduler.add_job(
                    func=self._sync_push_wrapper,
                    trigger=CronTrigger(hour=utc_hour, minute=utc_minute, timezone='UTC'),
                    args=[user.user_id],
                    id=f"push_{user.user_id}_{push_time}",
                    replace_existing=True
                )

                logger.info(f"添加定时任务: user_id={user.user_id}, user_time={push_time} ({user_timezone}), utc_time={utc_hour:02d}:{utc_minute:02d} (UTC)")

            except Exception as e:
                logger.error(f"添加定时任务失败: user_id={user.user_id}, time={push_time}, error={e}")

    def remove_user_jobs(self, user_id: str):
        """移除用户的所有定时任务"""
        jobs = self.scheduler.get_jobs()
        for job in jobs:
            if job.id.startswith(f"push_{user_id}_"):
                self.scheduler.remove_job(job.id)
                logger.info(f"移除定时任务: {job.id}")

    def reload_user_jobs(self, user_id: str):
        """重新加载单个用户的定时任务"""
        self.remove_user_jobs(user_id)

        user = self.db.get_user_config(user_id)
        if user and user.enabled:
            self.add_user_jobs(user)
