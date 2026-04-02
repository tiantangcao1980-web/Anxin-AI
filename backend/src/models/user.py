"""
用户与组织模型
"""



from datetime import datetime
from typing import Optional, TYPE_CHECKING

from sqlalchemy import String, ForeignKey, Boolean, DateTime, Integer
from sqlalchemy import JSON as JSONB

from sqlalchemy.orm import Mapped, mapped_column, relationship



from src.models.base import Base, TimestampMixin, GUID



if TYPE_CHECKING:

    from src.models.case import Case

    from src.models.document import Document

    from src.models.sentiment import SentimentRecord, SentimentAlert, SentimentMonitor





class Organization(Base, TimestampMixin):

    """组织/律所模型"""

    

    __tablename__ = "organizations"

    

    name: Mapped[str] = mapped_column(String(255), nullable=False)

    description: Mapped[Optional[str]] = mapped_column(String(1000))

    logo_url: Mapped[Optional[str]] = mapped_column(String(500))

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    

    # 关系

    users: Mapped[list["User"]] = relationship("User", back_populates="organization")

    cases: Mapped[list["Case"]] = relationship("Case", back_populates="organization")

    # 舆情关系

    sentiment_records: Mapped[list["SentimentRecord"]] = relationship(

        "SentimentRecord", back_populates="organization"

    )

    sentiment_alerts: Mapped[list["SentimentAlert"]] = relationship(

        "SentimentAlert", back_populates="organization"

    )

    sentiment_monitors: Mapped[list["SentimentMonitor"]] = relationship(

        "SentimentMonitor", back_populates="organization"

    )





class User(Base, TimestampMixin):

    """用户模型"""

    

    __tablename__ = "users"

    

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)

    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)

    name: Mapped[str] = mapped_column(String(100), nullable=False)

    avatar_url: Mapped[Optional[str]] = mapped_column(String(500))

    role: Mapped[str] = mapped_column(String(50), default="member")  # 见 UserRole 枚举

    # 部门（用于数据范围控制）
    department: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # 用户类型标识
    user_type: Mapped[str] = mapped_column(String(30), default="internal")  # internal / platform_lawyer / enterprise / individual

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)

    # 安全字段
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    login_attempts: Mapped[int] = mapped_column(Integer, default=0)
    password_changed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # OAuth 第三方登录绑定
    wechat_openid: Mapped[Optional[str]] = mapped_column(String(100), unique=True, nullable=True, index=True)
    wechat_unionid: Mapped[Optional[str]] = mapped_column(String(100), unique=True, nullable=True, index=True)
    alipay_user_id: Mapped[Optional[str]] = mapped_column(String(100), unique=True, nullable=True, index=True)
    login_type: Mapped[str] = mapped_column(String(20), default="email")  # email / wechat / alipay

    # AI 用户画像（法律专业度、常用场景、追问耐心度、默认上下文等）
    ai_profile: Mapped[Optional[dict]] = mapped_column(JSONB, default=dict)

    # 外键

    org_id: Mapped[Optional[str]] = mapped_column(
        GUID(),
        ForeignKey("organizations.id", ondelete="SET NULL")
    )

    

    # 关系

    organization: Mapped[Optional["Organization"]] = relationship(

        "Organization", back_populates="users"

    )

    created_cases: Mapped[list["Case"]] = relationship(

        "Case", back_populates="creator", foreign_keys="Case.created_by"

    )

    assigned_cases: Mapped[list["Case"]] = relationship(

        "Case", back_populates="assignee", foreign_keys="Case.assignee_id"

    )

    documents: Mapped[list["Document"]] = relationship(

        "Document", back_populates="created_by_user"

    )

