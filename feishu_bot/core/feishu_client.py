"""
飞书 API 客户端
"""

import logging
import requests
from typing import Dict, Optional
import time

logger = logging.getLogger(__name__)


class FeishuClient:
    """飞书 API 客户端"""

    def __init__(self, app_id: str, app_secret: str):
        self.app_id = app_id
        self.app_secret = app_secret
        self.base_url = "https://open.feishu.cn/open-apis"
        self._access_token: Optional[str] = None
        self._token_expire_time: float = 0  # token 过期时间戳

    def get_access_token(self) -> str:
        """获取 tenant_access_token"""
        # 检查 token 是否存在且未过期（提前5分钟刷新）
        if self._access_token and time.time() < (self._token_expire_time - 300):
            return self._access_token

        url = f"{self.base_url}/auth/v3/tenant_access_token/internal"
        payload = {
            "app_id": self.app_id,
            "app_secret": self.app_secret
        }

        try:
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            data = response.json()

            if data.get("code") == 0:
                self._access_token = data["tenant_access_token"]
                # 飞书返回的 expire 是秒数，通常是 7200（2小时）
                expire_seconds = data.get("expire", 7200)
                self._token_expire_time = time.time() + expire_seconds
                logger.info(f"获取 access_token 成功，有效期: {expire_seconds}秒")
                return self._access_token
            else:
                raise Exception(f"获取 access_token 失败: {data}")

        except Exception as e:
            logger.error(f"获取 access_token 异常: {e}")
            raise

    def send_message(self, user_id: str, content: Dict, msg_type: str = "interactive") -> bool:
        """
        发送消息给用户

        Args:
            user_id: 用户 open_id
            content: 消息内容
            msg_type: 消息类型 (text/interactive)

        Returns:
            bool: 是否发送成功
        """
        import json

        url = f"{self.base_url}/im/v1/messages"
        params = {"receive_id_type": "open_id"}
        headers = {
            "Authorization": f"Bearer {self.get_access_token()}",
            "Content-Type": "application/json"
        }

        # 确保 content 是有效的 JSON 字符串
        if isinstance(content, str):
            content_str = content
        else:
            content_str = json.dumps(content, ensure_ascii=False)

        payload = {
            "receive_id": user_id,
            "msg_type": msg_type,
            "content": content_str
        }

        try:
            response = requests.post(url, params=params, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()

            if data.get("code") == 0:
                logger.info(f"消息发送成功: user_id={user_id}")
                return True
            else:
                logger.error(f"消息发送失败: {data}")
                return False

        except Exception as e:
            logger.error(f"消息发送异常: user_id={user_id}, error={e}")
            return False

    def send_text_message(self, user_id: str, text: str) -> bool:
        """发送文本消息"""
        import json
        content = json.dumps({"text": text}, ensure_ascii=False)
        return self.send_message(user_id, content, msg_type="text")

    def send_card_message(self, user_id: str, card: Dict) -> bool:
        """发送卡片消息"""
        import json
        # card 参数格式: {"msg_type": "interactive", "card": {...}}
        # 提取 card 内容发送
        card_content = card.get("card", {})
        content = json.dumps(card_content, ensure_ascii=False)
        return self.send_message(user_id, content, msg_type="interactive")

    def get_user_info(self, user_id: str) -> Optional[Dict]:
        """获取用户信息"""
        url = f"{self.base_url}/contact/v3/users/{user_id}"
        params = {"user_id_type": "open_id"}
        headers = {
            "Authorization": f"Bearer {self.get_access_token()}"
        }

        try:
            response = requests.get(url, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()

            if data.get("code") == 0:
                return data.get("data", {}).get("user", {})
            else:
                logger.error(f"获取用户信息失败: {data}")
                return None

        except Exception as e:
            logger.error(f"获取用户信息异常: user_id={user_id}, error={e}")
            return None
