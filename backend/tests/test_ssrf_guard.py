# -*- coding: utf-8 -*-
"""
SSRF 防护单元测试 — 覆盖 OWASP A10:2021 主要场景。

测试矩阵：
- 协议白名单：http/https 通过；file/gopher/ftp/data 拒
- 域名黑名单：localhost / metadata.google.internal 拒
- IP 黑名单：169.254/16 (云元数据) / 127.0.0.0/8 (loopback)
  / 10.x / 172.16.x / 192.168.x (内网) / 0.0.0.0 / IPv6 ::1 / fe80::
- DNS 解析失败：抛 dns_fail
- DNS rebinding：mock socket.getaddrinfo 返回内网 IP
- 重定向链：mock httpx，redirect 到内网拦截
"""

from __future__ import annotations

import socket
from unittest.mock import patch

import pytest

from src.services.fetch.ssrf_guard import (
    SSRFError,
    is_blocked_ip,
    validate_redirect,
    validate_url,
)


def _fake_addrinfo(ip: str):
    """构造 socket.getaddrinfo 期望的返回结构。"""
    family = socket.AF_INET6 if ":" in ip else socket.AF_INET
    return [(family, socket.SOCK_STREAM, 0, "", (ip, 0))]


# ---------------------------------------------------------------------------
# 协议白名单
# ---------------------------------------------------------------------------


def test_allowed_https():
    """https + 公网域名应通过（mock DNS 到公网 IP）。"""
    with patch("socket.getaddrinfo", return_value=_fake_addrinfo("142.250.80.46")):
        assert validate_url("https://www.google.com/") == "https://www.google.com/"


def test_allowed_http():
    with patch("socket.getaddrinfo", return_value=_fake_addrinfo("93.184.216.34")):
        assert validate_url("http://example.com/path") == "http://example.com/path"


def test_blocked_scheme_file():
    with pytest.raises(SSRFError) as exc:
        validate_url("file:///etc/passwd")
    assert exc.value.code == "scheme"


def test_blocked_scheme_gopher():
    with pytest.raises(SSRFError) as exc:
        validate_url("gopher://evil.com:6379/_FLUSHALL")
    assert exc.value.code == "scheme"


def test_blocked_scheme_ftp():
    with pytest.raises(SSRFError) as exc:
        validate_url("ftp://internal.lan/secret.txt")
    assert exc.value.code == "scheme"


def test_blocked_scheme_data():
    with pytest.raises(SSRFError) as exc:
        validate_url("data:text/html,<script>alert(1)</script>")
    assert exc.value.code == "scheme"


def test_empty_url():
    with pytest.raises(SSRFError) as exc:
        validate_url("")
    assert exc.value.code == "empty"


def test_missing_hostname():
    with pytest.raises(SSRFError) as exc:
        validate_url("http:///path-only")
    assert exc.value.code == "hostname"


# ---------------------------------------------------------------------------
# 域名黑名单
# ---------------------------------------------------------------------------


def test_blocked_hostname_localhost():
    with pytest.raises(SSRFError) as exc:
        validate_url("http://localhost/admin")
    assert exc.value.code == "blocked_host"


def test_blocked_hostname_metadata_google():
    with pytest.raises(SSRFError) as exc:
        validate_url("http://metadata.google.internal/computeMetadata/v1/")
    assert exc.value.code == "blocked_host"


def test_blocked_hostname_metadata_aws_cn():
    with pytest.raises(SSRFError) as exc:
        validate_url("http://metadata.aws.cn/latest/meta-data/")
    assert exc.value.code == "blocked_host"


# ---------------------------------------------------------------------------
# IP 黑名单（字面量 IP，无需 DNS）
# ---------------------------------------------------------------------------


def test_blocked_aws_metadata():
    """AWS / 阿里云 / GCP 元数据服务 169.254.169.254。"""
    with pytest.raises(SSRFError) as exc:
        validate_url("http://169.254.169.254/latest/meta-data/")
    assert exc.value.code == "private_ip"


def test_blocked_loopback_ipv4():
    with pytest.raises(SSRFError) as exc:
        validate_url("http://127.0.0.1:8080/admin")
    assert exc.value.code == "private_ip"


def test_blocked_loopback_127_other():
    """127/8 整段都拦，不只 127.0.0.1。"""
    with pytest.raises(SSRFError) as exc:
        validate_url("http://127.1.2.3/")
    assert exc.value.code == "private_ip"


def test_blocked_internal_192_168():
    with pytest.raises(SSRFError) as exc:
        validate_url("http://192.168.1.100:5432/")
    assert exc.value.code == "private_ip"


