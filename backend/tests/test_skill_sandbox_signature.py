# -*- coding: utf-8 -*-
"""
SignatureVerifier 单测 + PolicyGate × Signature 集成验证

覆盖：
    - T0/T2 不要求签名 → verify 直接 True
    - T1 无签名 → False
    - T1 已签名 + 公钥未注册 → False
    - T1 已签名 + 正确公钥 → True
    - T1 已签名 + 篡改 fingerprint → False
    - PolicyGate 接入 verifier：T1 假签名直接 DENY
    - load_publisher_keys_from_env_value 解析 "a=A,b=B"
"""

from __future__ import annotations

import base64

import pytest

cryptography = pytest.importorskip("cryptography")
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey  # noqa: E402

from src.core.deps import UserRole  # noqa: E402
from src.services.skill_sandbox import (  # noqa: E402
    PolicyGate,
    SandboxManifest,
    SandboxTier,
    SignatureVerifier,
    load_publisher_keys_from_env,
)
from src.services.skill_sandbox.signature import (  # noqa: E402
    load_publisher_keys_from_env_value,
)

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _gen_keypair() -> tuple[str, str]:
    """生成一对 ed25519 key，返回 (private_b64, public_b64)。"""
    priv = Ed25519PrivateKey.generate()
    pub = priv.public_key()
    from cryptography.hazmat.primitives.serialization import (
        Encoding,
        NoEncryption,
        PrivateFormat,
        PublicFormat,
    )
    priv_b = priv.private_bytes(
        encoding=Encoding.Raw,
        format=PrivateFormat.Raw,
        encryption_algorithm=NoEncryption(),
    )
    pub_b = pub.public_bytes(encoding=Encoding.Raw, format=PublicFormat.Raw)
    return base64.b64encode(priv_b).decode(), base64.b64encode(pub_b).decode()


def _t1_manifest(publisher: str, sig_b64: str) -> SandboxManifest:
    return SandboxManifest.from_frontmatter({
        "sandbox": {
            "tier": "T1",
            "entrypoint": "m:f",
            "signature": {
                "algo": "ed25519",
                "publisher": publisher,
                "sig": sig_b64,
            },
        }
    })


# ---------------------------------------------------------------------------
# 单元：SignatureVerifier
# ---------------------------------------------------------------------------


def test_non_required_tier_passes() -> None:
    verifier = SignatureVerifier({})
    # T2/T3 不要求签名
    m = SandboxManifest.from_frontmatter({
        "sandbox": {"tier": "T2", "entrypoint": "m:f"}
    })
    assert verifier.verify(m) is True


def test_t1_unsigned_fails() -> None:
    """构造一个无签名的 T1 manifest（绕过 frontmatter 校验）→ verifier 应判 False。"""
    verifier = SignatureVerifier({})
    m = SandboxManifest.model_construct(
        tier=SandboxTier.T1, entrypoint="m:f", signature=None
    )
    assert verifier.verify(m) is False


def test_t1_unknown_publisher_fails() -> None:
    verifier = SignatureVerifier({"known": "AAAA"})
    m = _t1_manifest("unknown", "QUJD")  # ABC base64
    assert verifier.verify(m) is False


def test_t1_valid_signature_passes() -> None:
    priv_b64, pub_b64 = _gen_keypair()
    verifier = SignatureVerifier({"anxin-platform": pub_b64})
    # 先用占位 sig 构造 manifest 拿 fingerprint
    placeholder = _t1_manifest("anxin-platform", "AAAA")
    sig = SignatureVerifier.sign(
        placeholder, publisher="anxin-platform", private_key_b64=priv_b64
    )
    real = _t1_manifest("anxin-platform", sig)
    assert verifier.verify(real) is True


def test_tampered_signature_fails() -> None:
    priv_b64, pub_b64 = _gen_keypair()
    verifier = SignatureVerifier({"anxin-platform": pub_b64})
    placeholder = _t1_manifest("anxin-platform", "AAAA")
    sig = SignatureVerifier.sign(
        placeholder, publisher="anxin-platform", private_key_b64=priv_b64
    )
    # 篡改 sig 的最后一字节
    bad_bytes = bytearray(base64.b64decode(sig))
    bad_bytes[-1] ^= 0xFF
    bad_sig = base64.b64encode(bytes(bad_bytes)).decode()
    tampered = _t1_manifest("anxin-platform", bad_sig)
    assert verifier.verify(tampered) is False


def test_unsupported_algo_fails() -> None:
    verifier = SignatureVerifier({"p": "x"})
    m = SandboxManifest.from_frontmatter({
        "sandbox": {
            "tier": "T1",
            "entrypoint": "m:f",
            "signature": {"algo": "rsa-pss", "publisher": "p", "sig": "AAAA"},
        }
    })
    assert verifier.verify(m) is False


def test_sign_requires_matching_publisher() -> None:
    priv_b64, _ = _gen_keypair()
    m = _t1_manifest("publisher-a", "AAAA")
    with pytest.raises(ValueError):
        SignatureVerifier.sign(m, publisher="publisher-b", private_key_b64=priv_b64)


# ---------------------------------------------------------------------------
# 集成：PolicyGate + verifier
# ---------------------------------------------------------------------------


def test_policy_gate_denies_invalid_signature() -> None:
    priv_b64, pub_b64 = _gen_keypair()
    # 注册公钥
    verifier = SignatureVerifier({"anxin-platform": pub_b64})
    gate = PolicyGate(environment="production", signature_verifier=verifier)

    # 假签名
    fake = _t1_manifest("anxin-platform", base64.b64encode(b"x" * 64).decode())
    res = gate.check(manifest=fake, user_role=UserRole.LAWYER.value)
    assert not res.allow
    assert "签名校验失败" in (res.reason or "")


def test_policy_gate_allows_valid_signature() -> None:
    priv_b64, pub_b64 = _gen_keypair()
    verifier = SignatureVerifier({"anxin-platform": pub_b64})
    gate = PolicyGate(environment="production", signature_verifier=verifier)

    placeholder = _t1_manifest("anxin-platform", "AAAA")
    sig = SignatureVerifier.sign(
        placeholder, publisher="anxin-platform", private_key_b64=priv_b64
    )
    real = _t1_manifest("anxin-platform", sig)
    res = gate.check(manifest=real, user_role=UserRole.LAWYER.value)
    assert res.allow


# ---------------------------------------------------------------------------
# env / settings 加载
# ---------------------------------------------------------------------------


def test_load_keys_from_env_value() -> None:
    out = load_publisher_keys_from_env_value("a=AAAA,b=BBBB, c = CCCC ")
    assert out == {"a": "AAAA", "b": "BBBB", "c": "CCCC"}


def test_load_keys_from_env(monkeypatch) -> None:
    monkeypatch.setenv("SKILL_SANDBOX_PUBLISHER_KEYS", "p1=K1,p2=K2")
    out = load_publisher_keys_from_env()
    assert out == {"p1": "K1", "p2": "K2"}


def test_load_keys_empty_env(monkeypatch) -> None:
    monkeypatch.delenv("SKILL_SANDBOX_PUBLISHER_KEYS", raising=False)
    assert load_publisher_keys_from_env() == {}
