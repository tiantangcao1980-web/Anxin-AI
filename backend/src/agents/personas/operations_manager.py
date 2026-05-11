# -*- coding: utf-8 -*-
"""
OperationsManagerAgent —— 流程管家 persona（P7-A）

定位：制造业 / 中型团队的「OKR / 审批流 / 会议纪要 / 周报」自动化大脑。

核心能力（capability_*）：
    - okr_tracking          : OKR 拉数据 + 进度看板
    - approval_orchestration: 审批流编排（占位，后续接 OA）
    - meeting_minutes       : 会议录音 → 转写 → 提炼要点 + 待办
    - weekly_report         : 多源聚合周报 / 月报 (xlsx + pptx)
    - todo_extraction       : 自由文本 → 结构化待办清单

技能依赖（backed_by_skills）：
    - office/docx  → 会议纪要
    - office/xlsx  → OKR 表 / 周报数据表
    - office/pptx  → 周报 / 月报 演示稿

应用授权（supported_apps）：
    - feishu / dingtalk / notion （由 ``app_authorizations`` 服务提供 OAuth token，
      此处仅声明依赖，不直接调用 OA SDK 以保持 P7-A 范围内不动 IM 网关层。）
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from loguru import logger

from src.agents.personas.base_persona import BasePersonaAgent


SYSTEM_PROMPT = """你是「流程管家」，制造业团队的 OKR / 审批流 / 会议纪要 / 周报 自动化助理。

## 你的角色
- 你不是法务、税务、跨境电商 persona —— 那些工作分别交给 `compliance_steward` / `tax_steward` / `trade_officer`。
- 你的核心服务对象是：制造业中层管理者 / 部门负责人 / 经营助理 / HRBP。
- 你优先帮用户 **省时间**：把分散在飞书 / 钉钉 / 日历 / Notion 里的过程数据汇总、归档、提醒。

## 核心能力（清晰列出）
1. **OKR 跟踪 (okr_tracking)** — 制定 / 拆解 / 跟进 / 复盘；优先用 *xlsx* 表格输出。
2. **审批流编排 (approval_orchestration)** — 报销 / 请假 / 采购 智能审批 + 异常预警。
3. **会议纪要 (meeting_minutes)** — 录音转写 → 决议 / 行动项；输出 *docx* 纪要。
4. **周报 / 月报 (weekly_report)** — OKR + 飞书 + 日历 多源聚合；首选 *pptx* 演示稿。
5. **待办提取 (todo_extraction)** — 从任意文本自动抽取 `{owner, task, due, priority}`，结构化交付。

## 工具 / 技能调用偏好
| 输出场景 | 首选 skill | 备选 |
|---------|-----------|------|
| OKR 表 / 进度跟踪 | `office/xlsx` | `office/docx` |
| 会议纪要 / 待办清单 | `office/docx` | markdown |
| 周报 / 月报 / 述职 | `office/pptx` | `office/docx` |
| 财务 / 多 sheet 数据汇总 | `office/xlsx` | — |

## 与其他 persona 的边界（必须严守，避免越权）
- 涉及 **法律 / 合同 / 合规风险** → 让用户去找「合规管家」(`compliance_steward`)，你只汇报流程进度。
- 涉及 **税务 / 发票 / 增值税** → 让用户去找「财税管家」(`tax_steward`)。
- 涉及 **跨境电商 / 关务 / 退税** → 让用户去找「出海贸易官」(`trade_officer`)。
- 涉及 **品牌 / 内容创作 / 公众号** → 让用户去找「内容总监」(`content_director`)。
- 涉及 **客户合同起草 / NDA** → 让用户去找「文档秘书」(`doc_secretary`)。
- 你只在「过程管理」「数据汇总」「待办分发」这一层工作。

## 输出风格
- **优先 markdown**：列表、表格、可勾选 checklist (`- [ ]` / `- [x]`)。
- 关键数字必须用表格呈现，不口述。
- 不确定的事实（用户未提供）一律标 `?`，不要编造。
- 涉及具体人员 / 公司名时，用 `@姓名` / `《公司》` 包裹，便于后续解析。
- 输出 JSON 时必须放在 ```json``` 代码块中，方便 API 层 parse。

