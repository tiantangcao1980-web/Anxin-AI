"""
Harness Engineering 模块测试

覆盖：
1. 分级完整性门槛
2. 多轮追问 reassess
3. 模板请求意图识别
4. 输出验证器
5. 成本追踪
6. 权限检查
7. 任务状态机
8. 能力协商
"""

import asyncio
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


# ===== 1. 分级完整性门槛 =====

class TestCompletenessThresholds:
    """测试分级完整性门槛"""

    def test_document_drafting_blocks_on_empty_input(self):
        """文书起草场景：空输入必须拦截"""
        from src.services.scenario_templates import assess_completeness
        result = assess_completeness('帮我起草一份合同', 'DOCUMENT_DRAFTING')
        assert not result['is_complete'], "文书起草无具体信息不应放行"
        assert result['score'] < 0.75
        assert len(result['questions']) > 0

    def test_qa_consultation_passes_easily(self):
        """法律咨询：低门槛，直接放行"""
        from src.services.scenario_templates import assess_completeness
        result = assess_completeness('劳动法规定试用期最长多久？', 'QA_CONSULTATION')
        assert result['is_complete'], "法律咨询应该直接放行"

    def test_labor_hr_with_info_passes(self):
        """劳动人事：有信息时放行"""
        from src.services.scenario_templates import assess_completeness
        result = assess_completeness('我被公司辞退了，工作了3年', 'LABOR_HR')
        # 辞退+工龄 应该匹配到足够的 slots
        assert result['score'] > 0

    def test_criminal_has_highest_threshold(self):
        """刑事案件：最严格门槛"""
        from src.services.scenario_templates import COMPLETENESS_THRESHOLDS
        criminal = COMPLETENESS_THRESHOLDS['CRIMINAL']
        drafting = COMPLETENESS_THRESHOLDS['DOCUMENT_DRAFTING']
        qa = COMPLETENESS_THRESHOLDS['QA_CONSULTATION']
        assert criminal['min_score'] > drafting['min_score'] > qa['min_score']
        assert criminal['min_filled_ratio'] > drafting['min_filled_ratio']


# ===== 2. 多轮追问 =====

class TestReassessAfterClarification:
    """测试补充信息后重新评估"""

    def test_one_field_not_enough_for_drafting(self):
        """文书起草：补充1个字段仍不放行"""
        from src.services.scenario_templates import (
            assess_completeness,
            reassess_after_clarification,
        )
        initial = assess_completeness('帮我起草一份合同', 'DOCUMENT_DRAFTING')
        result = reassess_after_clarification(
            user_input='帮我起草一份合同',
            intent='DOCUMENT_DRAFTING',
            original_assessment=initial,
            user_selections={'合同类型': '买卖合同'},
            current_round=1,
        )
        assert not result['is_complete'], "补充1项后文书起草不应放行"
        assert result['round'] == 2
        assert len(result['questions']) > 0

    def test_reassess_generates_next_round_questions(self):
        """重评估应生成下一轮问题"""
        from src.services.scenario_templates import (
            assess_completeness,
            reassess_after_clarification,
        )
        initial = assess_completeness('帮我起草合同', 'DOCUMENT_DRAFTING')
        result = reassess_after_clarification(
            user_input='帮我起草合同',
            intent='DOCUMENT_DRAFTING',
            original_assessment=initial,
            user_selections={},
            current_round=1,
        )
        assert result['has_next_round'] or not result['is_complete']


# ===== 3. 输出验证器 =====

class TestOutputValidator:
    """测试输出质量校验"""

    def test_blocks_guarantee_promises(self):
        """拦截不当保证性承诺"""
        from src.harness.output_validator import output_validator
        result = asyncio.get_event_loop().run_until_complete(
            output_validator.validate(
                response_text='根据分析，我保证胜诉，请放心。',
                user_query='官司能赢吗？',
                agent_name='legal_advisor',
            )
        )
        assert not result.passed, "包含'保证胜诉'应该被拦截"
        assert any('保证' in i.message for i in result.issues)

    def test_passes_good_response(self):
        """正常法律回复通过"""
        from src.harness.output_validator import output_validator
        result = asyncio.get_event_loop().run_until_complete(
            output_validator.validate(
                response_text='根据《民法典》第五百七十七条，违约方应当承担继续履行、采取补救措施等违约责任。建议您收集相关证据后向法院提起诉讼。',
                user_query='对方违约怎么办？',
                agent_name='legal_advisor',
            )
        )
        assert result.passed
        assert result.score >= 0.9

    def test_document_completeness_check(self):
        """文书场景检查必要要素"""
        from src.harness.output_validator import output_validator
        # 缺少当事人和日期的文书
        result = asyncio.get_event_loop().run_until_complete(
            output_validator.validate(
                response_text='第一条 服务内容为法律咨询。第二条 费用为1万元。',
                route='DOCUMENT_DRAFTING',
            )
        )
        # 应该有 warning 但仍然 passed
        has_doc_warning = any('文书' in i.message or '要素' in i.message for i in result.issues)
        assert has_doc_warning, "缺少当事人/日期应产生警告"


