"""

??????

"""



from datetime import datetime

from typing import Optional, TYPE_CHECKING

from sqlalchemy import String, Text, ForeignKey, DateTime, Enum as SQLEnum

from sqlalchemy import JSON as JSONB

from sqlalchemy.orm import Mapped, mapped_column, relationship

import enum



from src.models.base import Base, TimestampMixin, GUID



if TYPE_CHECKING:

    from src.models.user import User, Organization

    from src.models.document import Document





class CaseStatus(str, enum.Enum):

    """????"""

    PENDING = "pending"

    IN_PROGRESS = "in_progress"

    UNDER_REVIEW = "under_review"

    COMPLETED = "completed"

    CLOSED = "closed"

    CANCELLED = "cancelled"





class CasePriority(str, enum.Enum):

    """?????"""

    LOW = "low"

    MEDIUM = "medium"

    HIGH = "high"

    URGENT = "urgent"





class CaseType(str, enum.Enum):

    """????"""

    CONTRACT = "contract"  # ????

    LABOR = "labor"  # ????

    INTELLECTUAL_PROPERTY = "ip"  # ????

    CORPORATE = "corporate"  # ????

    LITIGATION = "litigation"  # ????

    COMPLIANCE = "compliance"  # ????

    DUE_DILIGENCE = "due_diligence"  # ????

    OTHER = "other"  # ??





class Case(Base, TimestampMixin):

    """????"""

    

    __tablename__ = "cases"

    

    title: Mapped[str] = mapped_column(String(255), nullable=False)

    case_number: Mapped[Optional[str]] = mapped_column(String(50), unique=True)

    case_type: Mapped[CaseType] = mapped_column(

        SQLEnum(CaseType), default=CaseType.OTHER

    )

    status: Mapped[CaseStatus] = mapped_column(

        SQLEnum(CaseStatus), default=CaseStatus.PENDING

    )

    priority: Mapped[CasePriority] = mapped_column(

        SQLEnum(CasePriority), default=CasePriority.MEDIUM

    )

    description: Mapped[Optional[str]] = mapped_column(Text)

    

    # ?????

    parties: Mapped[Optional[dict]] = mapped_column(JSONB)  # ?????

    

    # AI????

    ai_analysis: Mapped[Optional[dict]] = mapped_column(JSONB)

    risk_score: Mapped[Optional[float]] = mapped_column()

    

    # ????

    deadline: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    

    # ??

    org_id: Mapped[Optional[str]] = mapped_column(

        GUID(), ForeignKey("organizations.id", ondelete="CASCADE")

    )

    created_by: Mapped[Optional[str]] = mapped_column(

        GUID(), ForeignKey("users.id", ondelete="SET NULL")

    )

    assignee_id: Mapped[Optional[str]] = mapped_column(

        GUID(), ForeignKey("users.id", ondelete="SET NULL")

    )

    

    # ??

    organization: Mapped[Optional["Organization"]] = relationship(

        "Organization", back_populates="cases"

    )

    creator: Mapped[Optional["User"]] = relationship(

        "User", back_populates="created_cases", foreign_keys=[created_by]

    )

    assignee: Mapped[Optional["User"]] = relationship(

        "User", back_populates="assigned_cases", foreign_keys=[assignee_id]

    )

    events: Mapped[list["CaseEvent"]] = relationship(

        "CaseEvent", back_populates="case", cascade="all, delete-orphan"

    )

    documents: Mapped[list["Document"]] = relationship(

        "Document", back_populates="case"

    )





class CaseEvent(Base, TimestampMixin):

    """????/???"""

    

    __tablename__ = "case_events"

    

    event_type: Mapped[str] = mapped_column(String(50), nullable=False)

    title: Mapped[str] = mapped_column(String(255), nullable=False)

    description: Mapped[Optional[str]] = mapped_column(Text)

    event_data: Mapped[Optional[dict]] = mapped_column(JSONB)

    event_time: Mapped[datetime] = mapped_column(

        DateTime(timezone=True), nullable=False

    )

    

    # ??

    case_id: Mapped[str] = mapped_column(

        GUID(), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False

    )

    created_by: Mapped[Optional[str]] = mapped_column(

        GUID(), ForeignKey("users.id", ondelete="SET NULL")

    )

    

    # ??

    case: Mapped["Case"] = relationship("Case", back_populates="events")

