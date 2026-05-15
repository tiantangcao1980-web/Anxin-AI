import pytest

from src.services.lawyer_matching_service import LawyerMatchingService, anonymize_text


def test_anonymize_text_masks_common_identifiers() -> None:
    masked = anonymize_text(
        "我叫张三，电话13812345678，邮箱alice@example.com，身份证110101199001011234"
    )

    assert "张三" not in masked
    assert "13812345678" not in masked
    assert "alice@example.com" not in masked
    assert "110101199001011234" not in masked
    assert "张某" in masked
    assert "138****5678" in masked


@pytest.mark.asyncio
async def test_analyze_case_falls_back_to_rule_summary_when_llm_is_unavailable() -> None:
    service = LawyerMatchingService()

    result = await service.analyze_case("我叫张三，手机13812345678。对方合同违约，拖欠10万元货款。")

    assert result["legal_domain"] == "contract"
    assert result["domain_label"] == "合同纠纷"
    assert result["legal_elements"]["amounts_mentioned"] == [10.0]
    assert "张三" not in result["anonymous_summary"]
    assert "13812345678" not in result["anonymous_summary"]
    assert "138****5678" in result["anonymous_summary"]
