import pytest

from src.services.batch_document_service import BatchDocumentService


@pytest.mark.asyncio
async def test_batch_document_service_renders_property_letters():
    service = BatchDocumentService()

    job = service.create_batch_job(
        "property_demand_letter",
        recipients=[
            {
                "owner_name": "张三",
                "unit_number": "1-101",
                "overdue_amount": "5000",
                "overdue_period": "2025年1月至3月",
            },
            {
                "owner_name": "李四",
                "unit_number": "2-202",
                "overdue_amount": "3200",
                "overdue_period": "2025年2月至4月",
            },
        ],
        common_context={
            "property_company": "安心物业",
            "property_address": "安心小区",
            "contact_phone": "400-000-0000",
            "date": "2026年05月07日",
        },
    )

    completed = await service.execute_batch(job.job_id)
    markdown = service.get_job_results_markdown(job.job_id)

    assert completed.status == "done"
    assert completed.completed == 2
    assert completed.progress == 1
    assert all(item.status == "done" for item in completed.items)
    assert "张三" in completed.items[0].content
    assert "安心物业" in completed.items[0].content
    assert "第 2 份 — 李四" in markdown


def test_batch_document_service_lists_templates_and_rejects_unknown_type():
    service = BatchDocumentService()

    templates = service.get_available_templates()

    assert any(item["type"] == "property_demand_letter" for item in templates)
    with pytest.raises(ValueError, match="不支持的模板类型"):
        service.create_batch_job("unknown", [])