# ===== 4. 成本追踪 =====

class TestCostTracker:
    """测试费用统计"""

    def test_cost_calculation(self):
        """GPT-4o 费用计算"""
        from src.harness.cost_tracker import cost_tracker
        record = cost_tracker.record(
            model='gpt-4o', provider='openai',
            prompt_tokens=1000, completion_tokens=500,
        )
        # gpt-4o: input $2.50/M, output $10.00/M
        expected = (1000 * 2.50 + 500 * 10.00) / 1_000_000
        assert abs(record.cost_usd - expected) < 0.0001

    def test_local_model_zero_cost(self):
        """本地模型零费用"""
        from src.harness.cost_tracker import cost_tracker
        record = cost_tracker.record(
            model='qwen2.5:7b', provider='ollama',
            prompt_tokens=5000, completion_tokens=2000,
        )
        assert record.cost_usd == 0.0

    def test_stats_aggregation(self):
        """统计聚合"""
        from src.harness.cost_tracker import CostTracker
        tracker = CostTracker()
        tracker.record(model='gpt-4o', provider='openai', prompt_tokens=100, completion_tokens=50, agent_name='agent_a')
        tracker.record(model='gpt-4o', provider='openai', prompt_tokens=200, completion_tokens=100, agent_name='agent_b')
        stats = tracker.get_stats()
        assert stats['total_records'] == 2
        assert 'agent_a' in stats['by_agent']
        assert 'agent_b' in stats['by_agent']

    # ===== T6: 本地 LLM 字符估算 + 用户配额 =====

    def test_estimate_tokens_from_text(self):
        """简易 token 估算: 4 字符 = 1 token, 空文本 = 0。"""
        from src.harness.cost_tracker import estimate_tokens_from_text
        assert estimate_tokens_from_text("") == 0
        assert estimate_tokens_from_text("hello world") == 11 // 4
        assert estimate_tokens_from_text("a") == 1  # 最少 1 token

    def test_record_with_estimate_local_llm(self):
        """本地 LLM API 无 usage 字段时, record_with_estimate 按字符估算。"""
        from src.harness.cost_tracker import CostTracker
        tracker = CostTracker()
        rec = tracker.record_with_estimate(
            model="qwen2.5:7b",
            provider="ollama",
            prompt_text="x" * 400,  # 100 tokens
            completion_text="y" * 200,  # 50 tokens
            prompt_tokens=None,
            completion_tokens=None,
            agent_name="local_test",
        )
        assert rec.prompt_tokens == 100
        assert rec.completion_tokens == 50
        assert rec.cost_usd == 0.0  # 本地模型零成本

    def test_record_with_estimate_uses_api_truth_when_available(self):
        """API 返回 usage 时, record_with_estimate 优先用真值不估算。"""
        from src.harness.cost_tracker import CostTracker
        tracker = CostTracker()
        rec = tracker.record_with_estimate(
            model="gpt-4o",
            provider="openai",
            prompt_text="x" * 1000,  # 估算 250, 但不应使用
            completion_text="y" * 1000,
            prompt_tokens=42,
            completion_tokens=17,
            agent_name="cloud_test",
        )
        assert rec.prompt_tokens == 42
        assert rec.completion_tokens == 17

    def test_user_token_aggregation(self):
        """T6: 多次调用累计到 _by_user_tokens, 用于配额扣减。"""
        from src.harness.cost_tracker import CostTracker
        tracker = CostTracker()
        tracker.record(model="gpt-4o", provider="openai", prompt_tokens=100, completion_tokens=50, user_id="u1")
        tracker.record(model="gpt-4o", provider="openai", prompt_tokens=200, completion_tokens=100, user_id="u1")
        tracker.record(model="gpt-4o", provider="openai", prompt_tokens=50, completion_tokens=25, user_id="u2")
        assert tracker.get_user_tokens("u1") == 450
        assert tracker.get_user_tokens("u2") == 75
        assert tracker.get_user_tokens("ghost") == 0

    def test_check_user_quota_under_limit(self):
        """T6: 用量 + 即将消耗 < 配额 → allowed=True。"""
        from src.harness.cost_tracker import CostTracker
        tracker = CostTracker()
        tracker.record(model="gpt-4o", provider="openai", prompt_tokens=100, completion_tokens=50, user_id="u1")
        allowed, used, remaining = tracker.check_user_quota("u1", quota_tokens=10_000, upcoming_tokens=500)
        assert allowed is True
        assert used == 150
        assert remaining == 10_000 - 150 - 500

    def test_check_user_quota_exceeds(self):
        """T6: 用量 + 即将消耗 > 配额 → allowed=False。"""
        from src.harness.cost_tracker import CostTracker
        tracker = CostTracker()
        tracker.record(model="gpt-4o", provider="openai", prompt_tokens=9000, completion_tokens=900, user_id="u1")
        allowed, used, remaining = tracker.check_user_quota("u1", quota_tokens=10_000, upcoming_tokens=500)
        assert allowed is False
        assert used == 9900
        assert remaining == 0

    def test_check_user_quota_unlimited(self):
        """T6: quota_tokens=0 表示不限, 永远 allowed。"""
        from src.harness.cost_tracker import CostTracker
        tracker = CostTracker()
        tracker.record(model="gpt-4o", provider="openai", prompt_tokens=99_999, completion_tokens=99_999, user_id="u1")
        allowed, used, _ = tracker.check_user_quota("u1", quota_tokens=0, upcoming_tokens=999_999)
        assert allowed is True

    def test_quota_exceeded_error_message(self):
        """T6: QuotaExceededError 含 user_id / used / quota 三字段。"""
        from src.harness.cost_tracker import QuotaExceededError
        err = QuotaExceededError("u1", used=10_500, quota=10_000)
        assert err.user_id == "u1"
        assert err.used == 10_500
        assert err.quota == 10_000
        assert "10500" in str(err) or "10,500" in str(err) or "10_500" in str(err)

    def test_reset_user_tokens(self):
        """T6: 新计费周期清零用户用量。"""
        from src.harness.cost_tracker import CostTracker
        tracker = CostTracker()
        tracker.record(model="gpt-4o", provider="openai", prompt_tokens=100, completion_tokens=50, user_id="u1")
        assert tracker.get_user_tokens("u1") == 150
        tracker.reset_user_tokens("u1")
        assert tracker.get_user_tokens("u1") == 0
        assert tracker.get_user_cost("u1") == 0.0


