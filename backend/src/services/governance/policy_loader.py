# -*- coding: utf-8 -*-
"""
PolicyLoader —— 加载 + 校验 + 热重载 policy/*.yaml

设计：
- **单例**：进程内一份，避免反复读盘；SIGHUP / API reload 触发 reload。
- **快照**：每次 reload 计算 `policy_snapshot_id`（全部 yaml 的 git tree hash），
  写入 .claude/policy-snapshots/<id>/，审计日志带这个 id。
- **校验**：reload 时跑一遍 schema 校验；失败保留旧版，不让无效 policy 上线。

约定：
- policy/*.yaml 是单一真相源
- 后端任何地方需要 policy → `get_policy()` 拿单例 `PolicyBundle`
- 修改 policy → 通过 `reload_policy()` 触发重载
"""
from __future__ import annotations

import hashlib
import json
import threading
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import yaml
from loguru import logger

REPO_ROOT = Path(__file__).resolve().parents[4]
POLICY_DIR = REPO_ROOT / "policy"
SNAPSHOT_DIR = REPO_ROOT / ".claude" / "policy-snapshots"

POLICY_FILES = [
    "access-matrix.yaml",
    "trust-levels.yaml",
    "data-classification.yaml",
    "jurisdiction-rules.yaml",
    "tool-allowlist.yaml",
    "pii-redaction.yaml",
    "skill-lifecycle.yaml",
]


@dataclass(frozen=True)
class PolicyBundle:
    """所有 policy yaml 加载后的不可变快照。"""

    snapshot_id: str
    loaded_at: datetime
    access_matrix: dict
    trust_levels: dict
    data_classification: dict
    jurisdiction_rules: dict
    tool_allowlist: dict
    pii_redaction: dict
    skill_lifecycle: dict
    raw: dict = field(default_factory=dict)

    @classmethod
    def from_dir(cls, policy_dir: Path = POLICY_DIR) -> PolicyBundle:
        raw: dict[str, dict] = {}
        for fn in POLICY_FILES:
            p = policy_dir / fn
            if not p.exists():
                raise FileNotFoundError(f"policy 文件缺失：{p}")
            raw[fn] = yaml.safe_load(p.read_text(encoding="utf-8"))
        snapshot_id = cls._snapshot_id(raw)
        cls._validate(raw)
        return cls(
            snapshot_id=snapshot_id,
            loaded_at=datetime.now(UTC),
            access_matrix=raw["access-matrix.yaml"],
            trust_levels=raw["trust-levels.yaml"],
            data_classification=raw["data-classification.yaml"],
            jurisdiction_rules=raw["jurisdiction-rules.yaml"],
            tool_allowlist=raw["tool-allowlist.yaml"],
            pii_redaction=raw["pii-redaction.yaml"],
            skill_lifecycle=raw["skill-lifecycle.yaml"],
            raw=raw,
        )

    @staticmethod
    def _snapshot_id(raw: dict) -> str:
        canonical = json.dumps(raw, sort_keys=True, ensure_ascii=False).encode("utf-8")
        return "pol_" + hashlib.sha256(canonical).hexdigest()[:24]

    @staticmethod
    def _validate(raw: dict) -> None:
        """轻量 schema 校验 — 强制每份 yaml 都声明 schema_version + 关键 section。"""
        required_top_keys: dict[str, list[str]] = {
            "access-matrix.yaml": ["schema_version", "default_decision", "roles"],
            "trust-levels.yaml": ["schema_version", "levels", "registries"],
            "data-classification.yaml": ["schema_version", "levels", "clearance_by_role"],
            "jurisdiction-rules.yaml": ["schema_version", "jurisdictions", "cross_border"],
            "tool-allowlist.yaml": ["schema_version", "tool_categories", "persona_defaults"],
            "pii-redaction.yaml": ["schema_version", "types", "policies"],
            "skill-lifecycle.yaml": ["schema_version", "states", "transitions", "thresholds"],
        }
        for fn, keys in required_top_keys.items():
            data = raw[fn]
            missing = [k for k in keys if k not in data]
            if missing:
                raise ValueError(f"policy/{fn} 缺字段: {missing}")
            if data["schema_version"] != 1:
                raise ValueError(f"policy/{fn} schema_version 不兼容: {data['schema_version']}")

    def persist_snapshot(self) -> Path:
        """落盘 snapshot，便于审计重放。"""
        sdir = SNAPSHOT_DIR / self.snapshot_id
        sdir.mkdir(parents=True, exist_ok=True)
        for fn, data in self.raw.items():
            (sdir / fn).write_text(
                yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
                encoding="utf-8",
            )
        meta = {
            "snapshot_id": self.snapshot_id,
            "loaded_at": self.loaded_at.isoformat(),
            "files": list(self.raw.keys()),
        }
        (sdir / "_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
        return sdir


# ──────────────────────────────────────────────────────────────────────
# 单例 + 热重载
# ──────────────────────────────────────────────────────────────────────
_LOCK = threading.Lock()
_BUNDLE: PolicyBundle | None = None


def get_policy() -> PolicyBundle:
    global _BUNDLE
    if _BUNDLE is None:
        with _LOCK:
            if _BUNDLE is None:
                _BUNDLE = PolicyBundle.from_dir()
                try:
                    _BUNDLE.persist_snapshot()
                except OSError as e:
                    logger.warning("policy snapshot 写盘失败：{}", e)
                logger.info("Policy loaded — snapshot={}", _BUNDLE.snapshot_id)
    return _BUNDLE


def reload_policy() -> PolicyBundle:
    """强制重载 policy。失败时保留旧版。"""
    global _BUNDLE
    try:
        new_bundle = PolicyBundle.from_dir()
    except (FileNotFoundError, ValueError, yaml.YAMLError) as e:
        logger.error("Policy reload 失败，保留旧版：{}", e)
        raise
    with _LOCK:
        old_id = _BUNDLE.snapshot_id if _BUNDLE else "<none>"
        _BUNDLE = new_bundle
    try:
        new_bundle.persist_snapshot()
    except OSError as e:
        logger.warning("policy snapshot 写盘失败：{}", e)
    logger.info("Policy reloaded — {} → {}", old_id, new_bundle.snapshot_id)
    return new_bundle


def _signal_reload() -> None:
    """SIGHUP 信号处理器（main 注册）。"""
    try:
        reload_policy()
    except Exception:  # noqa: BLE001
        logger.exception("SIGHUP policy reload 失败")


__all__ = ["PolicyBundle", "get_policy", "reload_policy"]
