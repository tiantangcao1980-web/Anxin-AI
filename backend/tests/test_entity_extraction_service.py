from src.services.entity_extraction_service import EntityExtractionService


def test_entity_extraction_returns_empty_result_for_blank_text():
    service = EntityExtractionService()

    result = service._rule_based_extract("")

    assert result["entities"] == []
    assert result["relations"] == []
    assert result["method"] == "rule_based"


def test_entity_extraction_rule_based_finds_legal_entities():
    service = EntityExtractionService()

    result = service._rule_based_extract(
        "北京市朝阳区人民法院依据《民法典》第五百七十七条审理，"
        "北京安心科技有限公司承担违约责任。"
    )

    entities = {(item["name"], item["type"]) for item in result["entities"]}
    assert ("北京市朝阳区人民法院", "Court") in entities
    assert ("民法典", "Law") in entities
    assert ("第五百七十七条", "Provision") in entities
    assert ("北京安心科技有限公司", "Company") in entities
    assert result["relations"] == []
