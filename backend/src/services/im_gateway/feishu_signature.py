# -*- coding: utf-8 -*-
"""
飞书事件订阅签名校验 + 加密 payload 解密工具

飞书开放平台事件回调有两种安全机制：

1. 签名校验（Verification Token + HMAC-SHA256）
   服务端按 ``timestamp + nonce + encrypt_key + body`` 拼接后做 SHA-256，
   再 hex digest，与 ``X-Lark-Signature`` 比较。
   参考：https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/event-subscription-guide/event-subscription-configure-/encrypt-key-encryption-configuration-case

2. 加密推送（Encrypt Key + AES-256-CBC）
   payload 字段 ``encrypt`` 为 base64 后的密文：
       key = SHA256(encrypt_key)            # 32 字节
       iv  = ciphertext[:16]
       data = AES-256-CBC-Decrypt(ciphertext[16:], key, iv)
       data 用 PKCS7 去填充后是 UTF-8 JSON

P16-C 安全加固（2026-04-28）：
    - ``verify_signature``：encrypt_key 缺失时改为 fail-closed，除非
      ``FEISHU_VERIFY_SIGNATURE=False`` 显式关闭；之前的"空 key 直接放行"
      在多租户场景被列为 P0 漏洞（A08 综合审计）。
    - 增加 ``X-Lark-Request-Timestamp`` 新鲜度校验（默认 ±300 秒），防
      重放攻击。
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from loguru import logger


class FeishuSignatureError(Exception):
    """飞书签名校验失败 / 配置缺失（fail-closed）。"""


class FeishuTimestampError(FeishuSignatureError):
    """飞书事件 timestamp 不在允许的新鲜度窗口内（疑似 replay）。"""


def _compute_signature(
    timestamp: str,
    nonce: str,
    body: bytes,
    encrypt_key: str,
) -> str:
    """按飞书规则计算签名 hex（SHA-256）。

    飞书算法（事件 v2）：
        sha256(timestamp + nonce + encrypt_key + body).hexdigest()

    注意：这是基于 ``encrypt_key``（加密 Key）做的拼接，并非 HMAC；
    部分文档也称此为 "签名校验"。如未配置 encrypt_key，则不应启用签名校验。
    """
    raw = (timestamp + nonce + encrypt_key).encode("utf-8") + body
    return hashlib.sha256(raw).hexdigest()


def verify_signature(
    timestamp: str,
    nonce: str,
    body: bytes,
    signature: str,
    encrypt_key: str,
    *,
    max_age_seconds: int | None = None,
    now: float | None = None,
) -> bool:
    """校验飞书事件订阅签名（fail-closed）。

    参数：
        timestamp:     来自 ``X-Lark-Request-Timestamp``
        nonce:         来自 ``X-Lark-Request-Nonce``
        body:          原始 HTTP body 字节（必须未经任何重新序列化）
        signature:     来自 ``X-Lark-Signature``
        encrypt_key:   应用配置中的 Encrypt Key
        max_age_seconds: 允许的 timestamp 偏差（默认从 settings 读取，兜底 300）
        now:           注入的当前时间（秒）— 仅测试用

    返回：``True`` 表示签名匹配。

    异常：
        FeishuSignatureError  — encrypt_key 未配置且未显式关闭校验
        FeishuTimestampError  — timestamp 缺失 / 非法 / 超过新鲜度窗口

    使用 ``hmac.compare_digest`` 做常量时间比较，避免时序侧信道攻击。

    P16-C：之前 ``not encrypt_key → return True`` 是 backward-compat 默认，
    但在生产多租户场景下等于"任何未签名请求一律放行"，被列为 P0 漏洞。
    现在改为 fail-closed —— 如确需在本地调试场景关闭，请显式设置
    ``FEISHU_VERIFY_SIGNATURE=False``。
    """
    # 延迟导入，避免单测导入 settings 时的循环依赖
    try:
        from src.core.config import settings  # type: ignore
    except Exception:  # pragma: no cover
        settings = None  # type: ignore[assignment]

    verify_required = True
    cfg_max_age = 300
    if settings is not None:
        verify_required = bool(getattr(settings, "FEISHU_VERIFY_SIGNATURE", True))
        cfg_max_age = int(getattr(settings, "FEISHU_TIMESTAMP_MAX_AGE_SECONDS", 300))

    if max_age_seconds is None:
        max_age_seconds = cfg_max_age

    if not encrypt_key:
        if not verify_required:
            logger.warning(
                "[Feishu] signature verify SKIPPED — FEISHU_VERIFY_SIGNATURE=False"
            )
            return True
        raise FeishuSignatureError(
            "FEISHU_ENCRYPT_KEY 未配置但签名校验为强制项。请配置 "
            "FEISHU_ENCRYPT_KEY；如需在本地/联调环境关闭，请显式设置 "
            "FEISHU_VERIFY_SIGNATURE=False。"
        )

    # ---- timestamp 新鲜度校验（防 replay）----
    if not timestamp:
        raise FeishuTimestampError("X-Lark-Request-Timestamp 缺失")
    try:
        ts_value = int(timestamp)
    except (TypeError, ValueError) as e:
        raise FeishuTimestampError(
            f"X-Lark-Request-Timestamp 非法: {timestamp!r}"
        ) from e
    current = now if now is not None else time.time()
    if abs(current - ts_value) > max_age_seconds:
        raise FeishuTimestampError(
            f"X-Lark-Request-Timestamp 过期或来自未来: "
            f"diff={abs(current - ts_value):.0f}s > {max_age_seconds}s"
        )

    expected = _compute_signature(timestamp, nonce, body, encrypt_key)
    return hmac.compare_digest(expected, signature or "")


def decrypt_payload(encrypted: str, encrypt_key: str) -> dict[str, Any]:
    """解密飞书加密事件 payload。

    参数：
        encrypted:    payload 中的 ``encrypt`` 字段（base64 字符串）
        encrypt_key:  应用配置中的 Encrypt Key

    返回：解密并 JSON 反序列化后的事件字典。

    抛出：
        ValueError：encrypt_key 为空 / base64 解码失败 / 密文长度不合法 /
                     去填充失败 / JSON 解析失败。
    """
    if not encrypt_key:
        raise ValueError("FEISHU_ENCRYPT_KEY 未配置，无法解密加密 payload")

    try:
        ciphertext = base64.b64decode(encrypted)
    except Exception as e:
        raise ValueError(f"飞书加密 payload base64 解码失败: {e}") from e

    if len(ciphertext) < 32 or len(ciphertext) % 16 != 0:
        raise ValueError("飞书加密 payload 长度非法（应为 16 字节倍数且 ≥32）")

    # AES-256-CBC: key = SHA256(encrypt_key), iv = 密文前 16 字节
    key = hashlib.sha256(encrypt_key.encode("utf-8")).digest()
    iv = ciphertext[:16]
    data = ciphertext[16:]

    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    decryptor = cipher.decryptor()
    padded = decryptor.update(data) + decryptor.finalize()

    # PKCS7 去填充
    pad_len = padded[-1]
    if pad_len < 1 or pad_len > 16:
        raise ValueError("飞书加密 payload PKCS7 填充非法")
    plaintext = padded[:-pad_len]

    try:
        return json.loads(plaintext.decode("utf-8"))
    except Exception as e:
        raise ValueError(f"飞书加密 payload JSON 解析失败: {e}") from e
