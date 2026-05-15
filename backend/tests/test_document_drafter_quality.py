from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.document_drafter import DocumentDraftAgent


def _make_llm_config_mock():
    return MagicMock(
        provider="openai",
        model_name="gpt-4o",
        temperature=0.7,
        max_tokens=4096,
        api_key="test-key",
        api_base_url=None,
        source="env",
    )


@pytest.mark.asyncio
@patch("src.agents.base.get_llm_config_sync")
@patch("src.agents.base.ModelFactory.create")
async def test_process_uses_high_usability_draft_mode_when_key_info_missing(
    mock_model_factory, mock_llm_config
):
    mock_llm_config.return_value = _make_llm_config_mock()
    mock_model_factory.return_value = MagicMock()
    agent = DocumentDraftAgent()

    with patch.object(
        agent, "chat", new_callable=AsyncMock, return_value="# 服务合同\n\n## 第一条 合同标的\n..."
    ) as mock_chat:
        task = {
            "description": "起草一份服务合同",
            "context": {
                "doc_type": "服务合同",
                "scenario": "甲方委托乙方提供年度运维服务",
                "requirements": {
                    "client": "甲公司",
                    "target": "乙公司",
                    "details": "未提供金额和付款节点",
                },
            },
        }

        result = await agent.process(task)

    first_prompt = mock_chat.await_args_list[0].args[0]
    assert "高可用草案" in result.reasoning
    assert "【输出模式】高可用草案" in first_prompt
    assert "## 待确认事项" in first_prompt


@pytest.mark.asyncio
@patch("src.agents.base.get_llm_config_sync")
@patch("src.agents.base.ModelFactory.create")
async def test_process_retries_with_targeted_repair_when_validation_fails(
    mock_model_factory, mock_llm_config
):
    mock_llm_config.return_value = _make_llm_config_mock()
    mock_model_factory.return_value = MagicMock()
    agent = DocumentDraftAgent()

    first_output = "# 服务合同\n\n甲方：甲公司\n乙方：乙公司"
    repaired_output = "# 服务合同\n\n## 第一条 定义与解释\n1.1 ..."

    with patch.object(
        agent, "chat", new_callable=AsyncMock, side_effect=[first_output, repaired_output]
    ) as mock_chat:
        result = await agent.process(
            {
                "description": "起草一份服务合同",
                "context": {
                    "doc_type": "服务合同",
                    "requirements": {"client": "甲公司", "target": "乙公司"},
                },
            }
        )

    second_prompt = mock_chat.await_args_list[1].args[0]
    assert result.content.startswith(repaired_output)
    assert "## 待确认事项" in result.content
    assert mock_chat.await_count == 2
    assert "必须修复的问题" in second_prompt


@pytest.mark.asyncio
@patch("src.agents.base.get_llm_config_sync")
@patch("src.agents.base.ModelFactory.create")
async def test_process_uses_doc_type_specific_missing_fields_for_contract(
    mock_model_factory, mock_llm_config
):
    mock_llm_config.return_value = _make_llm_config_mock()
    mock_model_factory.return_value = MagicMock()
    agent = DocumentDraftAgent()

    with patch.object(
        agent, "chat", new_callable=AsyncMock, return_value="# 服务合同\n\n## 第一条 合同标的\n..."
    ) as mock_chat:
        result = await agent.process(
            {
                "description": "起草一份服务合同",
                "context": {
                    "doc_type": "服务合同",
                    "scenario": "甲方委托乙方提供系统运维服务",
                    "requirements": {"client": "甲公司", "target": "乙公司"},
                },
            }
        )

    first_prompt = mock_chat.await_args_list[0].args[0]
    assert "合同金额与付款安排" in first_prompt
    assert "履行期限与交付节点" in first_prompt
    assert "missing_fields" in result.metadata
    assert result.metadata["missing_fields"][0]["label"] == "合同金额与付款安排"
    assert result.metadata["missing_fields"][0]["severity"] == "high"


@pytest.mark.asyncio
@patch("src.agents.base.get_llm_config_sync")
@patch("src.agents.base.ModelFactory.create")
async def test_process_appends_missing_sections_when_model_output_is_sparse(
    mock_model_factory, mock_llm_config
):
    mock_llm_config.return_value = _make_llm_config_mock()
    mock_model_factory.return_value = MagicMock()
    agent = DocumentDraftAgent()

    with patch.object(
        agent,
        "chat",
        new_callable=AsyncMock,
        return_value="# 服务合同\n\n## 第一条 合同标的\n乙方向甲方提供运维服务。",
    ):
        result = await agent.process(
            {
                "description": "起草一份服务合同",
                "context": {
                    "doc_type": "服务合同",
                    "scenario": "甲方委托乙方提供年度运维服务",
                    "requirements": {"client": "甲公司", "target": "乙公司"},
                },
            }
        )

    assert "## 起草说明" in result.content
    assert "## 待确认事项" in result.content
    assert "## 使用提示" in result.content


