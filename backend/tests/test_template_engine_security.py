import pytest

from src.services.template_context import inject_template_context
from src.services.template_engine import TemplateEngine, get_template_by_id

from .conftest import create_auth_headers


def _sale_template():
    template = get_template_by_id("sale_purchase")
    assert template is not None
    return template


def _valid_sale_variables(**overrides):
    variables = {
        "goods_name": "服务器",
        "goods_spec": "A100",
        "quantity": 2,
        "unit": "台",
        "unit_price": 1000,
        "total_amount": 2000,
        "payment_method": "full",
        "delivery_date": "2026-05-06",
        "delivery_place": "上海",
        "warranty_period": 12,
        "has_ip_clause": False,
        "dispute_method": "court",
        "court_name": "上海市浦东新区",
        "party_a": {"name": "甲方公司"},
        "party_b": {"name": "乙方公司"},
    }
    variables.update(overrides)
    return variables


def test_template_engine_escapes_markdown_and_html_values():
    rendered = TemplateEngine.render_template(
        _sale_template(),
        _valid_sale_variables(
            goods_name="货物\n## 免责条款<script>alert(1)</script>",
            goods_spec="[点我](https://evil.example)",
        ),
    )

    assert "## 免责条款" not in rendered
    assert "&lt;script&gt;alert\\(1\\)&lt;/script&gt;" in rendered
    assert "\\[点我\\]\\(https://evil.example\\)" in rendered


def test_template_validation_rejects_unsafe_variable_name():
    errors = TemplateEngine.validate_variables(_sale_template(), {"__class__": "x"})

    assert "变量名不安全: __class__" in errors


def test_template_validation_rejects_nested_party_value():
    errors = TemplateEngine.validate_variables(
        _sale_template(),
        {"party_a": {"name": {"raw": "甲方"}}},
    )

    assert "party_a.name 不允许嵌套对象或数组" in errors


@pytest.mark.asyncio
async def test_template_render_api_rejects_select_outside_options(client, test_user):
    response = await client.post(
        "/api/v1/contracts/templates/sale_purchase/render",
        headers=create_auth_headers(test_user),
        json={"variables": _valid_sale_variables(payment_method="wire")},
    )

    assert response.status_code == 422
    assert "付款方式 不是允许的选项" in response.text


@pytest.mark.asyncio
async def test_template_render_api_rejects_oversized_text(client, test_user):
    response = await client.post(
        "/api/v1/contracts/templates/sale_purchase/render",
        headers=create_auth_headers(test_user),
        json={"variables": _valid_sale_variables(goods_name="x" * 501)},
    )

    assert response.status_code == 422
    assert "商品/货物名称 超过长度限制" in response.text


@pytest.mark.asyncio
async def test_template_render_api_returns_escaped_output(client, test_user):
    response = await client.post(
        "/api/v1/contracts/templates/sale_purchase/render",
        headers=create_auth_headers(test_user),
        json={
            "variables": _valid_sale_variables(
                goods_name="<img src=x onerror=alert(1)>",
                goods_spec="[evil](https://evil.example)",
            )
        },
    )

    assert response.status_code == 200
    rendered_text = response.json()["data"]["rendered_text"]
    assert "<img" not in rendered_text
    assert "&lt;img src=x onerror=alert\\(1\\)&gt;" in rendered_text
    assert "\\[evil\\]\\(https://evil.example\\)" in rendered_text


def test_template_context_rejects_unknown_template_id():
    assert inject_template_context("正文", "../../etc/passwd") == "正文"