## 行动原则
1. 先确认 **时间窗口**（"本周" / "Q2" / "4/22 那次会议" 等），再聚合数据。
2. 多源数据冲突时，标注来源并请求用户裁决，不要私自合并。
3. 待办项必须包含 owner + due_date，否则提示用户补全。
4. 涉及自动发送（周报群 / 飞书群）时，**最后一步必须等用户确认**。
"""


# ------------------------------------------------------------------
# 内部数据结构（轻量，不入库）
# ------------------------------------------------------------------
@dataclass(slots=True)
class OkrItem:
    objective: str
    owner: str = ""
    progress: float = 0.0  # 0~1
    key_results: List[Dict[str, Any]] = field(default_factory=list)
    status: str = "on_track"  # on_track / at_risk / off_track / done


@dataclass(slots=True)
class TodoItem:
    task: str
    owner: str = "?"
    due_date: str = "?"
    priority: str = "P2"  # P0 / P1 / P2 / P3
    source: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task": self.task,
            "owner": self.owner,
            "due_date": self.due_date,
            "priority": self.priority,
            "source": self.source,
        }


# ------------------------------------------------------------------
# Persona 主体
# ------------------------------------------------------------------
class OperationsManagerAgent(BasePersonaAgent):
    """流程管家 persona agent（P7-A）。"""

    persona_id = "operations_manager"
    display_name = "流程管家"
    emoji = "📋"
    description = "OKR / 审批 / 会议纪要 / 周报 自动化大脑（制造业团队过程管理）"

    backed_by_skills = ["docx", "xlsx", "pptx"]
    supported_apps = ["feishu", "dingtalk", "notion"]
    capabilities = [
        "okr_tracking",
        "approval_orchestration",
        "meeting_minutes",
        "weekly_report",
        "todo_extraction",
    ]
    backed_by_agents = ["requirement_analyst", "coordinator"]

    SYSTEM_PROMPT = SYSTEM_PROMPT

    # ------------------------------------------------------------------
    # handle_message —— 对外主入口（覆盖 BasePersonaAgent 默认实现，
    # 增加轻量 capability 路由 hint）
    # ------------------------------------------------------------------
    async def handle_message(
        self,
        message: str,
        user_id: Optional[str] = None,
        llm_config: Optional[Any] = None,
        history: Optional[List[Dict[str, Any]]] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> str:
        capability_hint = self._guess_capability(message)
        prompt_override: Optional[str] = None
        if capability_hint:
            prompt_override = (
                self.SYSTEM_PROMPT
                + f"\n\n## 当前用户意图（系统识别）\n- capability: {capability_hint}"
            )
        return await self.chat(
            message=message,
            user_id=user_id,
            llm_config=llm_config,
            system_prompt_override=prompt_override,
            history=history,
        )

    @staticmethod
    def _guess_capability(message: str) -> Optional[str]:
        """简单关键词路由（仅给 LLM 一个 hint，不强制）。"""
        if not message:
            return None
        msg = message.lower()
        rules = [
            ("okr_tracking", ["okr", "kr", "关键结果", "目标进度"]),
            ("meeting_minutes", ["会议纪要", "纪要", "录音", "转写", "会议记录"]),
            ("weekly_report", ["周报", "月报", "述职", "经营报告"]),
            ("approval_orchestration", ["审批", "报销", "请假", "采购"]),
            ("todo_extraction", ["待办", "todo", "行动项", "任务列表"]),
        ]
        for cap, keys in rules:
            if any(k.lower() in msg for k in keys):
                return cap
        return None

    # ------------------------------------------------------------------
    # capability 1: OKR 看板
    # ------------------------------------------------------------------
    async def generate_okr_dashboard(
        self,
        period: str,
        team: Optional[str] = None,
        user_id: Optional[str] = None,
        llm_config: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """生成 OKR 看板 markdown + 结构化数据。

        返回::
            {
                "period": "Q2-2026",
                "team": "...",
                "markdown": "## ...",
                "items": [ { objective, owner, progress, status, key_results } ],
                "summary": { "total": int, "on_track": int, "at_risk": int, "off_track": int },
            }
        """
        prompt = (
            f"请生成 {period} 期间"
            + (f" {team} 团队" if team else "")
            + " 的 OKR 看板。\n\n"
            "格式要求：\n"
            "1. 先输出 markdown 表格（objective / owner / progress / status）。\n"
            "2. 然后输出一段 ```json``` 代码块，结构如下：\n"
            "   ```json\n"
            '   {"items":[{"objective":"...","owner":"...","progress":0.6,'
            '"status":"on_track","key_results":[{"kr":"...","progress":0.5}]}],'
            '"summary":{"total":3,"on_track":2,"at_risk":1,"off_track":0}}\n'
            "   ```\n"
            "3. 若用户尚未导入 OKR 数据，请在 markdown 顶部用 `> 提示：` 注明，"
            "并以 mock 示例填充 items（status 字段必须是 on_track/at_risk/off_track/done 之一）。"
        )
        content = await self.chat(
            message=prompt,
            user_id=user_id,
            llm_config=llm_config,
        )
        items, summary = self._parse_okr_payload(content)
        return {
            "period": period,
            "team": team,
            "markdown": content,
            "items": items,
            "summary": summary,
        }

    @staticmethod
    def _parse_okr_payload(text: str) -> tuple[List[Dict[str, Any]], Dict[str, int]]:
        """从 LLM 返回中抽取 ```json``` 块。失败时返回空。"""
        items: List[Dict[str, Any]] = []
        summary: Dict[str, int] = {"total": 0, "on_track": 0, "at_risk": 0, "off_track": 0}
        if not text:
            return items, summary
        match = re.search(r"```json\s*(.+?)```", text, re.DOTALL)
        if not match:
            return items, summary
        try:
            data = json.loads(match.group(1).strip())
            raw_items = data.get("items") or []
            if isinstance(raw_items, list):
                items = [item for item in raw_items if isinstance(item, dict)]
            raw_summary = data.get("summary") or {}
            if isinstance(raw_summary, dict):
                for k in summary:
                    v = raw_summary.get(k)
                    if isinstance(v, int):
                        summary[k] = v
            if not summary["total"] and items:
                summary["total"] = len(items)
        except json.JSONDecodeError as exc:
            logger.warning(f"OKR payload 解析失败: {exc}")
        return items, summary

    # ------------------------------------------------------------------
    # capability 2: 周报生成
    # ------------------------------------------------------------------
    async def generate_weekly_report(
        self,
        week_start: date,
        sources: Optional[List[str]] = None,
        team: Optional[str] = None,
        user_id: Optional[str] = None,
        llm_config: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """生成周报草稿。

        返回::
            {
                "week_start": "2026-04-20",
                "week_end":   "2026-04-26",
                "team":       ...,
                "sources":    ["feishu","dingtalk"],
                "markdown":   "...",
                "sections":   {"highlights": [...], "risks": [...], "next_week": [...]},
            }

        说明：
            - 生成的是 **markdown 草稿** + 结构化 sections，
              真正落 pptx 文件由调用方走 ``skill_executor.execute("pptx", ...)``，
              本方法不直接产出二进制（保持 persona 与 skill 解耦）。
        """
        sources = sources or ["飞书", "钉钉", "日历"]
        week_end = week_start + timedelta(days=6)
        sources_text = "、".join(sources)
        team_text = f" {team} 团队" if team else ""
        prompt = (
            f"请基于 {sources_text} 数据，为{team_text} {week_start} ~ {week_end} 周起草本周周报。\n\n"
            "输出要求：\n"
            "1. markdown 三段：## 本周亮点 / ## 风险 求助 / ## 下周计划\n"
            "2. 每段用 `- [x]` / `- [ ]` 形式列条目，关键数字加粗\n"
            "3. 末尾追加一个 ```json``` 块：\n"
            "   ```json\n"
            '   {"highlights":["..."],"risks":["..."],"next_week":["..."]}\n'
            "   ```\n"
            "4. 如缺数据，明示 `?` 而非编造，并在末尾问用户是否需要补充。"
        )
        content = await self.chat(
            message=prompt,
            user_id=user_id,
            llm_config=llm_config,
        )
        sections = self._parse_weekly_sections(content)
        return {
            "week_start": week_start.isoformat(),
            "week_end": week_end.isoformat(),
            "team": team,
            "sources": sources,
            "markdown": content,
            "sections": sections,
        }

    @staticmethod
    def _parse_weekly_sections(text: str) -> Dict[str, List[str]]:
        result: Dict[str, List[str]] = {"highlights": [], "risks": [], "next_week": []}
        if not text:
            return result
        match = re.search(r"```json\s*(.+?)```", text, re.DOTALL)
        if not match:
            return result
        try:
            data = json.loads(match.group(1).strip())
            for k in result:
                v = data.get(k)
                if isinstance(v, list):
                    result[k] = [str(x) for x in v if x]
        except json.JSONDecodeError:
            return result
        return result

    # ------------------------------------------------------------------
    # capability 3: 会议纪要（转写 + 摘要）
    # ------------------------------------------------------------------
    async def transcribe_and_summarize(
        self,
        audio_url: Optional[str] = None,
        transcript: Optional[str] = None,
        meeting_topic: Optional[str] = None,
        user_id: Optional[str] = None,
        llm_config: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """会议录音转写 + 摘要。

        参数二选一：
            - audio_url   : 音频 URL（P7-A 阶段先标记为 `pending`，由后续 P7-A.1
                            接入 ASR 后真正调用；当前仅占位返回 status）
            - transcript  : 已经有的转写文本，直接走摘要

        返回::
            {
                "status": "ready" | "pending_transcribe",
                "topic": "...",
                "transcript_excerpt": "...",
                "summary_markdown": "...",
                "decisions": [...],
                "todos": [TodoItem.to_dict(), ...],
            }
        """
        if not audio_url and not transcript:
            raise ValueError("必须提供 audio_url 或 transcript 之一")

        # 暂未接入 ASR：audio_url 仅 transcript 为空时返回 pending
        if not transcript:
            return {
                "status": "pending_transcribe",
                "topic": meeting_topic or "?",
                "transcript_excerpt": "",
                "summary_markdown": (
                    f"> 已收到音频 `{audio_url}`，转写服务尚未接入（P7-A.1 阶段交付）。"
                ),
                "decisions": [],
                "todos": [],
                "audio_url": audio_url,
            }

        prompt = (
            "请基于下面的会议转写，整理一份会议纪要。\n\n"
            f"会议主题：{meeting_topic or '?'}\n\n"
            "## 转写原文\n"
            f"{transcript[:8000]}\n\n"
            "输出要求：\n"
            "1. markdown 段落：**会议主题** / **决议** / **待办** / **下次会议**\n"
            "2. 待办项必须含 `owner` + `due_date`，缺失用 `?` 占位\n"
            "3. 末尾追加 ```json``` 块：\n"
            "   ```json\n"
            '   {"decisions":["..."],"todos":[{"task":"...","owner":"...","due_date":"...","priority":"P1"}]}\n'
            "   ```"
        )
        content = await self.chat(
            message=prompt,
            user_id=user_id,
            llm_config=llm_config,
        )
        decisions, todos = self._parse_minutes_payload(content)
        return {
            "status": "ready",
            "topic": meeting_topic or "?",
            "transcript_excerpt": (transcript or "")[:500],
            "summary_markdown": content,
            "decisions": decisions,
            "todos": [t.to_dict() for t in todos],
        }

    @staticmethod
    def _parse_minutes_payload(text: str) -> tuple[List[str], List[TodoItem]]:
        decisions: List[str] = []
        todos: List[TodoItem] = []
        if not text:
            return decisions, todos
        match = re.search(r"```json\s*(.+?)```", text, re.DOTALL)
        if not match:
            return decisions, todos
        try:
            data = json.loads(match.group(1).strip())
            raw_dec = data.get("decisions") or []
            decisions = [str(x) for x in raw_dec if x]
            for item in data.get("todos") or []:
                if not isinstance(item, dict):
                    continue
                todos.append(
                    TodoItem(
                        task=str(item.get("task", "")).strip(),
                        owner=str(item.get("owner", "?")),
                        due_date=str(item.get("due_date", "?")),
                        priority=str(item.get("priority", "P2")).upper(),
                        source="meeting_minutes",
                    )
                )
        except json.JSONDecodeError:
            return decisions, todos
        return decisions, todos

    # ------------------------------------------------------------------
    # capability 4: 待办提取
    # ------------------------------------------------------------------
    async def extract_todos(
        self,
        text: str,
        source: str = "free_text",
        user_id: Optional[str] = None,
        llm_config: Optional[Any] = None,
    ) -> List[Dict[str, Any]]:
        """从任意文本抽取结构化待办列表。"""
        if not text or not text.strip():
            return []
        prompt = (
            "请从下面文本中抽取所有「待办事项」，每条必须包含 task / owner / due_date / priority。\n"
            "缺失字段用 `?` 占位，priority 取值范围 P0/P1/P2/P3。\n"
            "**只输出 ```json``` 代码块**，不要额外说明。结构：\n"
            "```json\n"
            '{"todos":[{"task":"...","owner":"...","due_date":"...","priority":"P1"}]}\n'
            "```\n\n"
            "## 待解析文本\n"
            f"{text[:6000]}"
        )
        content = await self.chat(
            message=prompt,
            user_id=user_id,
            llm_config=llm_config,
        )
        _, todos = self._parse_minutes_payload(content)
        # source 覆盖
        return [{**t.to_dict(), "source": source} for t in todos]

    # ------------------------------------------------------------------
    # capability 5: 审批流编排（P7-A 占位，等 OA 接入）
    # ------------------------------------------------------------------
    async def orchestrate_approval(
        self,
        approval_type: str,
        applicant: str,
        details: Dict[str, Any],
        user_id: Optional[str] = None,
        llm_config: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """审批流编排（占位实现）。

        P7-A 阶段：返回 LLM 推荐的审批路径 + 风险提示，
        实际审批动作由 P7-A.2 接入 OA SDK 后落地。
        """
        prompt = (
            "你是流程管家。请为下列审批申请推荐一条审批链路 + 风险提示。\n\n"
            f"- 类型：{approval_type}\n"
            f"- 申请人：{applicant}\n"
            f"- 详情：{json.dumps(details, ensure_ascii=False)}\n\n"
            "输出格式：\n"
            "1. markdown：**推荐审批链** / **风险提示** / **预计时长**\n"
            "2. 末尾 ```json``` 块：\n"
            "   ```json\n"
            '   {"chain":["直属上级","部门负责人","财务"],"risk_level":"low","eta_hours":24}\n'
            "   ```"
        )
        content = await self.chat(
            message=prompt,
            user_id=user_id,
            llm_config=llm_config,
        )
        chain: List[str] = []
        risk_level = "low"
        eta_hours = 0
        match = re.search(r"```json\s*(.+?)```", content, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(1).strip())
                if isinstance(data.get("chain"), list):
                    chain = [str(x) for x in data["chain"] if x]
                if isinstance(data.get("risk_level"), str):
                    risk_level = data["risk_level"]
                if isinstance(data.get("eta_hours"), (int, float)):
                    eta_hours = int(data["eta_hours"])
            except json.JSONDecodeError:
                pass
        return {
            "approval_type": approval_type,
            "applicant": applicant,
            "chain": chain,
            "risk_level": risk_level,
            "eta_hours": eta_hours,
            "markdown": content,
            "status": "draft",  # 真正提交需走 OA SDK
        }
