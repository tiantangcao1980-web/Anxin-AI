"""merge 030_app_authorization head with 044_skill_connector_configs

Revision ID: 045_merge_030_044
Revises: 030_app_authorization, 044_skill_connector_configs
Create Date: 2026-05-14

为什么需要这个 merge migration:
  自 028_agent_tasks → 029_im_gateway → 030_app_authorization 分支以来,
  主线沿 028_password_reset → 030_webhook_received → ... → 044 一路演进,
  两条 chain 共享 029 之前的 ancestor 但之后从未合并.

  这导致 `alembic heads` 显示 2 个并行 head, 任何新 migration 必须显式
  指明 down_revision 是哪个 head; 单 head 假设的代码 (含 CI / startup
  alembic upgrade head) 也无法工作.

  本 migration 不改 schema, 仅在 alembic_version 历史中把两个 head
  合并成一个新 head 045_merge_030_044, 后续 migration 可直接依赖它.

  P5 followup (T5 peaceful-goodall CREAO Slice 1 合并) 现在可以以此为基线.
"""

from collections.abc import Sequence

revision: str = "045_merge_030_044"
down_revision: tuple[str, ...] = (
    "030_app_authorization",
    "044_skill_connector_configs",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """两个 head 在此汇合; 无 schema 变更。"""
    pass


def downgrade() -> None:
    """回退本 merge 只需保留两个原 head 即可; 无 schema 变更。"""
    pass
