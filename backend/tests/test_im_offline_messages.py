from uuid import uuid4

import pytest
from sqlalchemy import select

from src.models.im import IMMessage, IMParticipant
from src.models.user import User
from src.services.im_service import IMService


@pytest.mark.asyncio
async def test_im_offline_messages_after_ack_and_ack_updates_read_state(
    db_session,
    test_user,
    test_organization,
):
    other_user = User(
        id=str(uuid4()),
        email=f"im-other-{uuid4().hex[:8]}@example.com",
        name="IM 对方用户",
        hashed_password="hashed_password",
        org_id=test_organization.id,
        is_active=True,
    )
    db_session.add(other_user)
    await db_session.flush()

    service = IMService(db_session)
    conversation = await service.create_conversation(
        type="private",
        creator_id=test_user.id,
        participant_ids=[other_user.id],
    )
    first = await service.send_message(
        conversation_id=conversation.id,
        sender_id=other_user.id,
        content="第一条离线消息",
    )
    second = await service.send_message(
        conversation_id=conversation.id,
        sender_id=other_user.id,
        content="第二条离线消息",
    )

    offline = await service.get_offline_messages(
        test_user.id,
        last_ack_message_id=first["id"],
    )

    assert [message["id"] for message in offline] == [second["id"]]
    assert await service.ack_message(second["id"], test_user.id) is True

    participant = (
        await db_session.execute(
            select(IMParticipant).where(
                IMParticipant.conversation_id == conversation.id,
                IMParticipant.user_id == test_user.id,
            )
        )
    ).scalar_one()
    message = await db_session.get(IMMessage, second["id"])

    assert participant.unread_count == 0
    assert participant.last_read_at == message.created_at
    assert test_user.id in message.read_by


@pytest.mark.asyncio
async def test_im_ack_rejects_non_participant_message(
    db_session,
    test_user,
    test_organization,
):
    sender = User(
        id=str(uuid4()),
        email=f"im-sender-{uuid4().hex[:8]}@example.com",
        name="IM 发送方",
        hashed_password="hashed_password",
        org_id=test_organization.id,
        is_active=True,
    )
    receiver = User(
        id=str(uuid4()),
        email=f"im-receiver-{uuid4().hex[:8]}@example.com",
        name="IM 接收方",
        hashed_password="hashed_password",
        org_id=test_organization.id,
        is_active=True,
    )
    db_session.add_all([sender, receiver])
    await db_session.flush()

    service = IMService(db_session)
    conversation = await service.create_conversation(
        type="private",
        creator_id=sender.id,
        participant_ids=[receiver.id],
    )
    message = await service.send_message(
        conversation_id=conversation.id,
        sender_id=sender.id,
        content="仅参与者可 ACK",
    )

    assert await service.ack_message(message["id"], test_user.id) is False
