"""
FastAPI 应用入口
"""

import logging
import sys
from pathlib import Path
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
import uvicorn

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from feishu_bot.config.settings import settings
from feishu_bot.storage.database import Database
from feishu_bot.core.feishu_client import FeishuClient
from feishu_bot.core.command_handler import CommandHandler
from feishu_bot.scheduler.pusher import Pusher
from feishu_bot.scheduler.job_manager import JobManager

# 配置日志
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/app/logs/feishu_bot.log') if Path('/app/logs').exists() else logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# 创建 FastAPI 应用
app = FastAPI(title="Feishu Trend Bot", version="1.0.0")

# 全局变量
db: Database = None
feishu_client: FeishuClient = None
command_handler: CommandHandler = None
pusher: Pusher = None
job_manager: JobManager = None


@app.on_event("startup")
def startup_event():
    """应用启动事件"""
    global db, feishu_client, command_handler, pusher, job_manager

    try:
        # 验证配置
        settings.validate()
        logger.info("配置验证通过")

        # 初始化数据库
        db = Database(settings.DATABASE_PATH)
        logger.info(f"数据库初始化完成: {settings.DATABASE_PATH}")

        # 初始化飞书客户端
        feishu_client = FeishuClient(settings.FEISHU_APP_ID, settings.FEISHU_APP_SECRET)
        logger.info("飞书客户端初始化完成")

        # 初始化命令处理器
        command_handler = CommandHandler(db, feishu_client)
        logger.info("命令处理器初始化完成")

        # 初始化推送器
        base_config_path = str(project_root / "config" / "config.yaml")
        pusher = Pusher(db, feishu_client, base_config_path)
        logger.info("推送器初始化完成")

        # 初始化任务调度器
        job_manager = JobManager(db, pusher)
        job_manager.start()
        logger.info("任务调度器启动完成")

        logger.info("应用启动成功")

    except Exception as e:
        logger.error(f"应用启动失败: {e}", exc_info=True)
        raise


@app.on_event("shutdown")
def shutdown_event():
    """应用关闭事件"""
    global job_manager

    if job_manager:
        job_manager.stop()
        logger.info("任务调度器已停止")

    logger.info("应用已关闭")


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "ok", "version": "1.0.0"}


@app.post("/api/event")
async def handle_event(request: Request):
    """
    处理飞书事件订阅
    """
    try:
        body = await request.json()
        logger.info(f"收到事件: {body}")

        # 处理 URL 验证
        if body.get("type") == "url_verification":
            challenge = body.get("challenge", "")
            return {"challenge": challenge}

        # 处理消息事件
        if body.get("header", {}).get("event_type") == "im.message.receive_v1":
            event = body.get("event", {})
            message = event.get("message", {})
            sender = event.get("sender", {})

            user_id = sender.get("sender_id", {}).get("open_id", "")
            message_type = message.get("message_type", "")
            content = message.get("content", "")

            if message_type == "text":
                import json
                content_dict = json.loads(content)
                text = content_dict.get("text", "").strip()

                logger.info(f"收到消息: user_id={user_id}, text={text}")

                # 处理命令
                success, response = command_handler.handle_command(user_id, text)

                # 发送响应
                if response:
                    feishu_client.send_text_message(user_id, response)

                # 如果是测试命令，立即执行推送
                if text.strip() == "/test":
                    await pusher.push_to_user(user_id)

        return {"code": 0, "msg": "success"}

    except Exception as e:
        logger.error(f"处理事件异常: {e}", exc_info=True)
        return {"code": -1, "msg": str(e)}


@app.post("/api/card")
async def handle_card_action(request: Request):
    """
    处理消息卡片交互
    """
    try:
        body = await request.json()
        logger.info(f"收到卡片交互: {body}")

        # 处理 URL 验证（飞书配置回调地址时会发送验证请求）
        if body.get("type") == "url_verification":
            challenge = body.get("challenge", "")
            logger.info(f"卡片回调 URL 验证: challenge={challenge}")
            return {"challenge": challenge}

        action = body.get("action", {})
        value = action.get("value", {})
        user_id = body.get("open_id", "")

        action_type = value.get("action", "")

        if action_type == "view_config":
            # 查看配置
            success, response = command_handler.handle_command(user_id, "/status")
            if response:
                feishu_client.send_text_message(user_id, response)

        elif action_type == "pause":
            # 暂停推送
            success, response = command_handler.handle_command(user_id, "/pause")
            if response:
                feishu_client.send_text_message(user_id, response)

            # 重新加载任务
            job_manager.reload_user_jobs(user_id)

        return {"code": 0, "msg": "success"}

    except Exception as e:
        logger.error(f"处理卡片交互异常: {e}", exc_info=True)
        return {"code": -1, "msg": str(e)}


if __name__ == "__main__":
    uvicorn.run(
        "feishu_bot.main:app",
        host=settings.HOST,
        port=settings.PORT,
        log_level=settings.LOG_LEVEL.lower()
    )
