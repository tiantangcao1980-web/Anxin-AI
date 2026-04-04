# -*- coding: utf-8 -*-
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
import pytest
import sys
import os

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
        from src.services.scenario_templates import assess_completeness, reassess_after_clarification
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
        from src.services.scenario_templates import assess_completeness, reassess_after_clarification
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


# ===== 5. 权限检查 =====

class TestPolicyEngine:
    """测试 Agent 权限"""

    def test_contract_reviewer_can_search(self):
        """合同审查Agent可以检索知识库"""
        from src.harness.policy_engine import policy_engine, PolicyDecision
        result = policy_engine.check_tool_access('contract_reviewer', 'search_knowledge')
        assert result.decision == PolicyDecision.ALLOW

    def test_contract_reviewer_cannot_send_email(self):
        """合同审查Agent不能发邮件"""
        from src.harness.policy_engine import policy_engine, PolicyDecision
        result = policy_engine.check_tool_access('contract_reviewer', 'send_email')
        assert result.decision == PolicyDecision.DENY

    def test_risk_assessor_cannot_draft(self):
        """风险评估Agent不能起草合同"""
        from src.harness.policy_engine import policy_engine, PolicyDecision
        result = policy_engine.check_tool_access('risk_assessor', 'draft_contract')
        assert result.decision == PolicyDecision.DENY


# ===== 6. 任务状态机 =====

class TestTaskEngine:
    """测试任务状态流转"""

    def test_valid_transitions(self):
        """合法状态转换"""
        from src.harness.task_engine import task_engine, TaskState
        task = task_engine.create_task('测试任务', route='general')
        assert task_engine.transition(task.task_id, TaskState.RUNNING)
        assert task_engine.transition(task.task_id, TaskState.COMPLETED)

    def test_invalid_transition_blocked(self):
        """非法状态转换被拒绝"""
        from src.harness.task_engine import task_engine, TaskState
        task = task_engine.create_task('测试任务2', route='general')
        task_engine.transition(task.task_id, TaskState.RUNNING)
        task_engine.transition(task.task_id, TaskState.COMPLETED)
        # 终态不能回到 RUNNING
        assert not task_engine.transition(task.task_id, TaskState.RUNNING)

    def test_priority_assignment(self):
        """优先级自动分配"""
        from src.harness.task_engine import task_engine, TaskPriority
        t1 = task_engine.create_task('审查合同', route='contract_review')
        t2 = task_engine.create_task('法律咨询', route='rag')
        assert t1.priority == TaskPriority.HIGH
        assert t2.priority == TaskPriority.LOW


# ===== 7. 能力协商 =====

class TestCapabilityNegotiator:
    """测试多端能力协商"""

    def test_web_cloud_full_features(self):
        """Web+Cloud = 全功能"""
        from src.harness.capability_negotiator import capability_negotiator, PlatformType, AppMode
        result = capability_negotiator.negotiate(PlatformType.WEB, AppMode.CLOUD)
        available_count = sum(result.available_features.values())
        assert available_count > 8

    def test_desktop_top_secret_limited(self):
        """Desktop+TopSecret = 受限"""
        from src.harness.capability_negotiator import capability_negotiator, PlatformType, AppMode
        result = capability_negotiator.negotiate(PlatformType.DESKTOP, AppMode.TOP_SECRET)
        assert len(result.unavailable_features) > 5
        assert len(result.warnings) > 0

    def test_degradation_notice(self):
        """模式降级通知"""
        from src.harness.capability_negotiator import capability_negotiator, AppMode
        notice = capability_negotiator.get_degradation_notice(AppMode.CLOUD, AppMode.TOP_SECRET)
        assert len(notice['lost_features']) > 0


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
