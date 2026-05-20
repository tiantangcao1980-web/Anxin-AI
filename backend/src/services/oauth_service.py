"""第三方 OAuth 登录服务"""

from typing import Any, cast

import httpx
from loguru import logger

from src.core.config import settings

JsonObject = dict[str, Any]


def _response_json(resp: httpx.Response) -> JsonObject:
    data = resp.json()
    return data if isinstance(data, dict) else {}


class WeChatOAuth:
    """微信开放平台 OAuth 2.0
    文档: https://developers.weixin.qq.com/doc/oplatform/Website_App/WeChat_Login/Wechat_Login.html
    """

    AUTHORIZE_URL = "https://open.weixin.qq.com/connect/qrconnect"
    ACCESS_TOKEN_URL = "https://api.weixin.qq.com/sns/oauth2/access_token"
    USERINFO_URL = "https://api.weixin.qq.com/sns/userinfo"

    @staticmethod
    def get_authorize_url(state: str) -> str:
        """生成微信授权链接"""
        params = {
            "appid": settings.WECHAT_APP_ID,
            "redirect_uri": settings.WECHAT_REDIRECT_URI,
            "response_type": "code",
            "scope": "snsapi_login",
            "state": state,
        }
        query = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{WeChatOAuth.AUTHORIZE_URL}?{query}#wechat_redirect"

    @staticmethod
    async def get_access_token(code: str) -> JsonObject:
        """用 code 换取 access_token"""
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                WeChatOAuth.ACCESS_TOKEN_URL,
                params={
                    "appid": settings.WECHAT_APP_ID,
                    "secret": settings.WECHAT_APP_SECRET,
                    "code": code,
                    "grant_type": "authorization_code",
                },
            )
            data = _response_json(resp)
            if "errcode" in data:
                logger.error(f"微信 access_token 获取失败: {data}")
                raise ValueError(f"微信授权失败: {data.get('errmsg', '未知错误')}")
            return data  # {access_token, openid, unionid, ...}

    @staticmethod
    async def get_user_info(access_token: str, openid: str) -> JsonObject:
        """获取微信用户信息"""
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                WeChatOAuth.USERINFO_URL,
                params={
                    "access_token": access_token,
                    "openid": openid,
                },
            )
            data = _response_json(resp)
            if "errcode" in data:
                logger.error(f"微信用户信息获取失败: {data}")
                raise ValueError(f"获取用户信息失败: {data.get('errmsg')}")
            return data  # {openid, nickname, headimgurl, unionid, ...}


class WeChatMiniProgramOAuth:
    """微信小程序登录 code2Session.

    服务端用 wx.login 返回的 code 换取 openid/session_key；session_key
    不下发给小程序端，只用于服务端建立本地会话。
    """

    CODE2SESSION_URL = "https://api.weixin.qq.com/sns/jscode2session"

    @staticmethod
    async def code2session(code: str) -> JsonObject:
        app_id = settings.WECHAT_MINI_APP_ID or settings.WECHAT_APP_ID
        app_secret = settings.WECHAT_MINI_APP_SECRET or settings.WECHAT_APP_SECRET
        if not app_id or not app_secret:
            raise ValueError("微信小程序登录未配置")

        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                WeChatMiniProgramOAuth.CODE2SESSION_URL,
                params={
                    "appid": app_id,
                    "secret": app_secret,
                    "js_code": code,
                    "grant_type": "authorization_code",
                },
            )
            data = _response_json(resp)
            if data.get("errcode"):
                logger.error(f"微信小程序 code2session 失败: {data}")
                raise ValueError(f"微信小程序登录失败: {data.get('errmsg', '未知错误')}")
            if not data.get("openid"):
                logger.error(f"微信小程序 code2session 响应缺少 openid: {data}")
                raise ValueError("微信小程序登录失败: 缺少 openid")
            return data  # {openid, session_key, unionid, ...}


class AlipayOAuth:
    """支付宝 OAuth 2.0
    文档: https://opendocs.alipay.com/open/01emu5
    """

    AUTHORIZE_URL = "https://openauth.alipay.com/oauth2/publicAppAuthorize.htm"
    GATEWAY_URL = "https://openapi.alipay.com/gateway.do"

    @staticmethod
    def get_authorize_url(state: str) -> str:
        """生成支付宝授权链接"""
        params = {
            "app_id": settings.ALIPAY_APP_ID,
            "scope": "auth_user",
            "redirect_uri": settings.ALIPAY_REDIRECT_URI,
            "state": state,
        }
        query = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{AlipayOAuth.AUTHORIZE_URL}?{query}"

    @staticmethod
    async def get_access_token(auth_code: str) -> JsonObject:
        """用授权码换取 access_token
        注: 生产环境需使用 RSA2 签名，这里预留接口结构
        """
        # 实际生产中需要使用 alipay-sdk-python 或手动实现 RSA2 签名
        # 这里提供接口框架，后续接入时替换
        logger.info(f"支付宝 OAuth: 收到授权码 auth_code={auth_code[:8]}...")

        async with httpx.AsyncClient(timeout=10) as client:
            # 构建请求参数 (简化版，生产需加签名)
            resp = await client.post(
                AlipayOAuth.GATEWAY_URL,
                data={
                    "app_id": settings.ALIPAY_APP_ID,
                    "method": "alipay.system.oauth.token",
                    "grant_type": "authorization_code",
                    "code": auth_code,
                    "charset": "utf-8",
                    "sign_type": "RSA2",
                    # sign: 需要 RSA2 签名
                },
            )
            data = _response_json(resp)
            if "error_response" in data:
                raise ValueError(
                    f"支付宝授权失败: {data['error_response'].get('sub_msg', '未知错误')}"
                )
            token_resp = data.get("alipay_system_oauth_token_response", {})
            return cast(JsonObject, token_resp if isinstance(token_resp, dict) else {})

    @staticmethod
    async def get_user_info(access_token: str) -> JsonObject:
        """获取支付宝用户信息"""
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                AlipayOAuth.GATEWAY_URL,
                data={
                    "app_id": settings.ALIPAY_APP_ID,
                    "method": "alipay.user.info.share",
                    "auth_token": access_token,
                    "charset": "utf-8",
                    "sign_type": "RSA2",
                },
            )
            data = _response_json(resp)
            raw_user_resp = data.get("alipay_user_info_share_response", {})
            user_resp = raw_user_resp if isinstance(raw_user_resp, dict) else {}
            if user_resp.get("code") != "10000":
                raise ValueError(f"获取支付宝用户信息失败: {user_resp.get('sub_msg')}")
            return cast(JsonObject, user_resp)  # {user_id, nick_name, avatar, ...}
