"""
SSRF 防护 — 协议白名单 + IP 黑名单 + 域名黑名单 + DNS rebinding 防护。

挂载点：所有用户可控 URL 进入抓取层之前必须 ``validate_url(url)``，
重定向链每一跳也要重新校验（``validate_redirect``）。

威胁模型（OWASP A10:2021）：
- 云元数据 ``169.254.169.254`` / ``metadata.google.internal``
- 内网保留段 ``10/8`` ``172.16/12`` ``192.168/16`` ``127/8``
- IPv6 等价 ``::1`` ``fe80::/10`` ``fc00::/7``
- 非 http(s) 协议 ``file://`` ``gopher://`` ``ftp://`` ``data://``
- 重定向跳到内网 / 元数据
- DNS rebinding（域名首查公网 IP，二查内网 IP）

与 ``compliance/blocklist.py`` 关系：
- ``blocklist`` 负责 ToS / 法规级硬黑名单（domain/path），属业务策略层
- ``ssrf_guard`` 负责协议 / 网络层防护，属安全基线
- 二者互补、串联（先 SSRF，再 blocklist），任何一个命中都拒绝
"""

from __future__ import annotations

import ipaddress
import socket
from collections.abc import Iterable
from urllib.parse import urlparse

# ---------------------------------------------------------------------------
# 策略表
# ---------------------------------------------------------------------------

# 协议白名单
ALLOWED_SCHEMES: frozenset[str] = frozenset({"http", "https"})

# IP 黑名单（云元数据 + 内网保留 + IPv6 等价）
BLOCKED_IP_RANGES: tuple[ipaddress._BaseNetwork, ...] = (
    # IPv4
    ipaddress.ip_network("169.254.0.0/16"),    # link-local（AWS/阿里云/GCP metadata）
    ipaddress.ip_network("127.0.0.0/8"),       # loopback
    ipaddress.ip_network("10.0.0.0/8"),        # 私有网段 A
    ipaddress.ip_network("172.16.0.0/12"),     # 私有网段 B
    ipaddress.ip_network("192.168.0.0/16"),    # 私有网段 C
    ipaddress.ip_network("0.0.0.0/8"),         # "this network"
    ipaddress.ip_network("100.64.0.0/10"),     # CGNAT
    ipaddress.ip_network("224.0.0.0/4"),       # multicast
    ipaddress.ip_network("240.0.0.0/4"),       # reserved
    # IPv6
    ipaddress.ip_network("::1/128"),           # loopback
    ipaddress.ip_network("fe80::/10"),         # link-local
    ipaddress.ip_network("fc00::/7"),          # unique local addresses
    ipaddress.ip_network("fec0::/10"),         # site-local（已废弃但仍拦）
    ipaddress.ip_network("ff00::/8"),          # multicast
    # IPv4-mapped IPv6（防绕过）
    ipaddress.ip_network("::ffff:0.0.0.0/96"),
)

# 域名黑名单（即使解析出公网 IP 也拒绝；额外保险）
BLOCKED_HOSTNAMES: frozenset[str] = frozenset({
    "localhost",
    "metadata.google.internal",
    "metadata.aws.cn",
    "metadata",
    "instance-data",
    "instance-data.ec2.internal",
})

# 重定向最大深度（与 L1 手动 chain 校验配合）
MAX_REDIRECT_DEPTH: int = 5


# ---------------------------------------------------------------------------
# 异常
# ---------------------------------------------------------------------------


class SSRFError(ValueError):
    """SSRF 拦截异常。

    ``code`` 字段供路由层映射到 HTTP 400 + 错误码（不暴露内部 IP / DNS 细节）。
    取值：
    - ``empty``          — URL 为空
    - ``scheme``         — 协议不在白名单
    - ``hostname``       — URL 缺少 hostname
    - ``blocked_host``   — 命中域名黑名单
    - ``dns_fail``       — DNS 解析失败
    - ``private_ip``     — 解析到内网 / 云元数据 / 保留段 IP
    - ``redirect_target``— 重定向目标命中前述任一规则
    - ``redirect_depth`` — 重定向次数超限
    """

    def __init__(self, message: str, *, code: str) -> None:
        super().__init__(message)
        self.code = code


# ---------------------------------------------------------------------------
# 校验
# ---------------------------------------------------------------------------


