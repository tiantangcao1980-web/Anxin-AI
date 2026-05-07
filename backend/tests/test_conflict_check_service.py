from src.models.case import Case
from src.services.conflict_check_service import ConflictCheckResult, ConflictCheckService


def test_conflict_check_result_serializes_count():
    result = ConflictCheckResult()
    result.conflicts.append({"case_id": "case-1", "new_party": "安心科技"})
    result.has_conflict = True
    result.warning_level = "medium"

    assert result.to_dict() == {
        "has_conflict": True,
        "warning_level": "medium",
        "conflict_count": 1,
        "conflicts": [{"case_id": "case-1", "new_party": "安心科技"}],
    }


def test_extract_parties_supports_structured_case_payloads():
    case = Case(
        title="合同纠纷",
        parties={
            "plaintiff": "安心科技有限公司",
            "defendant": [{"name": "未来实业公司", "role": "defendant"}],
        },
    )

    parties = ConflictCheckService._extract_parties(case)

    assert {"name": "安心科技有限公司", "role": "plaintiff"} in parties
    assert {"name": "未来实业公司", "role": "defendant"} in parties


def test_names_match_exact_and_contained_company_names():
    assert ConflictCheckService._names_match("安心科技有限公司", "安心科技有限公司")
    assert ConflictCheckService._names_match("安心科技", "安心科技有限公司")
    assert not ConflictCheckService._names_match("安心科技", "远方实业")
