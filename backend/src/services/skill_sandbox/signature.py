# -*- coding: utf-8 -*-
"""
Ed25519 签名校验 —— Skills 沙箱 T1 信任校验

设计见 docs/v3/skills-sandbox-design.md §2 / §10。

签名对象：
    SandboxManifest.fingerprint()  # sha256:...

签名材料：
    canonical_payload = "{fingerprint}|{publisher}"

公钥管理：
    publisher_id → ed25519_public_key_b64
    本期通过环境变量 / 配置加载（``SKILL_SANDBOX_PUBLISHER_KEYS``）；
    P3 阶段接 KMS / 数据库。

使用方式::

    from src.services.skill_sandbox.signature import (
        SignatureVerifier,
        load_publisher_keys_from_settings,
    )

    verifier = SignatureVerifier(load_publisher_keys_from_settings())
    ok = verifier.verify(manifest)

注：``cryptography`` 缺失时 ``verify`` 直接返回 False（fail-closed），
而不是 raise —— 调用方只关心"通不通过"。
"""

from __future__ import annotations

import base64
import logging
import os
from typing import Mapping

from src.services.skill_sandbox.manifest import SandboxManifest, SandboxTier

logger = logging.getLogger(__name__)


class SignatureVerifier:
    """Ed25519 签名校验器。

    Args:
        publisher_keys: ``{publisher_id: base64_ed25519_public_key}``
        require_signature_for: 要求强制签名的 tier 集合（默认 ``{T1}``）
    """

    def __init__(
        self,
        publisher_keys: Mapping[str, str],
        *,
        require_signature_for: set[SandboxTier] | None = None,
    ) -> None:
        # 标准化：剥空白
        self._keys: dict[str, str] = {
            (pub or "").strip(): (key or "").strip()
            for pub, key in publisher_keys.items()
            if pub and key
        }
        self.require_signature_for = require_signature_for or {SandboxTier.T1}

    # ------------------------------------------------------------------
    # 公开
    # ------------------------------------------------------------------

    def is_signature_required(self, tier: SandboxTier) -> bool:
        return tier in self.require_signature_for

    def verify(self, manifest: SandboxManifest) -> bool:
        """返回签名是否有效。

        判定流程：
            1. 不要求签名的 tier → True（不校验，但允许已声明的签名）
            2. 要求签名但未提供 → False
            3. 未知 publisher → False
            4. 解码错误 / 校验失败 → False
            5. 成功 → True
        """
        if not self.is_signature_required(manifest.tier):
            return True
        sig = manifest.signature
        if sig is None:
            return False
        algo = (sig.algo or "").lower()
        if algo != "ed25519":
            logger.warning("不支持的签名算法: %s", algo)
            return False
        pub_b64 = self._keys.get(sig.publisher)
        if pub_b64 is None:
            logger.warning("未知 publisher: %s", sig.publisher)
            return False

        try:
            pub_bytes = base64.b64decode(pub_b64)
            sig_bytes = base64.b64decode(sig.sig)
        except (ValueError, base64.binascii.Error) as exc:  # type: ignore[attr-defined]
            logger.warning("base64 解码失败: %s", exc)
            return False

        try:
            from cryptography.exceptions import InvalidSignature
            from cryptography.hazmat.primitives.asymmetric.ed25519 import (
                Ed25519PublicKey,
            )
        except ImportError:
            logger.warning("cryptography 未安装，无法校验签名 → 默认拒绝")
            return False

        try:
            pub_key = Ed25519PublicKey.from_public_bytes(pub_bytes)
        except Exception as exc:
            logger.warning("公钥载入失败 publisher=%s err=%s", sig.publisher, exc)
            return False

        message = self._canonical_message(manifest).encode("utf-8")
        try:
            pub_key.verify(sig_bytes, message)
            return True
        except InvalidSignature:
            logger.warning(
                "签名校验失败 publisher=%s fingerprint=%s",
                sig.publisher,
                manifest.fingerprint(),
            )
            return False
        except Exception:
            logger.exception("签名校验过程异常")
            return False

    # ------------------------------------------------------------------
    # 工具
    # ------------------------------------------------------------------

    @staticmethod
    def _canonical_message(manifest: SandboxManifest) -> str:
        """签名材料 —— 公开方便客户端生成。

        formula:
            ``{fingerprint}|{publisher}``

        - 把 publisher 一并签进去防止"同一指纹换个 publisher 名"攻击
        - fingerprint 已对 manifest 做规范化 sha256
        """
        sig = manifest.signature
        pub = sig.publisher if sig else ""
        return f"{manifest.fingerprint()}|{pub}"

    @staticmethod
    def sign(
        manifest: SandboxManifest,
        *,
        publisher: str,
        private_key_b64: str,
    ) -> str:
        """用 ed25519 私钥对 manifest 签名，返回 base64 编码的 signature。

        通常仅在**发布工具链**里调用，平台运行时只做 ``verify``。
        """
        from cryptography.hazmat.primitives.asymmetric.ed25519 import (
            Ed25519PrivateKey,
        )

        priv_bytes = base64.b64decode(private_key_b64)
        priv_key = Ed25519PrivateKey.from_private_bytes(priv_bytes)

        # 用一个"占位 manifest"，让 _canonical_message 拿到正确的 publisher
        # 这里要求 manifest.signature 已含 publisher（即使 sig 是空）
        if manifest.signature is None or manifest.signature.publisher != publisher:
            raise ValueError(
                "manifest.signature.publisher 必须与传入 publisher 一致"
            )
        message = SignatureVerifier._canonical_message(manifest).encode("utf-8")
        sig_bytes = priv_key.sign(message)
        return base64.b64encode(sig_bytes).decode("ascii")


# ---------------------------------------------------------------------------
# 工厂
# ---------------------------------------------------------------------------


def load_publisher_keys_from_env(
    env_var: str = "SKILL_SANDBOX_PUBLISHER_KEYS",
) -> dict[str, str]:
    """从环境变量加载 publisher 公钥。

    格式 (逗号分隔的 ``publisher=base64key`` 对)::

        SKILL_SANDBOX_PUBLISHER_KEYS="anxin-platform=AAAA...,partner-x=BBBB..."

    空值 / 缺省 → 返回空字典。
    """
    raw = os.environ.get(env_var, "").strip()
    if not raw:
        return {}
    out: dict[str, str] = {}
    for chunk in raw.split(","):
        if "=" not in chunk:
            continue
        pub, key = chunk.split("=", 1)
        pub = pub.strip()
        key = key.strip()
        if pub and key:
            out[pub] = key
    return out


def load_publisher_keys_from_settings() -> dict[str, str]:
    """从 ``src.core.config.settings`` 取 ``SKILL_SANDBOX_PUBLISHER_KEYS``；
    失败时退到环境变量。
    """
    try:
        from src.core.config import settings
        raw = getattr(settings, "SKILL_SANDBOX_PUBLISHER_KEYS", "") or ""
    except Exception:
        raw = ""
    if not raw:
        return load_publisher_keys_from_env()
    if isinstance(raw, dict):
        return {str(k).strip(): str(v).strip() for k, v in raw.items() if k and v}
    # 字符串格式同 env
    return load_publisher_keys_from_env_value(str(raw))


def load_publisher_keys_from_env_value(raw: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for chunk in raw.split(","):
        if "=" not in chunk:
            continue
        pub, key = chunk.split("=", 1)
        if pub.strip() and key.strip():
            out[pub.strip()] = key.strip()
    return out


__all__ = [
    "SignatureVerifier",
    "load_publisher_keys_from_env",
    "load_publisher_keys_from_settings",
]