# ===== 5. 权限检查 =====

class TestPolicyEngine:
    """测试 Agent 权限"""

    def test_contract_reviewer_can_search(self):
        """合同审查Agent可以检索知识库"""
        from src.harness.policy_engine import PolicyDecision, policy_engine
        result = policy_engine.check_tool_access('contract_reviewer', 'search_knowledge')
        assert result.decision == PolicyDecision.ALLOW

    def test_contract_reviewer_cannot_send_email(self):
        """合同审查Agent不能发邮件"""
        from src.harness.policy_engine import PolicyDecision, policy_engine
        result = policy_engine.check_tool_access('contract_reviewer', 'send_email')
        assert result.decision == PolicyDecision.DENY

    def test_risk_assessor_cannot_draft(self):
        """风险评估Agent不能起草合同"""
        from src.harness.policy_engine import PolicyDecision, policy_engine
        result = policy_engine.check_tool_access('risk_assessor', 'draft_contract')
        assert result.decision == PolicyDecision.DENY

    def test_unknown_tool_is_fail_closed(self):
        """未注册工具必须 fail-closed，避免 agent 绕过注册中心。"""
        from src.harness.policy_engine import PolicyDecision, PolicyEngine

        engine = PolicyEngine()
        result = engine.check_tool_access('legal_advisor', 'unregistered_shell_tool')

        assert result.decision == PolicyDecision.DENY

    def test_explicit_allowed_tools_are_enforced(self):
        """AgentPolicy.allowed_tools 生效，不能只靠 denied_tools。"""
        from src.harness.policy_engine import (
            AgentPolicy,
            PolicyDecision,
            PolicyEngine,
        )
        from src.harness.tool_registry import RiskLevel

        engine = PolicyEngine()
        engine.set_policy(AgentPolicy(
            agent_name='strict_agent',
            allowed_tools={'search_knowledge'},
            max_risk_level=RiskLevel.READ_ONLY,
        ))

        allowed = engine.check_tool_access('strict_agent', 'search_knowledge')
        denied = engine.check_tool_access('strict_agent', 'validate_document')

        assert allowed.decision == PolicyDecision.ALLOW
        assert denied.decision == PolicyDecision.DENY

    def test_subscription_feature_context_is_fail_closed(self):
        """传入订阅能力后，缺失能力不能继续调用工具。"""
        from src.harness.policy_engine import PolicyContext, PolicyDecision, PolicyEngine

        engine = PolicyEngine()
        result = engine.check_tool_access(
            'legal_advisor',
            'draft_contract',
            context=PolicyContext(subscription_features={'legal_knowledge_base'}),
        )

        assert result.decision == PolicyDecision.DENY

    def test_subscription_feature_alias_can_allow_tool(self):
        """订阅能力可通过业务 feature 映射到工具，而不是只认工具名。"""
        from src.harness.policy_engine import PolicyContext, PolicyDecision, PolicyEngine

        engine = PolicyEngine()
        result = engine.check_tool_access(
            'legal_researcher',
            'search_knowledge',
            context=PolicyContext(
                subscription_features={'legal_knowledge_base'},
                permissions={'read:knowledge'},
            ),
        )

        assert result.decision == PolicyDecision.ALLOW

    def test_missing_role_permission_denies_tool(self):
        """上下文传入角色权限后，缺少工具所需 permission 应拒绝。"""
        from src.harness.policy_engine import PolicyContext, PolicyDecision, PolicyEngine

        engine = PolicyEngine()
        result = engine.check_tool_access(
            'legal_researcher',
            'search_knowledge',
            context=PolicyContext(
                subscription_features={'legal_knowledge_base'},
                permissions=set(),
            ),
        )

        assert result.decision == PolicyDecision.DENY
        assert result.missing_permissions == {'read:knowledge'}

    def test_top_secret_mode_denies_external_tool(self):
        """绝密模式下外部数据采集必须 fail-closed。"""
        from src.harness.policy_engine import PolicyContext, PolicyDecision, PolicyEngine

        engine = PolicyEngine()
        result = engine.check_tool_access(
            'due_diligence',
            'crawl_company_info',
            context=PolicyContext(
                subscription_features={'due_diligence'},
                permissions={'read:assets'},
                privacy_mode='top_secret',
            ),
        )

        assert result.decision == PolicyDecision.DENY

    def test_untrusted_device_denies_high_risk_tool(self):
        """未受信设备不能进入高风险审批路径。"""
        from src.harness.policy_engine import (
            AgentPolicy,
            PolicyContext,
            PolicyDecision,
            PolicyEngine,
        )
        from src.harness.tool_registry import RiskLevel

        engine = PolicyEngine()
        engine.set_policy(AgentPolicy(
            agent_name='legal_advisor',
            max_risk_level=RiskLevel.HIGH_RISK,
        ))
        result = engine.check_tool_access(
            'legal_advisor',
            'generate_legal_opinion',
            context=PolicyContext(
                subscription_features={'lawyer_matching'},
                permissions={'review:contracts', 'sign:contracts'},
                device_trusted=False,
            ),
        )

        assert result.decision == PolicyDecision.DENY

    def test_authorized_approval_allows_high_risk_tool(self):
        """高风险工具在授权角色审批后才可放行。"""
        from src.harness.policy_engine import (
            AgentPolicy,
            PolicyContext,
            PolicyDecision,
            PolicyEngine,
        )
        from src.harness.tool_registry import RiskLevel

        engine = PolicyEngine()
        engine.set_policy(AgentPolicy(
            agent_name='legal_advisor',
            max_risk_level=RiskLevel.HIGH_RISK,
        ))
        result = engine.check_tool_access(
            'legal_advisor',
            'generate_legal_opinion',
            context=PolicyContext(
                subscription_features={'lawyer_matching'},
                permissions={'review:contracts', 'sign:contracts'},
                approval_state='approved',
                approver_role='admin',
            ),
        )

        assert result.decision == PolicyDecision.ALLOW


