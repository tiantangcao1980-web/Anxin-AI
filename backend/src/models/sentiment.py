"""

èæçæ§æ°æ®æ¨¡å

"""



from datetime import datetime

from typing import Optional, List, TYPE_CHECKING

from sqlalchemy import String, Text, ForeignKey, DateTime, Float, Boolean, Enum as SQLEnum, Integer

from sqlalchemy import JSON as JSONB, JSON as ARRAY

from sqlalchemy.orm import Mapped, mapped_column, relationship

import enum



from src.models.base import Base, TimestampMixin, GUID



if TYPE_CHECKING:

    from src.models.user import User, Organization





class SentimentType(str, enum.Enum):

    """ææç±»å"""

    POSITIVE = "positive"      # æ­£é¢

    NEGATIVE = "negative"      # è´é¢

    NEUTRAL = "neutral"        # ä¸­æ?





class RiskLevel(str, enum.Enum):

    """é£é©ç­çº§"""

    LOW = "low"                # ä½é£é?

    MEDIUM = "medium"          # ä¸­é£é?

    HIGH = "high"              # é«é£é?

    CRITICAL = "critical"      # æé«é£é©





class AlertLevel(str, enum.Enum):

    """é¢è­¦ç­çº§"""

    INFO = "info"              # æç¤º

    WARNING = "warning"        # è­¦å

    DANGER = "danger"          # å±é©

    CRITICAL = "critical"      # ç´§æ?





class AlertType(str, enum.Enum):

    """é¢è­¦ç±»å"""

    NEGATIVE_SURGE = "negative_surge"        # è´é¢èææ¿å¢?

    HIGH_RISK = "high_risk"                  # é«é£é©èæ?

    KEYWORD_MATCH = "keyword_match"          # å³é®è¯å¹é?

    TREND_ANOMALY = "trend_anomaly"          # è¶å¿å¼å¸¸

    REPUTATION_RISK = "reputation_risk"      # å£°èªé£é©





class SourceType(str, enum.Enum):

    """æ°æ®æ¥æºç±»å"""

    NEWS = "news"              # æ°é»

    SOCIAL_MEDIA = "social_media"  # ç¤¾äº¤åªä½

    FORUM = "forum"            # è®ºå

    BLOG = "blog"              # åå®¢

    OFFICIAL = "official"      # å®æ¹ç½ç«

    OTHER = "other"            # å¶ä»





class SentimentRecord(Base, TimestampMixin):

    """èæè®°å½æ¨¡å"""

    

    __tablename__ = "sentiment_records"

    

    # åºæ¬ä¿¡æ¯

    title: Mapped[Optional[str]] = mapped_column(String(500))

    content: Mapped[str] = mapped_column(Text, nullable=False)

    keyword: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    source: Mapped[Optional[str]] = mapped_column(String(255))  # æ¥æºURLæåç§?

    source_type: Mapped[SourceType] = mapped_column(

        SQLEnum(SourceType), default=SourceType.OTHER

    )

    

    # ææåæç»æ

    sentiment_type: Mapped[SentimentType] = mapped_column(

        SQLEnum(SentimentType), default=SentimentType.NEUTRAL

    )

    sentiment_score: Mapped[float] = mapped_column(Float, default=0.0)  # -1.0 å?1.0

    

    # é£é©è¯ä¼°

    risk_level: Mapped[RiskLevel] = mapped_column(

        SQLEnum(RiskLevel), default=RiskLevel.LOW

    )

    risk_score: Mapped[float] = mapped_column(Float, default=0.0)  # 0 å?1.0

    risk_factors: Mapped[Optional[dict]] = mapped_column(JSONB)  # é£é©å ç´ è¯¦æ

    

    # AIåæç»æ

    ai_analysis: Mapped[Optional[dict]] = mapped_column(JSONB)  # AIåæè¯¦æ

    summary: Mapped[Optional[str]] = mapped_column(Text)  # AIçææè¦

    

    # åæ°æ?

    publish_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    author: Mapped[Optional[str]] = mapped_column(String(100))

    engagement: Mapped[Optional[dict]] = mapped_column(JSONB)  # äºå¨æ°æ®ï¼ç¹èµãè¯è®ºãè½¬åç­

    

    # å¤é®

    org_id: Mapped[Optional[str]] = mapped_column(

        GUID(), ForeignKey("organizations.id", ondelete="CASCADE")

    )

    monitor_id: Mapped[Optional[str]] = mapped_column(

        GUID(), ForeignKey("sentiment_monitors.id", ondelete="SET NULL")

    )

    

    # å³ç³»

    organization: Mapped[Optional["Organization"]] = relationship(

        "Organization", back_populates="sentiment_records"

    )

    monitor: Mapped[Optional["SentimentMonitor"]] = relationship(

        "SentimentMonitor", back_populates="records"

    )





