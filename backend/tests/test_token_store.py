# -*- coding: utf-8 -*-
"""
TokenStore 加解密 + key rotation 单元测试（P4-A）

不依赖数据库 / FastAPI，纯 Fernet 行为验证。
"""

from __future__ import annotations

# SQLite ↔ JSONB 兼容补丁（必须在 import models 前生效；
# conftest setup_test_db 会 create_all 全表，包括 app_authorizations.scopes JSONB）
from sqlalchemy.dialects.sqlite.base import SQLiteTypeCompiler as _SQLiteTC

if not hasattr(_SQLiteTC, "visit_JSONB"):
    def _visit_JSONB(self, type_, **kw):  # noqa: N802
        return self.visit_JSON(type_, **kw)

    _SQLiteTC.visit_JSONB = _visit_JSONB  # type: ignore[attr-defined]


import pytest
from cryptography.fernet import Fernet, InvalidToken

# 触发 ORM 表注册，让 setup_test_db 能 create_all
from src.services.app_authorization.models import (  # noqa: F401
    AppAuthorization,
    AppToken,
)
from src.services.app_authorization.token_store import (
    TokenStore,
    TokenStoreConfigError,
)


# ---------------------------------------------------------------------------
# 1. 单 key 加解密往返
# ---------------------------------------------------------------------------


def test_encrypt_decrypt_roundtrip():
    """单 key 模式下 encrypt → decrypt 还原原文。"""
    key = Fernet.generate_key().decode()
    store = TokenStore(keys=[key])

    plain = "ya29.a0AfH6abc-DEFGHI_jkl1234567890"
    blob = store.encrypt(plain)

    assert isinstance(blob, bytes)
    assert blob != plain.encode()  # 确实加密了

    recovered = store.decrypt(blob)
    assert recovered == plain
    assert store.key_count == 1


def test_encrypt_optional_handles_none():
    """encrypt_optional / decrypt_optional 对 None 透传。"""
    key = Fernet.generate_key().decode()
    store = TokenStore(keys=[key])

    assert store.encrypt_optional(None) is None
    assert store.decrypt_optional(None) is None

    # 非 None 走加密
    blob = store.encrypt_optional("refresh_xxx")
    assert blob is not None
    assert store.decrypt_optional(blob) == "refresh_xxx"


def test_decrypt_with_wrong_key_raises_invalid_token():
    """用另一把 key 解密会抛 InvalidToken（外层应捕获并标 status=error）。"""
    store_a = TokenStore(keys=[Fernet.generate_key().decode()])
    store_b = TokenStore(keys=[Fernet.generate_key().decode()])

    blob = store_a.encrypt("secret")
    with pytest.raises(InvalidToken):
        store_b.decrypt(blob)


def test_encrypt_rejects_non_str():
    with pytest.raises(TypeError):
        TokenStore(keys=[Fernet.generate_key().decode()]).encrypt(b"not_a_str")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# 2. Key rotation（MultiFernet）
# ---------------------------------------------------------------------------


def test_key_rotation_decrypts_old_and_encrypts_with_new():
    """key rotation：新 key 在前，老 key 在后；
    - 用单 老 key 加密的 blob 仍可被多 key store 解密
    - 多 key store 加密永远用第一个 key（新 key）
    """
    old_key = Fernet.generate_key().decode()
    new_key = Fernet.generate_key().decode()

    # 旧库（rotation 之前）加密的 blob
    old_store = TokenStore(keys=[old_key])
    old_blob = old_store.encrypt("token_old")

    # rotation 期间：新 key 在前，旧 key 在后
    rotation_store = TokenStore(keys=[new_key, old_key])
    assert rotation_store.key_count == 2

    # 旧 blob 仍可解
    assert rotation_store.decrypt(old_blob) == "token_old"

    # 新加密的 blob 必须被「只有新 key」的库解开（证明是用新 key 加密的）
    new_blob = rotation_store.encrypt("token_new")
    new_only = TokenStore(keys=[new_key])
    assert new_only.decrypt(new_blob) == "token_new"

    # 反过来，纯老 key 库解不开新 blob
    old_only = TokenStore(keys=[old_key])
    with pytest.raises(InvalidToken):
        old_only.decrypt(new_blob)


# ---------------------------------------------------------------------------
# 3. 配置错误
# ---------------------------------------------------------------------------


def test_empty_keys_raises_config_error():
    with pytest.raises(TokenStoreConfigError):
        TokenStore(keys=[])


def test_invalid_key_raises_config_error():
    with pytest.raises(TokenStoreConfigError):
        TokenStore(keys=["not_a_valid_fernet_key"])


def test_from_settings_when_unset_raises(monkeypatch):
    """settings.OAUTH_TOKEN_ENCRYPTION_KEY 为空时报有用错误。"""
    from src.core.config import settings

    monkeypatch.setattr(settings, "OAUTH_TOKEN_ENCRYPTION_KEY", "", raising=False)
    with pytest.raises(TokenStoreConfigError):
        TokenStore.from_settings()


def test_from_settings_supports_comma_separated_keys(monkeypatch):
    """settings 中逗号分隔多 key → 自动启用 MultiFernet。"""
    from src.core.config import settings

    k1 = Fernet.generate_key().decode()
    k2 = Fernet.generate_key().decode()
    monkeypatch.setattr(
        settings,
        "OAUTH_TOKEN_ENCRYPTION_KEY",
        f"{k1},{k2}",
        raising=False,
    )

    store = TokenStore.from_settings()
    assert store.key_count == 2

    # 加密用 k1 → 仅含 k1 的 store 可解
    blob = store.encrypt("hi")
    only_k1 = TokenStore(keys=[k1])
    assert only_k1.decrypt(blob) == "hi"
