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
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
from typing import Any

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


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
) -> bool:
    """校验飞书事件订阅签名。

    参数：
        timestamp: 来自 ``X-Lark-Request-Timestamp``
        nonce:     来自 ``X-Lark-Request-Nonce``
        body:      原始 HTTP body 字节（必须未经任何重新序列化）
        signature: 来自 ``X-Lark-Signature``
        encrypt_key: 应用配置中的 Encrypt Key

    返回：``True`` 表示签名匹配。

    使用 ``hmac.compare_digest`` 做常量时间比较，避免时序侧信道攻击。
    """
    if not encrypt_key:
        # 未配置加密 Key 即未开启签名校验 — 直接放行（此时应在路由层做其他鉴权）
        return True
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
