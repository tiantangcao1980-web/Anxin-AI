"""
阿里云短信服务 (Dysmsapi)

使用 alibabacloud_dysmsapi20170525 SDK。
在 .env 中配置以下变量后即可调用：
  ALIYUN_ACCESS_KEY_ID=<你的AccessKeyId>
  ALIYUN_ACCESS_KEY_SECRET=<你的AccessKeySecret>
  ALIYUN_SMS_SIGN_NAME=安心法务
  ALIYUN_SMS_TEMPLATE_VERIFY=SMS_xxxxxx     # 验证码模板
  ALIYUN_SMS_TEMPLATE_LOGIN=SMS_xxxxxx      # 登录验证码模板
  ALIYUN_SMS_TEMPLATE_RESET=SMS_xxxxxx      # 密码重置模板

阿里云控制台：https://dysms.console.aliyun.com
SDK 文档：https://help.aliyun.com/document_detail/419273.html
"""

import json
from typing import Any

from loguru import logger

from src.core.config import settings


class SMSService:
    """阿里云短信服务"""

    _client: Any | None = None

    @classmethod
    def _get_client(cls) -> Any | None:
        """懒加载阿里云短信客户端"""
        if cls._client is not None:
            return cls._client

        try:
            from alibabacloud_dysmsapi20170525.client import Client
            from alibabacloud_tea_openapi.models import Config
        except ImportError:
            logger.warning(
                "阿里云短信 SDK 未安装，请执行: "
                "pip install alibabacloud_dysmsapi20170525 alibabacloud_tea_openapi"
            )
            return None

        key_id = settings.ALIYUN_ACCESS_KEY_ID
        key_secret = settings.ALIYUN_ACCESS_KEY_SECRET
        if not key_id or not key_secret:
            logger.warning("阿里云 AccessKey 未配置，短信功能不可用")
            return None

        config = Config(
            access_key_id=key_id,
            access_key_secret=key_secret,
            region_id=settings.ALIYUN_SMS_REGION,
        )
        cls._client = Client(config)
        return cls._client

    @classmethod
    async def send_verification_code(
        cls,
        phone: str,
        code: str,
        template_type: str = "verify",
    ) -> bool:
        """
        发送短信验证码

        Args:
            phone: 手机号（11 位国内号码）
            code: 6 位验证码
            template_type: 模板类型 verify / login / reset
        Returns:
            是否发送成功
        """
        client = cls._get_client()
        if not client:
            logger.warning(f"短信服务不可用，验证码 {code} -> {phone} (仅日志)")
            return False

        # 选择模板
        template_map = {
            "verify": settings.ALIYUN_SMS_TEMPLATE_VERIFY,
            "login": settings.ALIYUN_SMS_TEMPLATE_LOGIN,
            "reset": settings.ALIYUN_SMS_TEMPLATE_RESET,
        }
        template_code = template_map.get(template_type, settings.ALIYUN_SMS_TEMPLATE_VERIFY)

        if not template_code:
            logger.warning(f"短信模板 {template_type} 未配置")
            return False

        try:
            from alibabacloud_dysmsapi20170525.models import SendSmsRequest

            request = SendSmsRequest(
                phone_numbers=phone,
                sign_name=settings.ALIYUN_SMS_SIGN_NAME,
                template_code=template_code,
                template_param=json.dumps({"code": code}),
            )

            response = client.send_sms(request)
            body = response.body

            if body.code == "OK":
                logger.info(f"短信发送成功: phone={phone[-4:]}, type={template_type}")
                return True
            else:
                logger.error(f"短信发送失败: code={body.code}, msg={body.message}")
                return False

        except Exception as e:
            logger.error(f"短信发送异常: {e}")
            return False

    @classmethod
    def is_available(cls) -> bool:
        """检查短信服务是否可用"""
        return bool(
            settings.ALIYUN_ACCESS_KEY_ID
            and settings.ALIYUN_ACCESS_KEY_SECRET
            and settings.ALIYUN_SMS_SIGN_NAME
        )


# 模块级单例
sms_service = SMSService()
