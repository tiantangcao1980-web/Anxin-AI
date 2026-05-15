"""
IM 配对授权子模块（P3-B）

提供"用户在 IM 渠道 @bot 触发配对 → 管理员 24h 内审批 / 过期失效"
的完整业务闭环。

主要导出：
    - ``PairingService``        : 业务服务门面（create / approve / reject / list / cleanup）
    - ``cleanup_expired_pairing_requests`` : Celery beat 周期任务
"""

from src.services.im_gateway.pairing.service import PairingService

__all__ = [
    "PairingService",
]
