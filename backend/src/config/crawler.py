"""Crawler compliance defaults.

The values here intentionally form a conservative baseline. Runtime overrides
may only narrow or explicitly list hosts; more aggressive rate limits require
human review per TASK-09.
"""

from __future__ import annotations

from collections.abc import Iterable

LEGAL_CRAWLER_USER_AGENT = "Anxin-Legal-Crawler/1.0 (+contact: compliance@anxinai.com)"
DEFAULT_HOST_INTERVAL_SECONDS = 1.0
MIN_HOST_INTERVAL_SECONDS = 0.5

DEFAULT_LEGAL_WHITELIST = (
    "court.gov.cn",
    "chinacourt.gov.cn",
    "wenshu.court.gov.cn",
    "zxgk.court.gov.cn",
    "creditchina.gov.cn",
    "npc.gov.cn",
)


def normalize_legal_whitelist(configured_hosts: Iterable[str] | None = None) -> tuple[str, ...]:
    hosts = tuple(
        host.strip().lower() for host in (configured_hosts or ()) if host and host.strip()
    )
    return hosts or DEFAULT_LEGAL_WHITELIST


def clamp_host_interval(seconds: float | int | None = None) -> float:
    if seconds is None:
        return DEFAULT_HOST_INTERVAL_SECONDS
    return max(float(seconds), MIN_HOST_INTERVAL_SECONDS)
