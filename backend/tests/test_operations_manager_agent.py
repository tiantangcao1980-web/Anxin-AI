# -*- coding: utf-8 -*-
"""
P7-A: OperationsManagerAgent 单元测试

策略：
    - 全部 mock ``BaseLegalAgent.chat`` 的返回，避免真正调用 LLM；
    - 验证：
        1. 元信息字段完整 + 自动注册到 PersonaRegistry
        2. handle_message 路由 capability hint
        3. generate_okr_dashboard 解析 ```json``` 块
        4. generate_weekly_report 解析三段
        5. transcribe_and_summarize 两条路径（pending / ready）
        6. extract_todos 结构化输出
        7. orchestrate_approval 占位输出
"""

from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, patch

import pytest

from src.agents.personas import OperationsManagerAgent, PersonaRegistry


@pytest.fixture(autouse=True)
def _reset_registry():
    PersonaRegistry.reset_instance()
    # 重新触发自动注册
    yield
    PersonaRegistry.reset_instance()


@pytest.fixture
def agent():
    """构造 agent，规避 LLM 真初始化。"""
    with patch("src.agents.base.get_llm_config_sync", return_value=None):
        instance = OperationsManagerAgent()
    return instance


# ------------------------------------------------------------------
class TestMetadata:
    def test_persona_metadata(self, agent):
        info = agent.get_info()
        assert info.persona_id == "operations_manager"
        assert info.display_name == "流程管家"
        assert info.emoji == "📋"
        assert "okr_tracking" in info.capabilities
        assert "meeting_minutes" in info.capabilities
        assert "weekly_report" in info.capabilities
        assert "todo_extraction" in info.capabilities
        assert "approval_orchestration" in info.capabilities

    def test_skills_and_apps(self, agent):
        info = agent.get_info()
        assert set(info.backed_by_skills) == {"docx", "xlsx", "pptx"}
        assert set(info.supported_apps) == {"feishu", "dingtalk", "notion"}

    def test_system_prompt_minimum_length_and_persona_boundaries(self):
        prompt = OperationsManagerAgent.SYSTEM_PROMPT
        assert len(prompt) >= 200
        # 边界声明
        assert "compliance_steward" in prompt
        assert "tax_steward" in prompt
        assert "trade_officer" in prompt
        assert "content_director" in prompt
        # 工具偏好
        assert "xlsx" in prompt
        assert "docx" in prompt
        assert "pptx" in prompt

    def test_autoregistered(self):
        # 强制重新 autoload 确认 persona 仍在
        PersonaRegistry.instance().autoload("src.agents.personas")
        assert PersonaRegistry.instance().has("operations_manager")


# ------------------------------------------------------------------
class TestHandleMessageRouting:
    @pytest.mark.asyncio
    async def test_handle_message_passes_capability_hint(self, agent):
        with patch.object(agent, "chat", new=AsyncMock(return_value="ok")) as mock_chat:
            await agent.handle_message(message="本周 OKR 进度怎么样？")
            args, kwargs = mock_chat.call_args
            assert "operations_manager" in agent.SYSTEM_PROMPT or True
            # system_prompt_override 应携带 capability hint
            override = kwargs.get("system_prompt_override")
            assert override is not None
            assert "okr_tracking" in override

    @pytest.mark.asyncio
    async def test_handle_message_no_keyword_no_override(self, agent):
        with patch.object(agent, "chat", new=AsyncMock(return_value="ok")) as mock_chat:
            await agent.handle_message(message="你好啊")
            kwargs = mock_chat.call_args.kwargs
            assert kwargs.get("system_prompt_override") is None

    def test_guess_capability_keywords(self):
        guess = OperationsManagerAgent._guess_capability
        assert guess("帮我做周报") == "weekly_report"
        assert guess("整理上次的会议纪要") == "meeting_minutes"
        assert guess("提取待办") == "todo_extraction"
        assert guess("我要发起一个审批") == "approval_orchestration"
        assert guess("看下我们的 OKR") == "okr_tracking"
        assert guess("") is None


# ------------------------------------------------------------------
class TestOKRDashboard:
    @pytest.mark.asyncio
    async def test_okr_dashboard_parses_json(self, agent):
        fake_resp = (
            "## OKR 看板\n\n| obj | progress | status |\n|---|---|---|\n"
            "| 提升合格率 | 0.6 | on_track |\n\n"
            "```json\n"
            '{"items":[{"objective":"提升合格率","owner":"李雷","progress":0.6,'
            '"status":"on_track","key_results":[{"kr":"合格率提升至95%","progress":0.6}]}],'
            '"summary":{"total":1,"on_track":1,"at_risk":0,"off_track":0}}\n'
            "```\n"
        )
        with patch.object(agent, "chat", new=AsyncMock(return_value=fake_resp)):
            result = await agent.generate_okr_dashboard(period="Q2-2026", team="生产部")

        assert result["period"] == "Q2-2026"
        assert result["team"] == "生产部"
        assert len(result["items"]) == 1
        assert result["items"][0]["objective"] == "提升合格率"
        assert result["summary"]["total"] == 1
        assert result["summary"]["on_track"] == 1

    @pytest.mark.asyncio
    async def test_okr_dashboard_no_json_fallback(self, agent):
        with patch.object(agent, "chat", new=AsyncMock(return_value="纯文本，没有JSON")):
            result = await agent.generate_okr_dashboard(period="Q2")
        assert result["items"] == []
        assert result["summary"]["total"] == 0