class TestAgentMcpToolPolicy:
    """测试 Agent 运行时 MCP 工具判权。"""

    @staticmethod
    def _agent(name: str = 'legal_researcher'):
        from src.agents.base import AgentConfig, AgentResponse, BaseLegalAgent

        class PolicyProbeAgent(BaseLegalAgent):
            def _init_agent(self) -> None:
                self.llm_config = None
                self.model_name = None

            async def process(self, task):
                return AgentResponse(agent_name=self.name, content=str(task))

        return PolicyProbeAgent(AgentConfig(
            name=name,
            role='policy probe',
            description='policy probe',
            system_prompt='policy probe',
        ))

    def test_agent_only_exposes_policy_allowed_tools(self):
        """给模型的 MCP tool list 必须先经过 policy_engine。"""
        agent = self._agent('legal_researcher')
        tools = [
            {'type': 'function', 'function': {'name': 'search_knowledge'}},
            {'type': 'function', 'function': {'name': 'untrusted_server__shell'}},
        ]

        filtered = agent._filter_mcp_tools_for_policy(tools)

        assert [tool['function']['name'] for tool in filtered] == ['search_knowledge']

    def test_model_returned_forbidden_tool_is_denied_at_runtime(self):
        """即使模型返回被禁工具名，执行前仍应二次判权 (走 policy_enforcement, enforce=True)。"""
        agent = self._agent('legal_researcher')
        allowed, info = agent._check_mcp_tool_policy('untrusted_server__shell')
        denial = agent._tool_policy_denial('untrusted_server__shell', info.get('reason', ''))

        assert allowed is False
        assert info['decision'] == 'deny'
        assert info['enforced'] is True
        assert '工具调用被拒绝' in denial


