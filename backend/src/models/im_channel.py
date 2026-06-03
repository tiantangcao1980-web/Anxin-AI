# -*- coding: utf-8 -*-
"""IM 渠道（im_gateway_channels）模型对外稳定入口。

权威 ORM 定义在 ``src.services.im_gateway.models`` —— 它早于本期就被 IM 网关
adapters / 配对服务使用（表名 ``im_gateway_channels``）。为满足"渠道配置管理后端"
（P3-C）对模型层的一致引用，且避免重复定义同名表造成 ``Base.metadata`` 冲突，
本模块仅做 **re-export**，把渠道相关符号收敛到 ``src.models`` 命名空间，与其它
模型（``src.models.im`` 等）的导入风格保持一致。

JSON 列约定说明：权威模型 ``IMChannel.config`` 沿用 im_gateway 既有的
postgresql ``JSONB``。该列在 SQLite（测试）下由 SQLAlchemy 退化为通用 JSON 编解码，
不会破坏内存库 create_all（既有 im_gateway 配对测试已验证）。新写的渠道管理代码
不引入额外 PG 专属列。
"""

from __future__ import annotations

from src.services.im_gateway.models import (
    IMBinding,
    IMChannel,
    IMChannelStatus,
    IMChannelType,
    PairingRequest,
    PairingStatus,
)

__all__ = [
    "IMChannel",
    "IMChannelType",
    "IMChannelStatus",
    "IMBinding",
    "PairingRequest",
    "PairingStatus",
]
