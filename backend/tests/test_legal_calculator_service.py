from src.services.legal_calculator_service import LegalCalculatorService


def test_litigation_cost_supports_float_fee_and_simplified_reduction():
    service = LegalCalculatorService()

    result = service.calc_litigation_cost(
        amount=300_000,
        case_type="divorce",
        is_simplified=True,
    )

    assert result.total_amount == 400
    assert result.breakdown[1]["amount"] == 500
    assert result.breakdown[2]["item"] == "简易程序减半"
    assert "简易程序" in result.legal_basis[-1]


def test_calculate_dispatch_returns_result_and_handles_unknown_type():
    service = LegalCalculatorService()

    known = service.calculate(
        "litigation_cost",
        {"amount": 10_000, "case_type": "labor"},
    )
    unknown = service.calculate("unknown", {})

    assert known.calculator_name == "诉讼费计算器"
    assert known.total_amount == 10
    assert unknown.calculator_name == "未知计算器"
    assert "不支持的计算器类型" in unknown.warnings[0]
