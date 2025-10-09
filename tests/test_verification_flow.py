import asyncio
from datetime import datetime

from telegram import Update

from models.user import User


def _command_entities(command_text: str) -> list[dict[str, object]]:
    command = command_text.split()[0]
    return [{"offset": 0, "length": len(command), "type": "bot_command"}]


def build_message_update(
    bundle,
    *,
    update_id: int,
    chat_id: int,
    text: str,
    message_id: int,
    first_name: str,
) -> Update:
    data = {
        "update_id": update_id,
        "message": {
            "message_id": message_id,
            "date": int(datetime.now().timestamp()),
            "chat": {"id": chat_id, "type": "private", "first_name": first_name},
            "from": {"id": chat_id, "is_bot": False, "first_name": first_name},
            "text": text,
        },
    }
    if text.startswith("/"):
        data["message"]["entities"] = _command_entities(text)
    return Update.de_json(data=data, bot=bundle.app.bot)


def build_callback_query_update(
    bundle,
    *,
    update_id: int,
    from_id: int,
    data: str,
    message_text: str,
    message_id: int,
    first_name: str,
) -> Update:
    payload = {
        "update_id": update_id,
        "callback_query": {
            "id": f"cq-{update_id}",
            "from": {"id": from_id, "is_bot": False, "first_name": first_name},
            "chat_instance": "test-chat-instance",
            "data": data,
            "message": {
                "message_id": message_id,
                "date": int(datetime.now().timestamp()),
                "chat": {"id": from_id, "type": "private", "first_name": first_name},
                "text": message_text,
            },
        },
    }
    return Update.de_json(data=payload, bot=bundle.app.bot)


def _chat_id_from_call(call) -> int | None:
    value = call.kwargs.get("chat_id")
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def test_user_verification_lifecycle(application_bundle, sqlite_session_factory, admin_id):
    user_id = 424242

    async def scenario():
        async with application_bundle() as bundle:
            app = bundle.app

            start_update = build_message_update(
                bundle,
                update_id=1,
                chat_id=user_id,
                text="/start trial_completed",
                message_id=10,
                first_name="Alice",
            )
            await app.process_update(start_update)

            id_update = build_message_update(
                bundle,
                update_id=2,
                chat_id=user_id,
                text="USER12345",
                message_id=11,
                first_name="Alice",
            )
            await app.process_update(id_update)

            admin_messages = [
                call for call in bundle.send_message.await_args_list if _chat_id_from_call(call) == admin_id
            ]
            assert admin_messages, "Администратор должен получить уведомления"
            verification_call = admin_messages[-1]

            markup = verification_call.kwargs.get("reply_markup")
            assert markup is not None
            buttons = markup.inline_keyboard[0]
            assert [button.text for button in buttons[:2]] == ["✅ Одобрить", "❌ Отклонить"]

            callback_update = build_callback_query_update(
                bundle,
                update_id=3,
                from_id=admin_id,
                data=f"user_approve_{user_id}",
                message_text=verification_call.kwargs["text"],
                message_id=9999,
                first_name="Admin",
            )
            await app.process_update(callback_update)

            user_notifications = [
                call for call in bundle.send_message.await_args_list if _chat_id_from_call(call) == user_id
            ]
            assert any("заявка одобрена" in call.kwargs.get("text", "") for call in user_notifications)

    asyncio.run(scenario())

    session = sqlite_session_factory()
    try:
        db_user = session.query(User).filter_by(user_id=user_id).one()
        assert db_user.is_approved is True
        assert db_user.awaiting_verification is False
    finally:
        session.close()