@pytest.mark.asyncio
@patch("src.agents.base.get_llm_config_sync")
@patch("src.agents.base.ModelFactory.create")
async def test_process_uses_doc_type_specific_missing_fields_for_lawyer_letter(
    mock_model_factory, mock_llm_config
):
    mock_llm_config.return_value = _make_llm_config_mock()
    mock_model_factory.return_value = MagicMock()
    agent = DocumentDraftAgent()

    with patch.object(
        agent, "chat", new_callable=AsyncMock, return_value="# 律师函\n\n一、基本事实\n..."
    ) as mock_chat:
        result = await agent.process(
            {
                "description": "向供应商发送律师函",
                "context": {
                    "doc_type": "律师函",
                    "scenario": "乙方拖欠服务费，需要正式催告",
                    "requirements": {
                        "client": "甲公司",
                        "target": "乙公司",
                        "details": "要求尽快支付拖欠款项",
                    },
                },
            }
        )

    first_prompt = mock_chat.await_args_list[0].args[0]
    assert "履行要求与期限" in first_prompt
    assert result.metadata["missing_fields"][-1]["label"] == "法律后果提示"
    assert result.metadata["missing_fields"][-1]["group"] == "风险控制"


@pytest.mark.asyncio
@patch("src.agents.base.get_llm_config_sync")
@patch("src.agents.base.ModelFactory.create")
async def test_process_uses_doc_type_specific_missing_fields_for_legal_opinion(
    mock_model_factory, mock_llm_config
):
    mock_llm_config.return_value = _make_llm_config_mock()
    mock_model_factory.return_value = MagicMock()
    agent = DocumentDraftAgent()

    with patch.object(
        agent, "chat", new_callable=AsyncMock, return_value="# 法律意见书\n\n## 一、引言\n..."
    ) as mock_chat:
        result = await agent.process(
            {
                "description": "出具一份并购交易法律意见书",
                "context": {
                    "doc_type": "法律意见书",
                    "scenario": "围绕股权收购交易出具初步法律分析",
                    "requirements": {
                        "details": "已知存在股权转让协议，但未明确结论和适用限制",
                    },
                },
            }
        )

    first_prompt = mock_chat.await_args_list[0].args[0]
    assert "结论与适用限制" in first_prompt
    assert result.metadata["missing_fields"][0]["label"] == "委托事项与范围"
    assert result.metadata["missing_fields"][0]["group"] == "委托基础"


@pytest.mark.asyncio
@patch("src.agents.base.get_llm_config_sync")
@patch("src.agents.base.ModelFactory.create")
async def test_process_renders_structured_missing_fields_in_pending_section(
    mock_model_factory, mock_llm_config
):
    mock_llm_config.return_value = _make_llm_config_mock()
    mock_model_factory.return_value = MagicMock()
    agent = DocumentDraftAgent()

    with patch.object(
        agent,
        "chat",
        new_callable=AsyncMock,
        return_value="# 服务合同\n\n## 第一条 合同标的\n乙方向甲方提供运维服务。",
    ):
        result = await agent.process(
            {
                "description": "起草一份服务合同",
                "context": {
                    "doc_type": "服务合同",
                    "scenario": "甲方委托乙方提供年度运维服务",
                    "requirements": {"client": "甲公司", "target": "乙公司"},
                },
            }
        )

    assert "- 合同金额与付款安排：" in result.content
    assert "建议补充：明确合同总价、付款节点、付款条件" in result.content


@pytest.mark.asyncio
@patch("src.agents.base.get_llm_config_sync")
@patch("src.agents.base.ModelFactory.create")
async def test_process_uses_weighted_completeness_for_high_severity_contract_gaps(
    mock_model_factory, mock_llm_config
):
    mock_llm_config.return_value = _make_llm_config_mock()
    mock_model_factory.return_value = MagicMock()
    agent = DocumentDraftAgent()

    with patch.object(
        agent, "chat", new_callable=AsyncMock, return_value="# 服务合同\n\n## 第一条 合同标的\n..."
    ):
        result = await agent.process(
            {
                "description": "起草一份服务合同",
                "context": {
                    "doc_type": "服务合同",
                    "scenario": "甲方委托乙方提供系统运维服务",
                    "requirements": {
                        "client": "甲公司",
                        "target": "乙公司",
                        "details": "提供系统运维服务",
                    },
                },
            }
        )

    assert result.metadata["completeness_score"] < 0.45
    assert result.metadata["draft_mode"] == "结构化草稿"


@pytest.mark.asyncio
@patch("src.agents.base.get_llm_config_sync")
@patch("src.agents.base.ModelFactory.create")
async def test_process_prioritizes_high_severity_pending_items_in_repair_prompt(
    mock_model_factory, mock_llm_config
):
    mock_llm_config.return_value = _make_llm_config_mock()
    mock_model_factory.return_value = MagicMock()
    agent = DocumentDraftAgent()

    first_output = "# 律师函\n\n一、基本事实\n乙方拖欠服务费。"
    repaired_output = "# 律师函\n\n一、基本事实\n...\n\n四、具体要求\n..."

    with patch.object(
        agent, "chat", new_callable=AsyncMock, side_effect=[first_output, repaired_output]
    ) as mock_chat:
        await agent.process(
            {
                "description": "向供应商发送律师函",
                "context": {
                    "doc_type": "律师函",
                    "scenario": "乙方拖欠服务费，需要正式催告",
                    "requirements": {
                        "client": "甲公司",
                        "target": "乙公司",
                        "details": "要求尽快支付拖欠款项",
                    },
                },
            }
        )

    second_prompt = mock_chat.await_args_list[1].args[0]
    assert "优先补齐的待确认事项" in second_prompt
    assert second_prompt.index("履行要求与期限（优先级：high）") < second_prompt.index(
        "法律后果提示（优先级：medium）"
    )