def _check_ip(ip_str: str) -> None:
    """对单个 IP 字符串做黑名单校验，不通过则 raise。"""
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return  # 非 IP（不可能发生，但兜底跳过）
    # 通用属性兜底：is_private/is_loopback/is_reserved/is_link_local
    if ip.is_private or ip.is_loopback or ip.is_reserved or ip.is_link_local or ip.is_multicast:
        raise SSRFError(f"private/blocked IP: {ip}", code="private_ip")
    for net in BLOCKED_IP_RANGES:
        if ip in net:
            raise SSRFError(f"private/blocked IP: {ip}", code="private_ip")


def _resolve_and_check(hostname: str) -> None:
    """DNS 解析 hostname 并对每一个返回的 IP 做校验。

    DNS rebinding 防护策略：
    - 这里在 ``validate_url`` 中先解析一次（调用前）。
    - L1HttpTier 通过 ``ip_safe_transport`` 在 socket 连接时强制 connect 到这里
      校验过的同一组 IP 之一（见 ``transport_resolver``），避免 DNS rebinding：
      DNS 第一次解析为公网 → 进入 socket 连接前 DNS 又被改回内网。
    - 如果未启用 transport pinning，至少这里能拦掉 99% 静态域名的滥用，并通过
      重定向链每跳重新 validate 拦截动态情况。
    """
    # 先尝试直接解析为 IP（hostname 可能就是字面量 IP）
    try:
        ipaddress.ip_address(hostname)
        _check_ip(hostname)
        return
    except ValueError:
        pass

    # 处理 IPv6 字面量带方括号的情形 [::1]
    bare = hostname.strip("[]")
    try:
        ipaddress.ip_address(bare)
        _check_ip(bare)
        return
    except ValueError:
        pass

    # DNS 解析
    try:
        infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror as exc:
        raise SSRFError(f"DNS fail: {exc}", code="dns_fail") from exc

    seen: set[str] = set()
    for info in infos:
        sockaddr = info[4]
        if not sockaddr:
            continue
        ip_str = sockaddr[0]
        # IPv6 地址可能带 zone id（fe80::1%eth0），剥掉
        ip_str = ip_str.split("%", 1)[0]
        if ip_str in seen:
            continue
        seen.add(ip_str)
        _check_ip(ip_str)


def validate_url(url: str) -> str:
    """对入站 URL 做 SSRF 校验。

    成功返回原 URL；失败抛 :class:`SSRFError`。

    校验顺序（短路）：
    1. 非空
    2. 协议白名单（http / https）
    3. hostname 非空
    4. hostname 在域名黑名单（直接拒绝，不再解析）
    5. DNS 解析后逐 IP 校验（含字面量 IP 情形）
    """
    if not url or not isinstance(url, str):
        raise SSRFError("empty url", code="empty")

    parsed = urlparse(url.strip())

    scheme = (parsed.scheme or "").lower()
    if scheme not in ALLOWED_SCHEMES:
        raise SSRFError(f"scheme not allowed: {scheme!r}", code="scheme")

    hostname = (parsed.hostname or "").lower()
    if not hostname:
        raise SSRFError("missing hostname", code="hostname")

    if hostname in BLOCKED_HOSTNAMES:
        raise SSRFError(f"blocked hostname: {hostname}", code="blocked_host")

    _resolve_and_check(hostname)
    return url


def validate_redirect(response_url: str) -> str:
    """重定向目标 URL 也要走一遍校验。

    专门的封装让调用点意图清晰；命中后 raise 的 ``code`` 重写成 ``redirect_target``，
    便于审计层区分初始请求 vs 重定向链中拦截。
    """
    try:
        return validate_url(str(response_url))
    except SSRFError as exc:
        raise SSRFError(
            f"redirect target rejected: {exc}",
            code="redirect_target",
        ) from exc


# ---------------------------------------------------------------------------
# 工具：批量 / 内部使用
# ---------------------------------------------------------------------------


def is_blocked_ip(ip: str) -> bool:
    """供外层（如 transport hook）轻量复用：判断单个 IP 是否在黑名单。"""
    try:
        _check_ip(ip)
        return False
    except SSRFError:
        return True


def filter_safe_ips(ips: Iterable[str]) -> list[str]:
    """从一组候选 IP 中过滤出未被黑名单命中的（用于 transport pinning）。"""
    return [ip for ip in ips if not is_blocked_ip(ip)]
