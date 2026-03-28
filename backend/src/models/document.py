"""
ææ¡£ç®¡çæ¨¡å
"""

from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Text, ForeignKey, Integer, BigInteger, Enum as SQLEnum
from sqlalchemy import JSON as JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from src.models.base import Base, TimestampMixin, GUID

if TYPE_CHECKING:
    from src.models.user import User
    from src.models.case import Case
    from src.models.collaboration import DocumentSession


class DocumentType(str, enum.Enum):
    """ææ¡£ç±»å"""
    CONTRACT = "contract"  # åå
    AGREEMENT = "agreement"  # åè®®
    LEGAL_OPINION = "legal_opinion"  # æ³å¾æè§ä¹?
    LAWSUIT = "lawsuit"  # è¯ç¶
    EVIDENCE = "evidence"  # è¯æ®ææ
    REPORT = "report"  # æ¥å
    TEMPLATE = "template"  # æ¨¡æ¿
    OTHER = "other"  # å¶ä»


class Document(Base, TimestampMixin):
    """ææ¡£æ¨¡å"""
    
    __tablename__ = "documents"
    
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    doc_type: Mapped[DocumentType] = mapped_column(
        SQLEnum(DocumentType), default=DocumentType.OTHER
    )
    description: Mapped[Optional[str]] = mapped_column(Text)
    
    # æä»¶ä¿¡æ¯
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, default=0)
    mime_type: Mapped[Optional[str]] = mapped_column(String(100))
    file_hash: Mapped[Optional[str]] = mapped_column(String(64))
    
    # çæ¬æ§å¶
    version: Mapped[int] = mapped_column(Integer, default=1)
    is_latest: Mapped[bool] = mapped_column(default=True)
    
    # AIå¤çç»æ
    ai_summary: Mapped[Optional[str]] = mapped_column(Text)
    ai_analysis: Mapped[Optional[dict]] = mapped_column(JSONB)
    extracted_text: Mapped[Optional[str]] = mapped_column(Text)
    
    # æ ç­¾ååæ°æ®
    tags: Mapped[Optional[list]] = mapped_column(JSONB)
    doc_metadata: Mapped[Optional[dict]] = mapped_column(JSONB)
    
    # å¤é®
    org_id: Mapped[Optional[str]] = mapped_column(
        GUID(), ForeignKey("organizations.id", ondelete="CASCADE")
    )
    case_id: Mapped[Optional[str]] = mapped_column(
        GUID(), ForeignKey("cases.id", ondelete="SET NULL")
    )
    created_by: Mapped[Optional[str]] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL")
    )
    
    # å³ç³»
    case: Mapped[Optional["Case"]] = relationship("Case", back_populates="documents")
    created_by_user: Mapped[Optional["User"]] = relationship(
        "User", back_populates="documents"
    )
    versions: Mapped[list["DocumentVersion"]] = relationship(
        "DocumentVersion", back_populates="document", cascade="all, delete-orphan"
    )
    sessions: Mapped[list["DocumentSession"]] = relationship(
        "DocumentSession", back_populates="document", cascade="all, delete-orphan"
    )


class DocumentVersion(Base, TimestampMixin):
    """ææ¡£çæ¬åå²"""
    
    __tablename__ = "document_versions"
    
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, default=0)
    file_hash: Mapped[Optional[str]] = mapped_column(String(64))
    change_summary: Mapped[Optional[str]] = mapped_column(Text)
    
    # å¤é®
    document_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    created_by: Mapped[Optional[str]] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL")
    )
    
    # å³ç³»
    document: Mapped["Document"] = relationship("Document", back_populates="versions")