# ===== 6. 任务状态机 =====

class TestTaskEngine:
    """测试任务状态流转"""

    def test_valid_transitions(self):
        """合法状态转换"""
        from src.harness.task_engine import TaskState, task_engine
        task = task_engine.create_task('测试任务', route='general')
        assert task_engine.transition(task.task_id, TaskState.RUNNING)
        assert task_engine.transition(task.task_id, TaskState.COMPLETED)

    def test_invalid_transition_blocked(self):
        """非法状态转换被拒绝"""
        from src.harness.task_engine import TaskState, task_engine
        task = task_engine.create_task('测试任务2', route='general')
        task_engine.transition(task.task_id, TaskState.RUNNING)
        task_engine.transition(task.task_id, TaskState.COMPLETED)
        # 终态不能回到 RUNNING
        assert not task_engine.transition(task.task_id, TaskState.RUNNING)

    def test_priority_assignment(self):
        """优先级自动分配"""
        from src.harness.task_engine import TaskPriority, task_engine
        t1 = task_engine.create_task('审查合同', route='contract_review')
        t2 = task_engine.create_task('法律咨询', route='rag')
        assert t1.priority == TaskPriority.HIGH
        assert t2.priority == TaskPriority.LOW

    # ===== T7: 长任务接入 task_engine =====

    def test_t7_due_diligence_creates_task_record(self):
        """T7: investigate_company 应创建 task_engine 记录 + 透出 task_id。"""
        import asyncio

        from src.harness.task_engine import TaskState, task_engine

        # mock 出 due_diligence_service 的 _get_basic_info / report
        # 这里只验证 task_engine.create_task 被以 due_diligence route 创建
        # 用对 task_engine 的间接观察: 调 list_by_route 看到新记录
        before = len(task_engine._tasks)

        from unittest.mock import patch, AsyncMock
        from src.services import due_diligence_service as dd_module

        async def _run():
            svc = dd_module.DueDiligenceService.__new__(dd_module.DueDiligenceService)
            with (
                patch.object(svc, "_get_basic_info", AsyncMock(return_value={"name": "A 公司"})),
                patch.object(svc, "_get_litigation_info", AsyncMock(return_value={})),
                patch.object(svc, "_get_credit_info", AsyncMock(return_value={})),
                patch.object(svc, "_assess_risks", AsyncMock(return_value={"level": "low"})),
                patch.object(svc, "_get_company_relations", AsyncMock(return_value={})),
                patch.object(svc, "_generate_report", AsyncMock(return_value="OK")),
            ):
                return await svc.investigate_company("A 公司", "comprehensive")

        result = asyncio.get_event_loop().run_until_complete(_run())
        assert "task_id" in result
        assert len(task_engine._tasks) > before
        rec = task_engine.get_task(result["task_id"])
        assert rec is not None
        assert rec.route == "due_diligence"
        assert rec.state == TaskState.COMPLETED

    def test_t7_batch_document_creates_task_record(self):
        """T7: BatchDocumentService.execute_batch 应创建 task_engine 记录 + 设 task_id。"""
        import asyncio

        from src.harness.task_engine import TaskState, task_engine
        from src.services.batch_document_service import batch_document_service, DOCUMENT_TEMPLATES

        # 选 property_demand_letter 模板, 至少有 1 个必填字段
        template_key = "property_demand_letter"
        required = DOCUMENT_TEMPLATES[template_key]["required_fields"]
        recipient = {fld: "占位" for fld in required}

        async def _run():
            job = batch_document_service.create_batch_job(
                template_type=template_key,
                recipients=[recipient],
                common_context={},
            )
            return await batch_document_service.execute_batch(job.job_id)

        job = asyncio.get_event_loop().run_until_complete(_run())
        assert getattr(job, "task_id", None) is not None
        rec = task_engine.get_task(job.task_id)
        assert rec is not None
        assert rec.route == "document_drafting"
        assert rec.state == TaskState.COMPLETED