def test_blocked_internal_10_x():
    with pytest.raises(SSRFError) as exc:
        validate_url("http://10.0.0.5/internal-api")
    assert exc.value.code == "private_ip"


def test_blocked_internal_172_16():
    with pytest.raises(SSRFError) as exc:
        validate_url("http://172.20.0.1/")
    assert exc.value.code == "private_ip"


def test_blocked_zero_address():
    with pytest.raises(SSRFError) as exc:
        validate_url("http://0.0.0.0/")
    assert exc.value.code == "private_ip"


def test_blocked_cgnat_100_64():
    with pytest.raises(SSRFError) as exc:
        validate_url("http://100.64.0.1/")
    assert exc.value.code == "private_ip"


# ---------------------------------------------------------------------------
# IPv6
# ---------------------------------------------------------------------------


def test_ipv6_loopback_rejected():
    with pytest.raises(SSRFError) as exc:
        validate_url("http://[::1]/admin")
    assert exc.value.code == "private_ip"


def test_ipv6_link_local_rejected():
    with pytest.raises(SSRFError) as exc:
        validate_url("http://[fe80::1]/")
    assert exc.value.code == "private_ip"


def test_ipv6_unique_local_rejected():
    with pytest.raises(SSRFError) as exc:
        validate_url("http://[fc00::1]/")
    assert exc.value.code == "private_ip"


# ---------------------------------------------------------------------------
# DNS rebinding（mock）
# ---------------------------------------------------------------------------


def test_dns_resolves_to_private_ip_rejected():
    """域名公网注册，但 DNS 解析返回内网 IP — DNS rebinding 攻击。"""
    with patch("socket.getaddrinfo", return_value=_fake_addrinfo("10.0.0.5")):
        with pytest.raises(SSRFError) as exc:
            validate_url("http://attacker-rebind.example/")
        assert exc.value.code == "private_ip"


def test_dns_resolves_to_metadata_rejected():
    """域名解析到云元数据 IP（典型 SSRF 绕过）。"""
    with patch("socket.getaddrinfo", return_value=_fake_addrinfo("169.254.169.254")):
        with pytest.raises(SSRFError) as exc:
            validate_url("http://metadata-bypass.example/")
        assert exc.value.code == "private_ip"


def test_dns_multi_record_any_private_rejected():
    """multi-A 记录中任一 IP 在黑名单都拦截。"""
    fake = [
        (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("142.250.80.46", 0)),
        (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("10.0.0.5", 0)),
    ]
    with patch("socket.getaddrinfo", return_value=fake):
        with pytest.raises(SSRFError) as exc:
            validate_url("http://multi-record.example/")
        assert exc.value.code == "private_ip"


def test_dns_fail():
    with patch("socket.getaddrinfo", side_effect=socket.gaierror("Name or service not known")):
        with pytest.raises(SSRFError) as exc:
            validate_url("http://this-host-does-not-exist.invalid/")
        assert exc.value.code == "dns_fail"


# ---------------------------------------------------------------------------
# 重定向校验
# ---------------------------------------------------------------------------


def test_redirect_to_private_ip_rejected():
    """validate_redirect 把异常 code 改写成 redirect_target。"""
    with pytest.raises(SSRFError) as exc:
        validate_redirect("http://169.254.169.254/latest/meta-data/")
    assert exc.value.code == "redirect_target"


def test_redirect_to_loopback_rejected():
    with pytest.raises(SSRFError) as exc:
        validate_redirect("http://127.0.0.1:8500/v1/agent/services")
    assert exc.value.code == "redirect_target"


def test_redirect_scheme_change_to_file_rejected():
    """常见 SSRF 链：先 http 公网，再 redirect file://"""
    with pytest.raises(SSRFError) as exc:
        validate_redirect("file:///etc/shadow")
    assert exc.value.code == "redirect_target"


def test_redirect_to_public_passes():
    with patch("socket.getaddrinfo", return_value=_fake_addrinfo("142.250.80.46")):
        assert validate_redirect("https://www.google.com/") == "https://www.google.com/"


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------


def test_is_blocked_ip_helper():
    assert is_blocked_ip("169.254.169.254") is True
    assert is_blocked_ip("127.0.0.1") is True
    assert is_blocked_ip("10.0.0.5") is True
    assert is_blocked_ip("::1") is True
    assert is_blocked_ip("8.8.8.8") is False
    assert is_blocked_ip("142.250.80.46") is False


def test_ssrf_error_carries_code():
    err = SSRFError("test", code="scheme")
    assert err.code == "scheme"
    assert "test" in str(err)