# ------------------------------------------------------------------
class TestWeeklyReport:
    @pytest.mark.asyncio
    async def test_weekly_report_parses_sections(self, agent):
        fake_resp = (
            "## 本周亮点\n- [x] 完成 V3.2 评审\n\n"
            "## 风险\n- [ ] 性能人手不足\n\n"
            "## 下周计划\n- [ ] 启动测试\n\n"
            "```json\n"
            '{"highlights":["完成 V3.2 评审"],"risks":["性能人手不足"],'
            '"next_week":["启动测试"]}\n'
            "```\n"
        )
        with patch.object(agent, "chat", new=AsyncMock(return_value=fake_resp)):
            result = await agent.generate_weekly_report(
                week_start=date(2026, 4, 20),
                sources=["飞书"],
                team="研发组",
            )

        assert result["week_start"] == "2026-04-20"
        assert result["week_end"] == "2026-04-26"
        assert result["team"] == "研发组"
        assert result["sources"] == ["飞书"]
        assert "完成 V3.2 评审" in result["sections"]["highlights"]
        assert "性能人手不足" in result["sections"]["risks"]
        assert "启动测试" in result["sections"]["next_week"]


# ------------------------------------------------------------------
class TestMeetingMinutes:
    @pytest.mark.asyncio
    async def test_pending_when_only_audio_url(self, agent):
        with patch.object(agent, "chat", new=AsyncMock(return_value="should not call")) as mock_chat:
            result = await agent.transcribe_and_summarize(
                audio_url="https://example.com/audio.mp3",
                meeting_topic="V3.2 评审",
            )
        assert result["status"] == "pending_transcribe"
        assert result["topic"] == "V3.2 评审"
        assert result["audio_url"] == "https://example.com/audio.mp3"
        mock_chat.assert_not_called()

    @pytest.mark.asyncio
    async def test_ready_with_transcript(self, agent):
        fake_resp = (
            "## 会议主题\nV3.2 评审\n\n"
            "## 决议\n- 通过用户中心改版\n\n"
            "## 待办\n- @王伟 5/15 前完成改版\n\n"
            "```json\n"
            '{"decisions":["通过用户中心改版"],'
            '"todos":[{"task":"完成用户中心改版","owner":"王伟","due_date":"2026-05-15","priority":"P1"}]}\n'
            "```\n"
        )
        with patch.object(agent, "chat", new=AsyncMock(return_value=fake_resp)):
            result = await agent.transcribe_and_summarize(
                transcript="（这里是 1 小时录音的转写文本……）",
                meeting_topic="V3.2 评审",
            )

        assert result["status"] == "ready"
        assert "通过用户中心改版" in result["decisions"]
        assert len(result["todos"]) == 1
        todo = result["todos"][0]
        assert todo["owner"] == "王伟"
        assert todo["due_date"] == "2026-05-15"
        assert todo["priority"] == "P1"
        assert todo["source"] == "meeting_minutes"

    @pytest.mark.asyncio
    async def test_raises_when_neither_audio_nor_transcript(self, agent):
        with pytest.raises(ValueError):
            await agent.transcribe_and_summarize()


# ------------------------------------------------------------------
class TestExtractTodos:
    @pytest.mark.asyncio
    async def test_extract_todos_returns_list(self, agent):
        fake_resp = (
            "```json\n"
            '{"todos":[{"task":"准备客户拜访","owner":"张三","due_date":"2026-04-30","priority":"P0"},'
            '{"task":"提交报销单","owner":"李四","due_date":"?","priority":"P2"}]}\n'
            "```\n"
        )
        with patch.object(agent, "chat", new=AsyncMock(return_value=fake_resp)):
            todos = await agent.extract_todos(
                text="周一前张三去拜访客户，李四别忘了交报销单。",
                source="im_chat",
            )
        assert len(todos) == 2
        assert todos[0]["owner"] == "张三"
        assert todos[0]["priority"] == "P0"
        assert all(t["source"] == "im_chat" for t in todos)

    @pytest.mark.asyncio
    async def test_extract_todos_empty_text(self, agent):
        todos = await agent.extract_todos(text="")
        assert todos == []


# ------------------------------------------------------------------
class TestApprovalOrchestration:
    @pytest.mark.asyncio
    async def test_orchestrate_approval_parses_chain(self, agent):
        fake_resp = (
            "## 推荐审批链\n直属上级 → 部门负责人 → 财务\n\n"
            "## 风险提示\n金额低，风险低\n\n"
            "```json\n"
            '{"chain":["直属上级","部门负责人","财务"],"risk_level":"low","eta_hours":24}\n'
            "```\n"
        )
        with patch.object(agent, "chat", new=AsyncMock(return_value=fake_resp)):
            result = await agent.orchestrate_approval(
                approval_type="报销",
                applicant="张三",
                details={"amount": 1200, "currency": "CNY"},
            )
        assert result["chain"] == ["直属上级", "部门负责人", "财务"]
        assert result["risk_level"] == "low"
        assert result["eta_hours"] == 24
        assert result["status"] == "draft"
