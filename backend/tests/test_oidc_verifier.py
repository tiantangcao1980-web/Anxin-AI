# -*- coding: utf-8 -*-
"""
OidcVerifier 单测

覆盖：
    - 配置缺失抛 OidcUnavailable
    - id_token 格式非法 → OidcError
    - 算法不在白名单 → OidcError
    - 签名错 → OidcError
    - 正确签名 + 正确 iss/aud → 返回 claims
    - aud 不匹配 → OidcError
    - 过期 → OidcError
    - JWKS 缺失对应 kid → OidcError
"""

from __future__ import annotations

import base64
import json
import time

import pytest

cryptography = pytest.importorskip("cryptography")
jose = pytest.importorskip("jose")

from cryptography.hazmat.primitives.asymmetric import rsa  # noqa: E402
from jose import jwt  # noqa: E402
from jose.utils import base64url_encode  # noqa: E402

from src.core.oidc import (
    OidcConfig,
    OidcError,
    OidcUnavailable,
    OidcVerifier,
)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _gen_rsa_jwk(kid: str = "k1") -> tuple[dict, dict]:
    """生成 RSA key 对：返回 ``(private_jwk_dict, public_jwk_dict)``。

    private 是 python-jose 用的字典 PEM；public 是 JWKS 格式。
    """
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    from cryptography.hazmat.primitives import serialization

    pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    pub = private_key.public_key().public_numbers()
    n = pub.n
    e = pub.e

    def b64u(n_int: int) -> str:
        b = n_int.to_bytes((n_int.bit_length() + 7) // 8, "big")
        return base64url_encode(b).decode("ascii").rstrip("=")

    jwk = {
        "kty": "RSA",
        "kid": kid,
        "use": "sig",
        "alg": "RS256",
        "n": b64u(n),
        "e": b64u(e),
    }
    return {"pem": pem.decode(), "kid": kid}, jwk


def _make_token(
    private: dict,
    *,
    issuer: str,
    audience: str,
    sub: str = "u-1",
    email: str = "alice@corp.example",
    extra: dict | None = None,
    exp_offset_sec: int = 300,
) -> str:
    now = int(time.time())
    claims = {
        "iss": issuer,
        "aud": audience,
        "sub": sub,
        "email": email,
        "iat": now,
        "exp": now + exp_offset_sec,
    }
    if extra:
        claims.update(extra)
    return jwt.encode(
        claims,
        private["pem"],
        algorithm="RS256",
        headers={"kid": private["kid"]},
    )


class _StubVerifier(OidcVerifier):
    """子类化 OidcVerifier，跳过 discovery / 网络拉 JWKS。"""

    def __init__(self, config: OidcConfig, jwks_keys: list[dict]) -> None:
        super().__init__(config)
        from src.core.oidc import _JwksCacheEntry
        self._cache = _JwksCacheEntry(keys=list(jwks_keys), fetched_at=time.time())


# ---------------------------------------------------------------------------
# tests
# ---------------------------------------------------------------------------


def test_missing_issuer_raises() -> None:
    with pytest.raises(OidcUnavailable):
        OidcVerifier(OidcConfig(issuer="", client_id="c"))


def test_missing_client_id_raises() -> None:
    with pytest.raises(OidcUnavailable):
        OidcVerifier(OidcConfig(issuer="https://idp.example", client_id=""))


@pytest.mark.asyncio
async def test_invalid_token_format_rejected() -> None:
    priv, pub = _gen_rsa_jwk()
    v = _StubVerifier(
        OidcConfig(issuer="https://idp.example", client_id="c"),
        [pub],
    )
    with pytest.raises(OidcError):
        await v.verify_id_token("not-a-jwt")


@pytest.mark.asyncio
async def test_valid_signature_passes() -> None:
    priv, pub = _gen_rsa_jwk()
    cfg = OidcConfig(issuer="https://idp.example", client_id="c-abc")
    v = _StubVerifier(cfg, [pub])
    token = _make_token(priv, issuer="https://idp.example", audience="c-abc")
    claims = await v.verify_id_token(token)
    assert claims["sub"] == "u-1"
    assert claims["email"] == "alice@corp.example"


@pytest.mark.asyncio
async def test_audience_mismatch_rejected() -> None:
    priv, pub = _gen_rsa_jwk()
    cfg = OidcConfig(issuer="https://idp.example", client_id="c-abc")
    v = _StubVerifier(cfg, [pub])
    token = _make_token(priv, issuer="https://idp.example", audience="other-aud")
    with pytest.raises(OidcError):
        await v.verify_id_token(token)


@pytest.mark.asyncio
async def test_issuer_mismatch_rejected() -> None:
    priv, pub = _gen_rsa_jwk()
    cfg = OidcConfig(issuer="https://idp.example", client_id="c")
    v = _StubVerifier(cfg, [pub])
    token = _make_token(priv, issuer="https://attacker.example", audience="c")
    with pytest.raises(OidcError):
        await v.verify_id_token(token)


@pytest.mark.asyncio
async def test_expired_token_rejected() -> None:
    priv, pub = _gen_rsa_jwk()
    cfg = OidcConfig(
        issuer="https://idp.example", client_id="c", clock_skew_sec=0
    )
    v = _StubVerifier(cfg, [pub])
    token = _make_token(
        priv,
        issuer="https://idp.example",
        audience="c",
        exp_offset_sec=-60,
    )
    with pytest.raises(OidcError):
        await v.verify_id_token(token)


@pytest.mark.asyncio
async def test_disallowed_algorithm_rejected() -> None:
    priv, pub = _gen_rsa_jwk()
    cfg = OidcConfig(
        issuer="https://idp.example",
        client_id="c",
        allowed_algorithms=("RS512",),
    )
    v = _StubVerifier(cfg, [pub])
    token = _make_token(priv, issuer="https://idp.example", audience="c")
    with pytest.raises(OidcError):
        await v.verify_id_token(token)


@pytest.mark.asyncio
async def test_kid_not_in_jwks_rejected(monkeypatch) -> None:
    priv, pub = _gen_rsa_jwk(kid="k1")
    _, other_pub = _gen_rsa_jwk(kid="k2")
    cfg = OidcConfig(issuer="https://idp.example", client_id="c")
    v = _StubVerifier(cfg, [other_pub])
    # 让 refresh_jwks 也不再变化 —— 直接 monkeypatch 成 noop
    async def _noop():
        pass
    monkeypatch.setattr(v, "_refresh_jwks", _noop)
    token = _make_token(priv, issuer="https://idp.example", audience="c")
    with pytest.raises(OidcError):
        await v.verify_id_token(token)


@pytest.mark.asyncio
async def test_audience_override_takes_precedence() -> None:
    priv, pub = _gen_rsa_jwk()
    cfg = OidcConfig(
        issuer="https://idp.example",
        client_id="local-id",
        audience_override="external-aud",
    )
    v = _StubVerifier(cfg, [pub])
    token = _make_token(priv, issuer="https://idp.example", audience="external-aud")
    claims = await v.verify_id_token(token)
    assert claims["aud"] == "external-aud"
