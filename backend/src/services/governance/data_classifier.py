# -*- coding: utf-8 -*-
"""
DataClassifier —— 数据分级 + PII 识别 + 脱敏 / 还原

约定见 docs/governance/DATA-BOUNDARY.md，规则源 policy/pii-redaction.yaml
+ policy/data-classification.yaml。
"""
from __future__ import annotations

import hashlib
import hmac
import os
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any

from loguru import logger

from src.services.governance.policy_loader import get_policy


class Classification(str, Enum):
    L1 = "L1"
    L2 = "L2"
    L3 = "L3"
    L4 = "L4"
    L5 = "L5"

    @property
    def level(self) -> int:
        return int(self.value[1:])


@dataclass(frozen=True)
class PIIFinding:
    type: str
    span: tuple[int, int]
    classification: Classification


_MASK_KEY = os.getenv("ANXIN_PII_MASK_KEY", "dev-only-pii-key").encode()


def _luhn_ok(s: str) -> bool:
    digits = [int(c) for c in s if c.isdigit()]
    if len(digits) < 13:
        return False
    chk = 0
    for i, d in enumerate(reversed(digits)):
        if i % 2:
            d *= 2
            if d > 9:
                d -= 9
        chk += d
    return chk % 10 == 0


def _cn_id_checksum_ok(s: str) -> bool:
    if len(s) != 18:
        return False
    weights = [7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2]
    check_codes = ["1", "0", "X", "9", "8", "7", "6", "5", "4", "3", "2"]
    try:
        total = sum(int(s[i]) * weights[i] for i in range(17))
    except ValueError:
        return False
    return check_codes[total % 11].lower() == s[-1].lower()


_CHECKS = {
    "cn_id_checksum": _cn_id_checksum_ok,
    "luhn_checksum": _luhn_ok,
    # 其它 checksum 视需要拓展
}


def classify(text: str) -> tuple[Classification, list[PIIFinding]]:
    """返回 (highest_classification, findings[])。"""
    if not text:
        return Classification.L1, []
    policy = get_policy()
    rules = policy.pii_redaction.get("types", {})
    findings: list[PIIFinding] = []
    highest = Classification.L1

    for pii_type, cfg in rules.items():
        pattern = cfg.get("regex")
        if not pattern:
            continue
        try:
            rx = re.compile(pattern)
        except re.error:
            logger.warning("PII regex 编译失败：{}", pii_type)
            continue
        for m in rx.finditer(text):
            value = m.group(0)
            check = cfg.get("extra_check")
            if check and check in _CHECKS and not _CHECKS[check](value):
                continue
            cls = Classification(cfg.get("classification", "L3"))
            findings.append(PIIFinding(type=pii_type, span=m.span(), classification=cls))
            if cls.level > highest.level:
                highest = cls
    return highest, findings


def _mask_value(value: str, strategy: str, params: dict) -> str:
    if strategy == "reject":
        raise ValueError("PII rejected (CVV-class data forbidden)")
    if strategy == "keep_head_tail":
        head = params.get("head", 3)
        tail = params.get("tail", 4)
        fill = params.get("fill", "*")
        if len(value) <= head + tail:
            return fill * len(value)
        return value[:head] + fill * (len(value) - head - tail) + value[-tail:] if tail else value[:head] + fill * (len(value) - head)
    if strategy == "keep_tail":
        tail = params.get("tail", 4)
        fill = params.get("fill", "*")
        if len(value) <= tail:
            return fill * len(value)
        return fill * (len(value) - tail) + value[-tail:]
    if strategy == "email_local_partial":
        if "@" not in value:
            return "***"
        local, _, domain = value.partition("@")
        return (local[:1] + "***" if local else "***") + "@" + domain
    if strategy == "gps_round":
        precision = params.get("precision", 2)
        try:
            lat, lon = [float(x.strip()) for x in value.split(",")]
            return f"{round(lat, precision)},{round(lon, precision)}"
        except ValueError:
            return value
    return "***"


def mask(text: str, *, with_marker: bool = True) -> tuple[str, list[PIIFinding]]:
    """脱敏全文。返回 (脱敏后文本, findings)。"""
    if not text:
        return text, []
    policy = get_policy()
    rules = policy.pii_redaction.get("types", {})

    # 收集所有命中，按 span 反向替换避免位移
    matches: list[tuple[int, int, str, str]] = []  # (start, end, masked, type)
    for pii_type, cfg in rules.items():
        pattern = cfg.get("regex")
        if not pattern:
            continue
        try:
            rx = re.compile(pattern)
        except re.error:
            continue
        strategy = cfg.get("mask_strategy", "keep_head_tail")
        params = cfg.get("mask_params", {})
        check = cfg.get("extra_check")
        for m in rx.finditer(text):
            value = m.group(0)
            if check and check in _CHECKS and not _CHECKS[check](value):
                continue
            try:
                masked = _mask_value(value, strategy, params)
            except ValueError:
                masked = "<REJECTED>"
            if with_marker:
                masked = f"<PII:type={pii_type}>{masked}</PII>"
            matches.append((m.start(), m.end(), masked, pii_type))

    # 解决重叠：保留更长的命中
    matches.sort(key=lambda x: (x[0], -(x[1] - x[0])))
    deduped: list[tuple[int, int, str, str]] = []
    last_end = -1
    for start, end, masked, t in matches:
        if start >= last_end:
            deduped.append((start, end, masked, t))
            last_end = end

    # 替换
    out_parts: list[str] = []
    cursor = 0
    findings: list[PIIFinding] = []
    for start, end, masked, t in deduped:
        out_parts.append(text[cursor:start])
        out_parts.append(masked)
        cursor = end
        cls = Classification(rules[t].get("classification", "L3"))
        findings.append(PIIFinding(type=t, span=(start, end), classification=cls))
    out_parts.append(text[cursor:])
    return "".join(out_parts), findings


def unmask(masked: str, *, subject: dict, original_lookup: callable | None = None) -> str:  # type: ignore[type-arg]
    """还原：只有持 `super_admin` 或 `compliance_officer` 的 subject 才能调用。

    原文从 KMS / 持久化 PII vault 取回（通过传入的 `original_lookup` 闭包）。
    审计事件 `pii.unmask` 必写。
    """
    policy = get_policy()
    authority = policy.pii_redaction.get("unmask", {}).get("default_authority", [])
    if subject.get("role") not in authority:
        raise PermissionError(f"role={subject.get('role')} 无 PII unmask 权限")
    if original_lookup is None:
        raise ValueError("unmask 需要 original_lookup 回调")
    # 简化：把 <PII:...>masked</PII> 标签替换回原文
    return re.sub(
        r"<PII:type=([a-z_]+)>(.+?)</PII>",
        lambda m: original_lookup(m.group(1), m.group(2)) or m.group(2),
        masked,
    )


__all__ = ["Classification", "PIIFinding", "classify", "mask", "unmask"]