class SentimentAlert(Base, TimestampMixin):

    """èæé¢è­¦æ¨¡å"""

    

    __tablename__ = "sentiment_alerts"

    

    # é¢è­¦ä¿¡æ¯

    alert_type: Mapped[AlertType] = mapped_column(

        SQLEnum(AlertType), nullable=False

    )

    alert_level: Mapped[AlertLevel] = mapped_column(

        SQLEnum(AlertLevel), default=AlertLevel.INFO

    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)

    message: Mapped[str] = mapped_column(Text, nullable=False)

    

    # ç¶æ?

    is_read: Mapped[bool] = mapped_column(Boolean, default=False)

    is_handled: Mapped[bool] = mapped_column(Boolean, default=False)

    handled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    handled_by: Mapped[Optional[str]] = mapped_column(

        GUID(), ForeignKey("users.id", ondelete="SET NULL")

    )

    handle_note: Mapped[Optional[str]] = mapped_column(Text)

    

    # å³èæ°æ®

    related_records: Mapped[Optional[list]] = mapped_column(JSONB)  # ç¸å³èæè®°å½IDåè¡¨

    statistics: Mapped[Optional[dict]] = mapped_column(JSONB)  # ç»è®¡æ°æ®

    

    # å¤é®

    org_id: Mapped[Optional[str]] = mapped_column(

        GUID(), ForeignKey("organizations.id", ondelete="CASCADE")

    )

    monitor_id: Mapped[Optional[str]] = mapped_column(

        GUID(), ForeignKey("sentiment_monitors.id", ondelete="SET NULL")

    )

    

    # å³ç³»

    organization: Mapped[Optional["Organization"]] = relationship(

        "Organization", back_populates="sentiment_alerts"

    )

    monitor: Mapped[Optional["SentimentMonitor"]] = relationship(

        "SentimentMonitor", back_populates="alerts"

    )

    handler: Mapped[Optional["User"]] = relationship("User")





class SentimentMonitor(Base, TimestampMixin):

    """çæ§éç½®æ¨¡å"""

    

    __tablename__ = "sentiment_monitors"

    

    # åºæ¬ä¿¡æ¯

    name: Mapped[str] = mapped_column(String(100), nullable=False)

    description: Mapped[Optional[str]] = mapped_column(Text)

    

    # çæ§éç½®

    keywords: Mapped[list] = mapped_column(JSONB, nullable=False)  # çæ§å³é®è¯åè¡?

    sources: Mapped[Optional[list]] = mapped_column(JSONB)  # çæ§æ¥æºåè¡¨

    exclude_keywords: Mapped[Optional[list]] = mapped_column(JSONB)  # æé¤å³é®è¯?

    

    # é¢è­¦éå?

    alert_threshold: Mapped[float] = mapped_column(Float, default=0.7)  # é¢è­¦éå?

    negative_threshold: Mapped[float] = mapped_column(Float, default=0.6)  # è´é¢éå?

    risk_threshold: Mapped[float] = mapped_column(Float, default=0.8)  # é£é©éå?

    

    # çæ§ç¶æ?

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    last_scan_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    scan_interval: Mapped[int] = mapped_column(Integer, default=3600)  # æ«æé´éï¼ç§ï¼?

    

    # ç»è®¡

    total_records: Mapped[int] = mapped_column(Integer, default=0)

    negative_count: Mapped[int] = mapped_column(Integer, default=0)

    alert_count: Mapped[int] = mapped_column(Integer, default=0)

    

    # å¤é®

    org_id: Mapped[Optional[str]] = mapped_column(

        GUID(), ForeignKey("organizations.id", ondelete="CASCADE")

    )

    created_by: Mapped[Optional[str]] = mapped_column(

        GUID(), ForeignKey("users.id", ondelete="SET NULL")

    )

    

    # å³ç³»

    organization: Mapped[Optional["Organization"]] = relationship(

        "Organization", back_populates="sentiment_monitors"

    )

    creator: Mapped[Optional["User"]] = relationship("User")

    records: Mapped[list["SentimentRecord"]] = relationship(

        "SentimentRecord", back_populates="monitor"

    )

    alerts: Mapped[list["SentimentAlert"]] = relationship(

        "SentimentAlert", back_populates="monitor"

    )