# ===== 7. 能力协商 =====

class TestCapabilityNegotiator:
    """测试多端能力协商"""

    def test_web_cloud_full_features(self):
        """Web+Cloud = 全功能"""
        from src.harness.capability_negotiator import AppMode, PlatformType, capability_negotiator
        result = capability_negotiator.negotiate(PlatformType.WEB, AppMode.CLOUD)
        available_count = sum(result.available_features.values())
        assert available_count > 8

    def test_desktop_top_secret_limited(self):
        """Desktop+TopSecret = 受限"""
        from src.harness.capability_negotiator import AppMode, PlatformType, capability_negotiator
        result = capability_negotiator.negotiate(PlatformType.DESKTOP, AppMode.TOP_SECRET)
        assert len(result.unavailable_features) > 5
        assert len(result.warnings) > 0

    def test_degradation_notice(self):
        """模式降级通知"""
        from src.harness.capability_negotiator import AppMode, capability_negotiator
        notice = capability_negotiator.get_degradation_notice(AppMode.CLOUD, AppMode.TOP_SECRET)
        assert len(notice['lost_features']) > 0


@pytest.mark.asyncio
async def test_context_engine_handoff_artifacts(monkeypatch):
    """跨会话 artifact handoff 应复制已存在的中间产物并跳过缺失类型。"""
    from src.harness.context_engine import ContextEngine
    from src.services import memory_layer as memory_module

    local_memory = memory_module.MemoryLayer()
    monkeypatch.setattr(memory_module, "memory_layer", local_memory)

    await local_memory.set_session_artifact("source-session", "summary", {"text": "摘要"})
    await local_memory.set_session_artifact(
        "source-session",
        "citations",
        [{"title": "《民法典》第五百七十七条"}],
    )

    result = await ContextEngine().handoff_artifacts(
        "source-session",
        "target-session",
        artifact_types=["summary", "citations", "missing"],
    )

    assert result == {"transferred": {"summary": True, "citations": True}}
    assert await local_memory.get_session_artifact("target-session", "summary") == {"text": "摘要"}
    assert await local_memory.get_session_artifact("target-session", "citations") == [
        {"title": "《民法典》第五百七十七条"}
    ]
    assert await local_memory.get_session_artifact("target-session", "missing") is None


# ===== 8. 模板管理员 =====

class TestTemplateLibrarian:
    """测试模板查询Agent"""

    def test_match_sales_contract(self):
        """匹配买卖合同模板"""
        from src.agents.template_librarian import TemplateLirarianAgent
        agent = TemplateLirarianAgent()
        result = asyncio.get_event_loop().run_until_complete(
            agent.process({'description': '给我一份买卖合同模板'})
        )
        assert result.metadata['template_count'] > 0
        assert '买卖' in result.content or '模板' in result.content

    def test_no_match_returns_fallback(self):
        """无匹配时提供降级选项"""
        from src.agents.template_librarian import TemplateLirarianAgent
        agent = TemplateLirarianAgent()
        result = asyncio.get_event_loop().run_until_complete(
            agent.process({'description': '给我一份火星殖民合同模板'})
        )
        assert result.metadata['template_count'] == 0
        assert result.metadata['has_ai_fallback'] is True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
