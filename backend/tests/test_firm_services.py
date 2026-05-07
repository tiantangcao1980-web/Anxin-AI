from datetime import date

import pytest

from src.models.firm_management import TimeEntry
from src.services.billing_service import BillingService
from src.services.team_service import TeamService
from src.services.timesheet_service import TimesheetService


@pytest.mark.asyncio
async def test_timesheet_summary_counts_only_approved_entries(db_session, test_user):
    approved = TimeEntry(
        user_id=test_user.id,
        date=date.today(),
        minutes=120,
        billable=True,
        rate=300.0,
        status="approved",
    )
    draft = TimeEntry(
        user_id=test_user.id,
        date=date.today(),
        minutes=60,
        billable=True,
        rate=300.0,
        status="draft",
    )
    db_session.add_all([approved, draft])
    await db_session.flush()

    summary = await TimesheetService(db_session).get_summary(user_id=test_user.id)

    assert summary["total_minutes"] == 120
    assert summary["billable_minutes"] == 120
    assert summary["total_amount"] == 600.0
    assert summary["by_user"] == [
        {
            "user_id": test_user.id,
            "minutes": 120,
            "billable_minutes": 120,
            "amount": 600.0,
        }
    ]


@pytest.mark.asyncio
async def test_team_service_add_lists_and_removes_member(
    db_session,
    test_user,
    test_organization,
):
    service = TeamService(db_session)
    team = await service.create_team(
        org_id=test_organization.id,
        name="诉讼团队",
    )

    member = await service.add_member(team["id"], test_user.id, role="member")
    members = await service.list_members(team["id"])
    removed = await service.remove_member(team["id"], test_user.id)
    members_after_remove = await service.list_members(team["id"])

    assert member["user_id"] == test_user.id
    assert [item["user_id"] for item in members] == [test_user.id]
    assert removed is True
    assert members_after_remove == []


@pytest.mark.asyncio
async def test_billing_service_invoice_lifecycle_and_revenue_report(
    db_session,
    test_organization,
):
    service = BillingService(db_session)

    paid_invoice = await service.create_invoice(
        org_id=test_organization.id,
        client_name="客户A",
        items=[{"description": "咨询", "hours": 1, "rate": 100, "amount": 100}],
    )
    sent_invoice = await service.create_invoice(
        org_id=test_organization.id,
        client_name="客户B",
        items=[{"description": "审查", "hours": 2, "rate": 100, "amount": 200}],
    )

    await service.update_invoice_status(paid_invoice["id"], "paid")
    await service.update_invoice_status(sent_invoice["id"], "sent")

    invoices = await service.list_invoices(org_id=test_organization.id)
    report = await service.get_revenue_report(org_id=test_organization.id)

    assert {invoice["number"] for invoice in invoices} == {
        paid_invoice["number"],
        sent_invoice["number"],
    }
    assert report["total_revenue"] == 300.0
    assert report["paid_amount"] == 100.0
    assert report["pending_amount"] == 200.0
    assert {item["status"]: item["amount"] for item in report["by_status"]} == {
        "paid": 100.0,
        "sent": 200.0,
    }
    assert report["by_month"][0]["amount"] == 100.0
