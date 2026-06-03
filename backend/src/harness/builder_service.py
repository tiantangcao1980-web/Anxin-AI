# -*- coding: utf-8 -*-
"""
CREAO 自愈闭环 Slice 3 — Builder Service (A9, 2026-05-14)

Slice 2 已经把 incidents 聚类、写入 triage_summary 并转为 triaged 状态.
Slice 3 拿一个 cluster (或单条 triaged incident) 做两件事:

1. 生成回归测试草稿 (build_regression_test_draft):
   - 给一段 pytest 文件骨架 + 注释化的 trace_id / payload 引用
   - 草稿不立即落库 / 不自动 commit, 仅返回字符串给前端 admin 审核
   - 通过 admin 一键复制到 backend/tests/auto/ 后, 由人工补全 assertion

2. 生成 GitHub Issue 草稿 (build_github_issue_draft):
   - title: "[CREAO][P{severity}] {summary}"
   - body: cluster 概览 + 关联 incident 列表 + reproduce 步骤建议
   - 同样仅返回草稿字符串 + 可选关联到 incident.github_issue_url

设计:
   - Builder 全部输出"草稿" + admin 人工 gate, 与 audit 原话 "Builder + 人工 gate" 一致
   - 不直接调 GitHub API (避免凭证 / 误开 issue 风险), 留出 webhook 钩子位
   - LLM 总结放到 Slice 3.5 (可选), 当前是确定性模板
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.incident import Incident


def _slug(text: str, max_len: int = 40) -> str:
    """安全地把任意字符串转成 pytest 函数名可用的 snake_case。"""
    import re

    out = re.sub(r"[^a-zA-Z0-9_一-鿿]+", "_", text)
    out = re.sub(r"_+", "_", out).strip("_").lower()
    return out[:max_len] or "unknown"


def _build_test_function_name(incident: Incident) -> str:
    src = _slug(incident.source or "unknown")
    agent = _slug(incident.agent_name or "any") if incident.agent_name else "any"
    # incident.id 在内存对象上可能未生成, 用 fingerprint 兜底
    suffix = (str(incident.id) if incident.id else (incident.fingerprint or "xxxxxxxx"))[:8]
    return f"test_regression_{src}_{agent}_{suffix}"


def build_regression_test_draft(incident: Incident) -> str:
    """返回 pytest 测试草稿字符串. 不写盘, 由 admin 复制。"""
    fn_name = _build_test_function_name(incident)
    when = (incident.first_seen_at or datetime.now(UTC)).isoformat()
    payload_snippet = str(incident.payload)[:400].replace('"""', '\\"\\"\\"')
    return f"""# -*- coding: utf-8 -*-
\"\"\"
回归测试草稿 (CREAO Slice 3, 自动生成 {datetime.now(UTC).isoformat()})

  源 incident: {incident.id}
  首次出现:   {when}
  来源:       {incident.source}
  严重度:     {incident.severity}
  agent:      {incident.agent_name or '-'}
  route:      {incident.route or '-'}
  指纹:       {incident.fingerprint}

  triage_summary: {incident.triage_summary or '(未运行 Slice 2)'}

由 admin 审核后补全 assertion, 移入 backend/tests/auto/.
\"\"\"

import pytest


@pytest.mark.regression
@pytest.mark.creao_slice3
def {fn_name}():
    \"\"\"
    复现条件 (来自 incident.payload):
{payload_snippet}

    TODO (人工 gate):
      1. 用 payload 中关键字段重建调用上下文
      2. 写出预期行为 assertion
      3. 删除 pytest.skip 后提交
    \"\"\"
    pytest.skip("CREAO Slice 3 草稿, 待人工补全 assertion 后启用")
"""


def build_github_issue_draft(
    incident: Incident,
    *,
    repo_full_name: str = "anxin-ai/anxin-assistant",
) -> dict[str, str]:
    """返回 GitHub Issue 草稿 (title + body), 不调 GitHub API."""
    title = f"[CREAO][{incident.severity}] {incident.source}: {incident.title[:80]}"
    when = (incident.first_seen_at or datetime.now(UTC)).isoformat()
    last_when = (incident.last_seen_at or datetime.now(UTC)).isoformat()
    body = (
        f"## CREAO 自愈闭环 Slice 3 自动生成草稿\n\n"
        f"- **incident id**: `{incident.id}`\n"
        f"- **首次出现**: {when}\n"
        f"- **最近出现**: {last_when}\n"
        f"- **来源**: {incident.source}\n"
        f"- **严重度**: {incident.severity}\n"
        f"- **agent**: {incident.agent_name or '-'}\n"
        f"- **route**: {incident.route or '-'}\n"
        f"- **fingerprint**: `{incident.fingerprint}`\n"
        f"- **occurrence_count**: {incident.occurrence_count}\n\n"
        f"### Triage 总结\n\n"
        f"> {incident.triage_summary or '(未运行 Slice 2)'}\n\n"
        f"### Payload (已脱敏)\n\n"
        f"```json\n{incident.payload}\n```\n\n"
        f"### 复现建议\n\n"
        f"1. 用 payload 中的 user_query / route / agent_name 重建调用上下文\n"
        f"2. 检查 trace_id 关联的完整请求链\n"
        f"3. 必要时回放 fingerprint 相同的旧 incident 验证\n\n"
        f"---\n"
        f"_Issue 草稿由 admin 审核后通过 `gh issue create --repo {repo_full_name} ...` 提交._\n"
    )
    return {"title": title, "body": body, "repo": repo_full_name}


async def build_drafts_for_incident(
    db: AsyncSession,
    incident_id: str,
    *,
    repo_full_name: str = "anxin-ai/anxin-assistant",
) -> dict[str, Any]:
    """为指定 incident 同时返回两份草稿 + 元信息."""
    try:
        result = await db.execute(select(Incident).where(Incident.id == incident_id))
        incident = result.scalar_one_or_none()
    except Exception as exc:
        # id 格式非法 (e.g. 非 UUID 字符串) — DB 层会抛 StatementError
        return {"error": f"invalid incident id {incident_id!r}: {exc}"}
    if incident is None:
        return {"error": f"incident {incident_id} not found"}

    return {
        "incident_id": incident_id,
        "severity": incident.severity,
        "source": incident.source,
        "regression_test_draft": build_regression_test_draft(incident),
        "github_issue_draft": build_github_issue_draft(incident, repo_full_name=repo_full_name),
        "generated_at": datetime.now(UTC).isoformat(),
    }


async def link_github_issue(
    db: AsyncSession,
    incident_id: str,
    issue_url: str,
) -> dict[str, Any]:
    """人工提交 issue 后, 回填 github_issue_url 字段并把 incident 转为 linked 状态。"""
    try:
        result = await db.execute(select(Incident).where(Incident.id == incident_id))
        incident = result.scalar_one_or_none()
    except Exception as exc:
        return {"ok": False, "error": f"invalid incident id {incident_id!r}: {exc}"}
    if incident is None:
        return {"ok": False, "error": f"incident {incident_id} not found"}

    incident.github_issue_url = issue_url
    if incident.status in {"open", "triaged"}:
        incident.status = "linked"
    await db.flush()
    logger.info(f"[Builder] linked incident {incident_id} → {issue_url}")
    return {"ok": True, "incident_id": incident_id, "status": incident.status}
