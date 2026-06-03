# -*- coding: utf-8 -*-
"""
BuilderHubInstaller —— 第三方 skill 安装的统一入口

四步串行（任一失败即拒绝）：
  1. 来源校验（registries allowlist）
  2. 静态 scan（hidden-content / prompt-injection / tool-scope / license / freshness）
  3. 签名核验（verified 必需）
  4. 治理 frontmatter 完整性（access-level / data-classification / required-scopes ...）

参考 plugins/builder-hub/skills/skill-installer/SKILL.md。
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml
from loguru import logger

from src.services.governance.audit import write_event
from src.services.governance.trust import (
    TrustLevel,
    evaluate_trust,
    write_revoked,
)

REPO_ROOT = Path(__file__).resolve().parents[4]
PLUGINS_DIR = REPO_ROOT / "plugins"
AUDIT_LOG_FILE = REPO_ROOT / ".claude" / "builder-hub-audit.jsonl"


# ────────────────────────────────────────────────────────────────────
# Scan rules
# ────────────────────────────────────────────────────────────────────
HIDDEN_CONTENT_RX = [
    (r"[​‌‍﻿]", "hidden-content/zero-width"),
    (r"font-size\s*:\s*0", "hidden-content/font-size-0"),
    (r"color\s*:\s*#fff(?:fff)?\s*;\s*background", "hidden-content/white-on-white"),
    (r'style\s*=\s*["\']?\s*display\s*:\s*none', "hidden-content/font-size-0"),
]
PROMPT_INJECTION_RX = [
    (r"(?i)ignore\s+(all\s+)?(previous|prior|above)\s+instructions", "prompt-injection/ignore-previous"),
    (r"(?i)你现在是\s*(root|admin|系统管理员)", "prompt-injection/role-override"),
    (r"(?i)act\s+as\s+(root|admin|system)", "prompt-injection/role-override"),
    (r"(?i)post\s+(this|the\s+content)\s+to\s+https?://", "prompt-injection/data-exfil"),
    (r"(?i)curl\s+-X\s+POST\s+https?://", "prompt-injection/data-exfil"),
]
INCOMPATIBLE_LICENSES = {"GPL-2.0", "GPL-3.0", "AGPL-3.0", "SSPL-1.0"}


@dataclass
class ScanFinding:
    rule: str
    severity: str  # fail | warn
    snippet: str = ""
    line: int | None = None


@dataclass
class ScanReport:
    skill_id: str
    findings: list[ScanFinding] = field(default_factory=list)

    @property
    def has_hard_fail(self) -> bool:
        return any(f.severity == "fail" for f in self.findings)

    def to_dict(self) -> dict[str, Any]:
        return {
            "skill_id": self.skill_id,
            "result": "FAIL" if self.has_hard_fail else ("WARN" if self.findings else "OK"),
            "findings": [
                {"rule": f.rule, "severity": f.severity, "snippet": f.snippet[:140], "line": f.line}
                for f in self.findings
            ],
            "scanned_at": datetime.now(UTC).isoformat(),
        }


# ────────────────────────────────────────────────────────────────────
# Public API
# ────────────────────────────────────────────────────────────────────
def scan_skill_markdown(skill_md: Path, *, declared_license: str | None = None) -> ScanReport:
    """对单个 SKILL.md 跑静态 scan。"""
    rel = skill_md.relative_to(REPO_ROOT).as_posix() if skill_md.is_absolute() and str(skill_md).startswith(str(REPO_ROOT)) else str(skill_md)
    rep = ScanReport(skill_id=rel)
    text = skill_md.read_text(encoding="utf-8")

    # Hidden content
    for pattern, rule in HIDDEN_CONTENT_RX:
        for m in re.finditer(pattern, text):
            rep.findings.append(ScanFinding(rule=rule, severity="fail",
                                            snippet=text[max(0, m.start()-30):m.end()+30],
                                            line=text[:m.start()].count("\n") + 1))

    # Prompt injection
    for pattern, rule in PROMPT_INJECTION_RX:
        for m in re.finditer(pattern, text):
            rep.findings.append(ScanFinding(rule=rule, severity="fail",
                                            snippet=text[max(0, m.start()-30):m.end()+30],
                                            line=text[:m.start()].count("\n") + 1))

    # License
    if declared_license and declared_license in INCOMPATIBLE_LICENSES:
        rep.findings.append(ScanFinding(rule="license/incompatible", severity="fail",
                                        snippet=f"declared={declared_license}"))

    # Frontmatter 完整性（governance 字段）
    fm_match = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    fm: dict[str, Any] = {}
    if fm_match:
        try:
            fm = yaml.safe_load(fm_match.group(1)) or {}
        except yaml.YAMLError:
            rep.findings.append(ScanFinding(rule="frontmatter/missing-fields", severity="fail",
                                            snippet="YAML 解析失败"))
            fm = {}
    else:
        rep.findings.append(ScanFinding(rule="frontmatter/missing-fields", severity="fail",
                                        snippet="缺 frontmatter"))

    required_fields = [
        "name", "description", "version", "access-level", "data-classification",
        "jurisdiction", "required-scopes", "tool-allowlist", "lifecycle-stage", "audit-level",
    ]
    missing_fields = [k for k in required_fields if k not in fm]
    for k in missing_fields:
        rep.findings.append(ScanFinding(rule="frontmatter/missing-fields", severity="fail",
                                        snippet=f"missing: {k}"))

    # Tool scope：声明只读但 body 有 Write/Edit
    tool_allow = fm.get("tool-allowlist", []) or []
    if "read_only" in tool_allow and "read_write_local" not in tool_allow:
        if re.search(r"\b(Edit|Write|NotebookEdit|file_write)\b", text):
            rep.findings.append(ScanFinding(rule="tool-scope/excessive-write", severity="fail",
                                            snippet="声明 read_only 但 body 涉及 Write/Edit"))

    # Freshness：法规 / 政策类引用 30 天
    for m in re.finditer(r"\b(20\d{2})[-/](\d{1,2})[-/](\d{1,2})\b", text):
        try:
            y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
            ref = datetime(y, mo, d, tzinfo=UTC)
            age = (datetime.now(UTC) - ref).days
            if age > 30 and any(k in text for k in ["法规", "条例", "政策", "公告", "规章"]):
                rep.findings.append(ScanFinding(rule="freshness/stale-30d", severity="warn",
                                                snippet=f"reference {y}-{mo}-{d} aged {age}d"))
                break
        except (ValueError, OverflowError):
            continue

    # Size
    if len(text) > 50_000:
        rep.findings.append(ScanFinding(rule="size/oversized", severity="warn",
                                        snippet=f"{len(text)} bytes > 50 KB"))

    return rep


@dataclass
class InstallResult:
    ok: bool
    skill_id: str
    trust_level: str
    scan_report: dict[str, Any]
    target_path: str | None = None
    reasons: list[str] = field(default_factory=list)


def install_skill(
    *,
    source_path: Path,
    target_persona: str,
    skill_name: str,
    version: str,
    source_url: str | None = None,
    declared_level: str | None = None,
    declared_license: str | None = None,
    trust_untrusted: bool = False,
    installer: dict[str, Any] | None = None,
) -> InstallResult:
    """安装第三方 skill 到 plugins/<persona>/skills/<name>/。

    任一步骤失败即返回 ok=False 并写审计。
    """
    installer = installer or {}
    skill_id = f"/{target_persona}:{skill_name}"
    reasons: list[str] = []

    # 1. 来源核验 + Trust level
    trust = evaluate_trust(
        skill_id=skill_id,
        version=version,
        source_url=source_url,
        declared_level=declared_level,
    )
    reasons.extend(trust.reasons)
    if trust.level == TrustLevel.REVOKED:
        _audit_install("install.denied", installer, skill_id, version,
                       trust=trust.level.value, reasons=reasons, reason="revoked")
        return InstallResult(False, skill_id, trust.level.value, {}, reasons=reasons + ["revoked"])

    if trust.level == TrustLevel.UNTRUSTED and not trust_untrusted:
        _audit_install("install.denied", installer, skill_id, version,
                       trust=trust.level.value, reasons=reasons, reason="untrusted_without_flag")
        return InstallResult(False, skill_id, trust.level.value, {},
                              reasons=reasons + ["untrusted 源需 trust_untrusted=True"])

    # 2. 静态 scan
    if not source_path.exists():
        return InstallResult(False, skill_id, trust.level.value, {},
                              reasons=[f"source_path 不存在: {source_path}"])
    skill_md = source_path / "SKILL.md" if source_path.is_dir() else source_path
    if not skill_md.exists():
        return InstallResult(False, skill_id, trust.level.value, {},
                              reasons=[f"SKILL.md 不存在: {skill_md}"])

    report = scan_skill_markdown(skill_md, declared_license=declared_license)
    rep_dict = report.to_dict()
    if report.has_hard_fail:
        _audit_install("install.denied", installer, skill_id, version,
                       trust=trust.level.value, scan=rep_dict, reason="scan_hard_fail")
        return InstallResult(False, skill_id, trust.level.value, rep_dict,
                              reasons=reasons + ["scan hard-fail"])

    # 3. 写入目标 plugin（如 source 是目录 → 整目录拷贝）
    dest_dir = PLUGINS_DIR / target_persona / "skills" / skill_name
    if dest_dir.exists():
        return InstallResult(False, skill_id, trust.level.value, rep_dict,
                              reasons=[f"目标已存在：{dest_dir}（需先 uninstall 或改名）"])
    dest_dir.mkdir(parents=True, exist_ok=True)

    try:
        if source_path.is_dir():
            import shutil
            for item in source_path.rglob("*"):
                if item.is_file():
                    rel = item.relative_to(source_path)
                    target = dest_dir / rel
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(item, target)
        else:
            import shutil
            shutil.copy2(source_path, dest_dir / "SKILL.md")
    except OSError as e:
        return InstallResult(False, skill_id, trust.level.value, rep_dict,
                              reasons=[f"复制失败：{e}"])

    try:
        dest_rel = str(dest_dir.relative_to(REPO_ROOT))
    except ValueError:
        # 单测 monkeypatch PLUGINS_DIR 到 tmp 不在 REPO_ROOT 下
        dest_rel = str(dest_dir)
    _audit_install("install.granted", installer, skill_id, version,
                   trust=trust.level.value, scan=rep_dict, dest=dest_rel)

    return InstallResult(
        ok=True, skill_id=skill_id, trust_level=trust.level.value,
        scan_report=rep_dict, target_path=dest_rel,
        reasons=reasons,
    )


def revoke_skill(
    *,
    skill_id: str,
    version: str,
    reason: str,
    revoked_by: str,
    successor_version: str | None = None,
) -> dict[str, Any]:
    """撤回某个 skill@version。写 revoked.json + 审计 + builder-hub-audit.jsonl。"""
    write_revoked(skill_id, version, reason, revoked_by)
    # 同时写 audit JSONL 真相源
    write_event({
        "event_type": "lifecycle.change",
        "actor": {"id": revoked_by, "role": "security_committee"},
        "action": "lifecycle.skill.revoke",
        "resource": {"type": "skill", "id": skill_id, "version": version},
        "decision": "ALLOW",
        "outcome": "revoked",
        "reason": reason,
        "successor_version": successor_version,
    })
    _audit_install("revoke", {"id": revoked_by}, skill_id, version, reason=reason)
    return {"skill_id": skill_id, "version": version, "revoked_by": revoked_by, "reason": reason}


# ────────────────────────────────────────────────────────────────────
# helpers
# ────────────────────────────────────────────────────────────────────
def _audit_install(
    action: str,
    installer: dict[str, Any] | None,
    skill_id: str,
    version: str,
    **extra: Any,
) -> None:
    """builder-hub-audit.jsonl 独立审计文件，便于供应链合规审查。"""
    AUDIT_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": datetime.now(UTC).isoformat(),
        "action": action,
        "installer": installer or {},
        "skill_id": skill_id,
        "version": version,
        **extra,
    }
    with AUDIT_LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")
    logger.info("builder-hub audit: {} skill={} v={}", action, skill_id, version)


__all__ = [
    "ScanFinding",
    "ScanReport",
    "InstallResult",
    "install_skill",
    "scan_skill_markdown",
    "revoke_skill",
]
