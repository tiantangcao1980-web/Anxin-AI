from src.services.search_dedup_service import SearchDedupService


def test_deduplicate_keeps_highest_relevance_for_same_url():
    service = SearchDedupService()

    results = service.deduplicate(
        [
            {"url": "https://www.court.gov.cn/case?utm_source=news", "title": "低分", "relevance": 0.2},
            {"url": "https://court.gov.cn/case", "title": "高分", "relevance": 0.9},
        ]
    )

    assert len(results) == 1
    assert results[0]["title"] == "高分"


def test_merge_multi_source_adds_scores_and_keeps_best_item():
    service = SearchDedupService()

    merged = service.merge_multi_source(
        [{"url": "https://example.test/a", "title": "A", "relevance": 0.1}],
        [{"url": "https://example.test/a", "title": "A better", "relevance": 0.8}],
    )

    assert len(merged) == 1
    assert merged[0]["title"] == "A better"
    assert merged[0]["merged_score"] > 0
    assert merged[0]["trust_score"] == 0.5
