from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.lawyer_matching import Consultation, Delegation, LawyerProfile
from src.models.lead import Lead
from src.models.user import User
from src.services.acquisition_analytics_service import AcquisitionAnalyticsService


@pytest.mark.asyncio
async def test_acquisition_analytics_funnel_sources_and_lawyer_performance(
    db_session: AsyncSession,
) -> None:
    lawyer_user = User(
        email=f"{uuid4()}@example.com",
        hashed_password="hashed",
        name="Analytics Lawyer",
        role="platform_lawyer",
    )
    client_user = User(
        email=f"{uuid4()}@example.com",
        hashed_password="hashed",
        name="Analytics Client",
    )
    db_session.add_all([lawyer_user, client_user])
    await db_session.flush()

    db_session.add_all(
        [
            Lead(client_name="Lead A", stage="new", source="referral"),
            Lead(client_name="Lead B", stage="contacted", source="web"),
            Lead(client_name="Lead C", stage="won", source="referral"),
            LawyerProfile(
                user_id=lawyer_user.id,
                real_name="Lawyer A",
                license_number=f"LIC-{uuid4()}",
                law_firm="Firm A",
                rating=4.7,
                is_verified=True,
            ),
        ]
    )
    await db_session.flush()

    consultation = Consultation(
        user_id=client_user.id,
        original_description="contract dispute",
        matched_lawyer_id=lawyer_user.id,
    )
    db_session.add(consultation)
    await db_session.flush()

    db_session.add(
        Delegation(
            consultation_id=consultation.id,
            client_id=client_user.id,
            lawyer_id=lawyer_user.id,
            title="Delegation A",
            paid_amount=1200.0,
        )
    )
    await db_session.flush()

    service = AcquisitionAnalyticsService(db_session)

    funnel = await service.get_lead_funnel()
    assert {item["stage"]: item["count"] for item in funnel}["new"] == 1
    assert {item["stage"]: item["count"] for item in funnel}["won"] == 1

    conversion = await service.get_conversion_rates()
    assert conversion[0] == {
        "from_stage": "new",
        "to_stage": "contacted",
        "from_count": 1,
        "to_count": 1,
        "rate": 1.0,
    }

    sources = await service.get_lead_sources()
    assert sources[0] == {"source": "referral", "count": 2}

    performance = await service.get_lawyer_performance()
    assert performance == [
        {
            "lawyer_profile_id": performance[0]["lawyer_profile_id"],
            "lawyer_name": "Lawyer A",
            "law_firm": "Firm A",
            "total_consultations": 1,
            "total_delegations": 1,
            "revenue": 1200.0,
            "avg_rating": 4.7,
        }
    ]
