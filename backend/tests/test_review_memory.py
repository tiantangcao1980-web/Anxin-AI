from src.services.review_memory import ReviewMemoryService


def test_review_memory_saves_stats_and_common_risks():
    service = ReviewMemoryService()

    service.save_review(
        "买卖合同",
        {
            "risks": [
                {"title": "付款期限不清", "type": "payment"},
                {"title": "违约责任缺失", "type": "liability"},
            ],
            "missing_clauses": ["争议解决"],
        },
        accepted_risk_ids=["付款期限不清"],
        rejected_risk_ids=["违约责任缺失"],
        quality_score=0.8,
    )

    stats = service.get_type_stats("买卖合同")
    similar = service.find_similar_reviews("买卖合同")

    assert stats["total_reviews"] == 1
    assert stats["total_risks"] == 2
    assert service.get_common_risks("买卖合同") == ["付款期限不清", "违约责任缺失"]
    assert similar[0]["missing_clauses"] == ["争议解决"]
    assert similar[0]["quality_score"] == 0.8


def test_review_memory_builds_prompt_from_rejection_patterns():
    service = ReviewMemoryService()
    review_result = {
        "risks": [
            {"title": "违约金过高", "type": "liability"},
            {"title": "违约金过低", "type": "liability"},
        ],
        "missing_clauses": [],
    }

    service.save_review("服务合同", review_result, rejected_risk_ids=["违约金过高"])
    service.save_review("服务合同", review_result, rejected_risk_ids=["违约金过低"])

    prompt = service.get_prompt_enhancement("服务合同")

    assert "历史审查经验" in prompt
    assert "质量改进提示" in prompt
    assert "liability" in prompt
