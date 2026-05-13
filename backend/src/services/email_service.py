"""
阿里云邮件推送服务 (DirectMail)

使用 alibabacloud_dm20151123 SDK。
在 .env 中配置以下变量后即可调用：
  ALIYUN_ACCESS_KEY_ID=<你的AccessKeyId>        (与短信共用)
  ALIYUN_ACCESS_KEY_SECRET=<你的AccessKeySecret>  (与短信共用)
  ALIYUN_EMAIL_ACCOUNT=noreply@mail.anxinassistant.com
  ALIYUN_EMAIL_ALIAS=安心智能助手

阿里云控制台：https://dm.console.aliyun.com
SDK 文档：https://help.aliyun.com/document_detail/29444.html
"""
from typing import Any

from loguru import logger

from src.core.config import settings

# ========== 邮件模板 ==========

VERIFY_EMAIL_TEMPLATE = """
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 40px 20px;">
  <div style="text-align: center; margin-bottom: 30px;">
    <h2 style="color: #1a1a2e; margin: 0;">安心智能助手</h2>
    <p style="color: #666; font-size: 14px;">智能法律服务平台</p>
  </div>
  <div style="background: #f8f9fa; border-radius: 12px; padding: 30px; text-align: center;">
    <h3 style="color: #333; margin-top: 0;">{title}</h3>
    <p style="color: #666; font-size: 14px;">您的验证码为：</p>
    <div style="background: #fff; border: 2px solid #D4A574; border-radius: 8px; padding: 16px 24px; display: inline-block; margin: 16px 0;">
      <span style="font-size: 32px; font-weight: bold; letter-spacing: 8px; color: #D4A574;">{code}</span>
    </div>
    <p style="color: #999; font-size: 12px;">验证码 15 分钟内有效，请勿泄露给他人。</p>
  </div>
  <p style="color: #aaa; font-size: 12px; text-align: center; margin-top: 30px;">
    如果这不是您的操作，请忽略此邮件。<br/>
    &copy; 安心智能助手 anxinassistant.com
  </p>
</body>
</html>
"""


class EmailService:
    """阿里云邮件推送服务"""

    _client: Any | None = None

    @classmethod
    def _get_client(cls) -> Any | None:
        """懒加载阿里云邮件客户端"""
        if cls._client is not None:
            return cls._client

        try:
            from alibabacloud_dm20151123.client import Client
            from alibabacloud_tea_openapi.models import Config
        except ImportError:
            logger.warning(
                "阿里云邮件 SDK 未安装，请执行: "
                "pip install alibabacloud_dm20151123 alibabacloud_tea_openapi"
            )
            return None

        key_id = settings.ALIYUN_ACCESS_KEY_ID
        key_secret = settings.ALIYUN_ACCESS_KEY_SECRET
        if not key_id or not key_secret:
            logger.warning("阿里云 AccessKey 未配置，邮件功能不可用")
            return None

        account = settings.ALIYUN_EMAIL_ACCOUNT
        if not account:
            logger.warning("邮件发送地址 ALIYUN_EMAIL_ACCOUNT 未配置")
            return None

        config = Config(
            access_key_id=key_id,
            access_key_secret=key_secret,
            region_id=settings.ALIYUN_EMAIL_REGION,
        )
        cls._client = Client(config)
        return cls._client

    @classmethod
    async def send_verification_code(cls, to_address: str, code: str) -> bool:
        """发送邮箱验证码"""
        return await cls._send_email(
            to_address=to_address,
            subject="安心智能助手 - 邮箱验证码",
            html_body=VERIFY_EMAIL_TEMPLATE.format(
                title="邮箱验证",
                code=code,
            ),
        )

    @classmethod
    async def send_reset_code(cls, to_address: str, code: str) -> bool:
        """发送密码重置验证码"""
        return await cls._send_email(
            to_address=to_address,
            subject="安心智能助手 - 密码重置验证码",
            html_body=VERIFY_EMAIL_TEMPLATE.format(
                title="密码重置",
                code=code,
            ),
        )

    @classmethod
    async def _send_email(
        cls,
        to_address: str,
        subject: str,
        html_body: str,
    ) -> bool:
        """发送单封邮件"""
        client = cls._get_client()
        if not client:
            logger.warning(f"邮件服务不可用，邮件 -> {to_address} (仅日志)")
            return False

        try:
            from alibabacloud_dm20151123.models import SingleSendMailRequest

            request = SingleSendMailRequest(
                account_name=settings.ALIYUN_EMAIL_ACCOUNT,
                address_type=1,
                reply_to_address=False,
                to_address=to_address,
                subject=subject,
                html_body=html_body,
                from_alias=settings.ALIYUN_EMAIL_ALIAS,
            )

            client.single_send_mail(request)
            logger.info(f"邮件发送成功: to={to_address}, subject={subject}")
            return True

        except Exception as e:
            logger.error(f"邮件发送失败: to={to_address}, error={e}")
            return False

    @classmethod
    def is_available(cls) -> bool:
        """检查邮件服务是否可用"""
        return bool(
            settings.ALIYUN_ACCESS_KEY_ID
            and settings.ALIYUN_ACCESS_KEY_SECRET
            and settings.ALIYUN_EMAIL_ACCOUNT
        )


# 模块级单例
email_service = EmailService()
