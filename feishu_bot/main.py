"""
FastAPI 应用入口
"""

import logging
import sys
import json
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
user_temp_state = {}  # 用户临时状态（数据源多选等）
user_input_mode = {}  # 用户输入模式（等待输入关键词、时间等）


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

                # 检查是否处于输入模式
                if user_id in user_input_mode:
                    input_type = user_input_mode[user_id]

                    if input_type == "waiting_keyword":
                        # 处理关键词输入
                        keyword = text.strip()
                        if keyword:
                            config = db.get_user_config(user_id)
                            keywords = config.get_keywords()
                            if keyword not in keywords and len(keywords) < 10:
                                keywords.append(keyword)
                                config.set_keywords(keywords)
                                db.save_user_config(config)

                                from feishu_bot.core.message_builder import build_keywords_menu_card
                                card = build_keywords_menu_card(keywords)
                                feishu_client.send_card_message(user_id, card)
                                feishu_client.send_text_message(user_id, f"✅ 已添加关键词：{keyword}")
                            elif keyword in keywords:
                                feishu_client.send_text_message(user_id, f"⚠️ 关键词已存在：{keyword}")
                            else:
                                feishu_client.send_text_message(user_id, "⚠️ 关键词数量已达上限（10个）")
                        else:
                            feishu_client.send_text_message(user_id, "⚠️ 关键词不能为空")

                        # 清除输入模式
                        del user_input_mode[user_id]
                        return {"code": 0, "msg": "success"}

                    elif input_type == "waiting_time":
                        # 处理时间输入
                        time_str = text.strip()
                        if ':' in time_str:
                            parts = time_str.split(':')
                            if len(parts) == 2:
                                try:
                                    hour = int(parts[0])
                                    minute = int(parts[1])
                                    if 0 <= hour <= 23 and 0 <= minute <= 59:
                                        config = db.get_user_config(user_id)
                                        push_times = config.get_push_times()
                                        if time_str not in push_times:
                                            push_times.append(time_str)
                                            config.set_push_times(push_times)
                                            db.save_user_config(config)

                                            # 重新加载任务
                                            job_manager.reload_user_jobs(user_id)

                                            from feishu_bot.core.message_builder import build_time_menu_card
                                            card = build_time_menu_card(push_times)
                                            feishu_client.send_card_message(user_id, card)
                                            feishu_client.send_text_message(user_id, f"✅ 已添加推送时间：{time_str}")
                                        else:
                                            feishu_client.send_text_message(user_id, f"⚠️ 推送时间已存在：{time_str}")
                                    else:
                                        feishu_client.send_text_message(user_id, "⚠️ 时间范围错误，小时应为0-23，分钟应为0-59")
                                except ValueError:
                                    feishu_client.send_text_message(user_id, "⚠️ 时间格式错误，请使用 HH:MM 格式（例如：09:30）")
                            else:
                                feishu_client.send_text_message(user_id, "⚠️ 时间格式错误，请使用 HH:MM 格式（例如：09:30）")
                        else:
                            feishu_client.send_text_message(user_id, "⚠️ 时间格式错误，请使用 HH:MM 格式（例如：09:30）")

                        # 清除输入模式
                        del user_input_mode[user_id]
                        return {"code": 0, "msg": "success"}

                # 如果不是命令，显示当前配置状态
                if not text.startswith('/'):
                    from feishu_bot.core.message_builder import build_status_card
                    from feishu_bot.config.user_config import PLATFORM_NAME_MAPPING

                    config = db.get_user_config(user_id)

                    if not config:
                        # 如果没有配置，创建默认配置
                        from feishu_bot.storage.models import UserConfig
                        from feishu_bot.config.user_config import PLATFORM_MAPPING

                        user_info = feishu_client.get_user_info(user_id)
                        user_timezone = "Asia/Shanghai"
                        if user_info:
                            user_timezone = user_info.get("time_zone", "Asia/Shanghai")

                        all_platforms = list(PLATFORM_MAPPING.values())
                        config = UserConfig(
                            user_id=user_id,
                            keywords=json.dumps(["AI", "跨境电商"], ensure_ascii=False),
                            platforms=json.dumps(all_platforms, ensure_ascii=False),
                            push_times=json.dumps(["09:00"], ensure_ascii=False),
                            timezone=user_timezone,
                            report_mode="current",
                            enabled=1
                        )
                        db.save_user_config(config)

                    # 显示配置状态卡片
                    keywords = config.get_keywords()
                    platforms = config.get_platforms()
                    push_times = config.get_push_times()
                    platform_names = [PLATFORM_NAME_MAPPING.get(pid, pid) for pid in platforms]

                    card = build_status_card(keywords, platform_names, push_times, config.report_mode, config.enabled == 1)
                    feishu_client.send_card_message(user_id, card)
                else:
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

        # 解析 value（可能是 JSON 字符串，需要解析 1-2 次）
        if isinstance(value, str):
            try:
                value = json.loads(value)
                # 如果解析后还是字符串，再解析一次（双重编码的情况）
                if isinstance(value, str):
                    value = json.loads(value)
            except:
                value = {}

        action_type = value.get("action", "") if isinstance(value, dict) else ""

        from feishu_bot.core.message_builder import (
            build_main_menu_card, build_keywords_menu_card,
            build_sources_menu_card, build_time_menu_card,
            build_input_card, build_status_card, build_text_prompt_card
        )
        from feishu_bot.config.user_config import PLATFORM_NAME_MAPPING

        # 获取用户配置
        config = db.get_user_config(user_id)
        if not config:
            from feishu_bot.storage.models import UserConfig
            from feishu_bot.config.user_config import PLATFORM_MAPPING

            # 获取用户信息以获取时区
            user_info = feishu_client.get_user_info(user_id)
            user_timezone = "Asia/Shanghai"  # 默认时区

            if user_info:
                user_timezone = user_info.get("time_zone", "Asia/Shanghai")
                logger.info(f"用户时区: user_id={user_id}, timezone={user_timezone}")

            # 创建默认配置（所有数据源）
            all_platforms = list(PLATFORM_MAPPING.values())
            config = UserConfig(
                user_id=user_id,
                keywords=json.dumps(["AI", "跨境电商"], ensure_ascii=False),
                platforms=json.dumps(all_platforms, ensure_ascii=False),
                push_times=json.dumps(["09:00"], ensure_ascii=False),
                timezone=user_timezone,
                report_mode="current",
                enabled=1
            )
            db.save_user_config(config)

        # 导航类操作
        if action_type == "show_main_menu":
            card = build_main_menu_card(config.enabled == 1)
            feishu_client.send_card_message(user_id, card)

        elif action_type == "show_keywords_menu":
            keywords = config.get_keywords()
            card = build_keywords_menu_card(keywords)
            feishu_client.send_card_message(user_id, card)

        elif action_type == "show_sources_menu":
            # 初始化临时状态
            if user_id not in user_temp_state:
                user_temp_state[user_id] = {}
            user_temp_state[user_id]["sources"] = config.get_platforms().copy()

            card = build_sources_menu_card(user_temp_state[user_id]["sources"])
            feishu_client.send_card_message(user_id, card)

        elif action_type == "show_time_menu":
            push_times = config.get_push_times()
            card = build_time_menu_card(push_times)
            feishu_client.send_card_message(user_id, card)

        elif action_type == "show_status":
            keywords = config.get_keywords()
            platforms = config.get_platforms()
            push_times = config.get_push_times()
            platform_names = [PLATFORM_NAME_MAPPING.get(pid, pid) for pid in platforms]

            card = build_status_card(keywords, platform_names, push_times, config.report_mode, config.enabled == 1)
            feishu_client.send_card_message(user_id, card)

        # 关键词操作
        elif action_type == "add_keyword_prompt":
            # 使用降级方案：提示用户直接发送文本消息
            user_input_mode[user_id] = "waiting_keyword"
            card = build_text_prompt_card(
                "**请输入关键词**",
                "人工智能"
            )
            feishu_client.send_card_message(user_id, card)

        elif action_type == "add_keyword_confirm":
            # 获取输入内容
            form_value = action.get("form_value", {})
            keyword = form_value.get("user_input", "").strip()

            if keyword:
                keywords = config.get_keywords()
                if keyword not in keywords and len(keywords) < 10:
                    keywords.append(keyword)
                    config.set_keywords(keywords)
                    db.save_user_config(config)

                    # 刷新关键词管理卡片
                    card = build_keywords_menu_card(keywords)
                    feishu_client.send_card_message(user_id, card)
                    feishu_client.send_text_message(user_id, f"✅ 已添加关键词：{keyword}")
                elif keyword in keywords:
                    feishu_client.send_text_message(user_id, f"⚠️ 关键词已存在：{keyword}")
                else:
                    feishu_client.send_text_message(user_id, "⚠️ 关键词数量已达上限（10个）")
            else:
                feishu_client.send_text_message(user_id, "⚠️ 关键词不能为空")

        elif action_type == "remove_keyword":
            keyword = value.get("keyword", "")
            keywords = config.get_keywords()
            if keyword in keywords:
                keywords.remove(keyword)
                config.set_keywords(keywords)
                db.save_user_config(config)

                # 刷新关键词管理卡片
                card = build_keywords_menu_card(keywords)
                feishu_client.send_card_message(user_id, card)
                feishu_client.send_text_message(user_id, f"✅ 已删除关键词：{keyword}")

        # 数据源操作
        elif action_type == "toggle_source":
            source = value.get("source", "")
            if user_id not in user_temp_state:
                user_temp_state[user_id] = {"sources": config.get_platforms().copy()}

            sources = user_temp_state[user_id]["sources"]
            if source in sources:
                sources.remove(source)
            else:
                sources.append(source)

            # 刷新数据源选择卡片
            card = build_sources_menu_card(sources)
            feishu_client.send_card_message(user_id, card)

        elif action_type == "save_sources":
            if user_id in user_temp_state and "sources" in user_temp_state[user_id]:
                sources = user_temp_state[user_id]["sources"]
                config.set_platforms(sources)
                db.save_user_config(config)

                # 清除临时状态
                del user_temp_state[user_id]["sources"]

                # 返回主菜单
                card = build_main_menu_card(config.enabled == 1)
                feishu_client.send_card_message(user_id, card)

                platform_names = [PLATFORM_NAME_MAPPING.get(pid, pid) for pid in sources]
                sources_text = "、".join(platform_names)
                feishu_client.send_text_message(user_id, f"✅ 数据源已保存：{sources_text}")

        # 时间操作
        elif action_type == "add_preset_time":
            time_str = value.get("time", "")
            push_times = config.get_push_times()

            if time_str and time_str not in push_times:
                push_times.append(time_str)
                config.set_push_times(push_times)
                db.save_user_config(config)

                # 重新加载任务
                job_manager.reload_user_jobs(user_id)

                # 刷新时间配置卡片
                card = build_time_menu_card(push_times)
                feishu_client.send_card_message(user_id, card)
                feishu_client.send_text_message(user_id, f"✅ 已添加推送时间：{time_str}")
            elif time_str in push_times:
                feishu_client.send_text_message(user_id, f"⚠️ 推送时间已存在：{time_str}")

        elif action_type == "add_custom_time_prompt":
            # 使用降级方案：提示用户直接发送文本消息
            user_input_mode[user_id] = "waiting_time"
            card = build_text_prompt_card(
                "**请输入推送时间**\n\n格式：HH:MM",
                "09:30"
            )
            feishu_client.send_card_message(user_id, card)

        elif action_type == "add_time_confirm":
            # 获取输入内容
            form_value = action.get("form_value", {})
            time_str = form_value.get("user_input", "").strip()

            # 验证时间格式
            if ':' in time_str:
                parts = time_str.split(':')
                if len(parts) == 2:
                    try:
                        hour = int(parts[0])
                        minute = int(parts[1])
                        if 0 <= hour <= 23 and 0 <= minute <= 59:
                            push_times = config.get_push_times()
                            if time_str not in push_times:
                                push_times.append(time_str)
                                config.set_push_times(push_times)
                                db.save_user_config(config)

                                # 重新加载任务
                                job_manager.reload_user_jobs(user_id)

                                # 刷新时间配置卡片
                                card = build_time_menu_card(push_times)
                                feishu_client.send_card_message(user_id, card)
                                feishu_client.send_text_message(user_id, f"✅ 已添加推送时间：{time_str}")
                            else:
                                feishu_client.send_text_message(user_id, f"⚠️ 推送时间已存在：{time_str}")
                        else:
                            feishu_client.send_text_message(user_id, "⚠️ 时间范围错误，小时应为0-23，分钟应为0-59")
                    except ValueError:
                        feishu_client.send_text_message(user_id, "⚠️ 时间格式错误，请使用 HH:MM 格式（例如：09:30）")
                else:
                    feishu_client.send_text_message(user_id, "⚠️ 时间格式错误，请使用 HH:MM 格式（例如：09:30）")
            else:
                feishu_client.send_text_message(user_id, "⚠️ 时间格式错误，请使用 HH:MM 格式（例如：09:30）")

        elif action_type == "remove_time":
            time_str = value.get("time", "")
            push_times = config.get_push_times()
            if time_str in push_times:
                push_times.remove(time_str)
                config.set_push_times(push_times)
                db.save_user_config(config)

                # 重新加载任务
                job_manager.reload_user_jobs(user_id)

                # 刷新时间配置卡片
                card = build_time_menu_card(push_times)
                feishu_client.send_card_message(user_id, card)
                feishu_client.send_text_message(user_id, f"✅ 已删除推送时间：{time_str}")

        # 控制操作
        elif action_type == "toggle_enabled":
            config.enabled = 0 if config.enabled == 1 else 1
            db.save_user_config(config)

            # 重新加载任务
            job_manager.reload_user_jobs(user_id)

            # 刷新状态卡片
            keywords = config.get_keywords()
            platforms = config.get_platforms()
            push_times = config.get_push_times()
            platform_names = [PLATFORM_NAME_MAPPING.get(pid, pid) for pid in platforms]

            card = build_status_card(keywords, platform_names, push_times, config.report_mode, config.enabled == 1)
            feishu_client.send_card_message(user_id, card)

            status_text = "✅ 推送已恢复" if config.enabled == 1 else "⏸️ 推送已暂停"
            feishu_client.send_text_message(user_id, status_text)

        # 旧版兼容
        elif action_type == "view_config":
            success, response = command_handler.handle_command(user_id, "/status")
            if response:
                feishu_client.send_text_message(user_id, response)

        elif action_type == "pause":
            success, response = command_handler.handle_command(user_id, "/pause")
            if response:
                feishu_client.send_text_message(user_id, response)
            job_manager.reload_user_jobs(user_id)

        # 无操作（占位按钮）
        elif action_type == "noop":
            pass

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
