from src.middleware.waf import _scan_dict, _scan_value


def test_scan_value_detects_sql_and_xss_patterns() -> None:
    assert _scan_value("1 UNION SELECT password FROM users") is not None
    assert _scan_value("<script>alert(1)</script>") is not None
    assert _scan_value("普通合同条款") is None


def test_scan_dict_reports_nested_path_for_unsafe_value() -> None:
    hit = _scan_dict({"items": [{"title": "safe"}, {"title": "<script>alert(1)</script>"}]})

    assert hit is not None
    assert hit.startswith("items[1].title:")
