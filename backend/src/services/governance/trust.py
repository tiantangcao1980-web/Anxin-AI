# -*- coding: utf-8 -*-
"""
Trust —— skill / cookbook / connector 来源信任评估

约定见 docs/governance/TRUST-LEVELS.md，规则源 policy/trust-levels.yaml。
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

from loguru import logger

from src.services.governance.policy_loader import get_policy

REPO_ROOT = Path(__file__).resolve().parents[4]
REVOKED_FILE = REPO_ROOT / ".claude" / "builder-hub" / "revoked.json"


class TrustLevel(str, Enum):
    VERIFIED = "verified"
    COMMUNITY = "community"
    UNTRUSTED = "untrusted"
    REVOKED = "revoked"


@dataclass(frozen=True)
class TrustEvaluation:
    level: TrustLevel
    reasons: list[str]
    require_confirm_on_call: bool
    network_egress: str          # allow / allowlist / deny
    connector_write: str         # allow / confirm / deny


def _load_revoked() -> set[tuple[str, str]]:
    """返回 (skill_id, version) 集合。"""
    if not REVOKED_FILE.exists():
        return set()
    try:
        items = json.loads(REVOKED_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        logger.warning("revoked.json 解析失败")
        return set()
    return {(e.get("skill_id"), e.get("version")) for e in items if isinstance(e, dict)}


def evaluate_trust(
    *,
    skill_id: str,
    version: str,
    source_url: str | None = None,
    declared_level: str | None = None,
) -> TrustEvaluation:
    policy = get_policy().trust_levels
    reasons: list[str] = []

    # 1. 撤回检查
    if (skill_id, version) in _load_revoked():
        return TrustEvaluation(
            level=TrustLevel.REVOKED,
            reasons=[f"{skill_id}@{version} 在 revoked.json"],
            require_confirm_on_call=False,
            network_egress="deny",
            connector_write="deny",
        )

    # 2. 来源 → 默认级别
    registries = policy.get("registries", {}) or {}
    source_level = None
    for reg_name, cfg in registries.items():
        url = cfg.get("url", "")
        if source_url and source_url.startswith(url):
            source_level = cfg.get("default_level")
            reasons.append(f"source matched registry={reg_name} default={source_level}")
            break

    level_str = declared_level or source_level or "untrusted"
    if level_str not in policy.get("levels", {}):
        level_str = "untrusted"
        reasons.append("declared level not recognized → fallback untrusted")
    level_cfg = policy["levels"][level_str]

    reasons.append(f"final level={level_str}")
    return TrustEvaluation(
        level=TrustLevel(level_str),
        reasons=reasons,
        require_confirm_on_call=bool(level_cfg.get("confirm_on_call")),
        network_egress=level_cfg.get("network_egress", "deny"),
        connector_write=level_cfg.get("connector_write", "deny"),
    )


def write_revoked(skill_id: str, version: str, reason: str, revoked_by: str) -> None:
    REVOKED_FILE.parent.mkdir(parents=True, exist_ok=True)
    items: list[dict] = []
    if REVOKED_FILE.exists():
        try:
            items = json.loads(REVOKED_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            items = []
    items.append({
        "skill_id": skill_id,
        "version": version,
        "reason": reason,
        "revoked_by": revoked_by,
        "revoked_at": datetime.now(timezone.utc).isoformat(),
    })
    REVOKED_FILE.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.warning("Skill revoked: {}@{} reason={}", skill_id, version, reason)


__all__ = ["TrustLevel", "TrustEvaluation", "evaluate_trust", "write_revoked"]
