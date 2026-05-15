"""
用户服务
"""

from typing import Any

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.security import (
    create_access_token,
    create_refresh_token,
    get_password_hash,
    verify_password,
)
from src.models.user import Organization, User


class UserService:
    """用户服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_user(
        self,
        email: str,
        password: str,
        name: str,
        org_id: str | None = None,
        role: str = "member",
        user_type: str = "individual",
        phone: str | None = None,
    ) -> User:
        """创建用户"""
        # 检查邮箱是否已存在
        existing = await self.get_user_by_email(email)
        if existing:
            raise ValueError("邮箱已被注册")

        # V2 架构：根据 user_type 自动推断 primary_client
        # 律师/律所 → 服务方端；个人/企业 → 需求方端
        primary_client = "provider" if user_type in ("platform_lawyer", "institution") else "needer"

        user = User(
            email=email,
            hashed_password=get_password_hash(password),
            name=name,
            org_id=org_id,
            role=role,
            user_type=user_type,
            primary_client=primary_client,
            is_active=True,
        )

        self.db.add(user)
        await self.db.flush()

        logger.info(
            f"用户创建成功: {email}, type={user_type}, role={role}, client={primary_client}"
        )
        return user

    async def get_user(self, user_id: str) -> User | None:
        """获取用户"""
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_user_by_email(self, email: str) -> User | None:
        """根据邮箱获取用户"""
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def authenticate(self, email: str, password: str) -> User | None:
        """用户认证"""
        user = await self.get_user_by_email(email)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        if not user.is_active:
            return None
        return user

    async def login(self, email: str, password: str) -> dict[str, Any] | None:
        """用户登录"""
        user = await self.authenticate(email, password)
        if not user:
            return None

        access_token = create_access_token(user.id)
        refresh_token = create_refresh_token(user.id)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "role": user.role,
                "email_verified": user.email_verified,
            },
        }

    async def update_user(
        self,
        user_id: str,
        name: str | None = None,
        avatar_url: str | None = None,
    ) -> User | None:
        """更新用户信息"""
        user = await self.get_user(user_id)
        if not user:
            return None

        if name:
            user.name = name
        if avatar_url is not None:
            user.avatar_url = avatar_url

        await self.db.flush()
        return user

    async def change_password(
        self,
        user_id: str,
        old_password: str,
        new_password: str,
    ) -> bool:
        """修改密码"""
        user = await self.get_user(user_id)
        if not user:
            return False

        if not verify_password(old_password, user.hashed_password):
            return False

        user.hashed_password = get_password_hash(new_password)
        await self.db.flush()

        return True

    # OAuth 第三方登录查找方法
    async def get_by_wechat_openid(self, openid: str) -> User | None:
        """根据微信 openid 查找用户"""
        result = await self.db.execute(select(User).where(User.wechat_openid == openid))
        return result.scalar_one_or_none()

    async def get_by_alipay_uid(self, uid: str) -> User | None:
        """根据支付宝 user_id 查找用户"""
        result = await self.db.execute(select(User).where(User.alipay_user_id == uid))
        return result.scalar_one_or_none()

    # 组织相关
    async def create_organization(
        self,
        name: str,
        description: str | None = None,
    ) -> Organization:
        """创建组织"""
        org = Organization(
            name=name,
            description=description,
            is_active=True,
        )

        self.db.add(org)
        await self.db.flush()

        logger.info(f"组织创建成功: {name}")
        return org

    async def get_organization(self, org_id: str) -> Organization | None:
        """获取组织"""
        result = await self.db.execute(select(Organization).where(Organization.id == org_id))
        return result.scalar_one_or_none()

    async def list_org_users(self, org_id: str) -> list[User]:
        """获取组织成员"""
        result = await self.db.execute(
            select(User).where(User.org_id == org_id, User.is_active == True)
        )
        return list(result.scalars().all())
