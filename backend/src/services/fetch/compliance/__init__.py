"""合规与审计子模块（白名单 / 黑名单 / 审计日志）。"""

from src.services.fetch.compliance.allowlist import (
    ALLOWED_DOMAINS,
    is_allowed,
)
from src.services.fetch.compliance.audit import AuditLogger, AuditRecord
from src.services.fetch.compliance.blocklist import (
    BLOCKED_DOMAINS,
    BLOCKED_PATH_PATTERNS,
    BlockReason,
    is_blocked,
)

__all__ = [
    "ALLOWED_DOMAINS",
    "BLOCKED_DOMAINS",
    "BLOCKED_PATH_PATTERNS",
    "BlockReason",
    "is_allowed",
    "is_blocked",
    "AuditLogger",
    "AuditRecord",
]
