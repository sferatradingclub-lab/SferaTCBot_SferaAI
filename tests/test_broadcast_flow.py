import asyncio
from datetime import datetime
from unittest.mock import AsyncMock

from telegram import Update

from models.user import User


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
        command = text.split()[0]
        data["message"]["entities"] = [{"offset": 0, "length": len(command), "type": "bot_command"}]
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


def test_admin_broadcast_flow(application_bundle, sqlite_session_factory, admin_id, monkeypatch):
    active_user_ids = [1000 + idx for idx in range(5)]
    banned_user_ids = [2000 + idx for idx in range(2)]

    session = sqlite_session_factory()
    try:
        now = datetime.now()
        for uid in active_user_ids:
            session.add(
                User(
                    user_id=uid,
                    username=f"user{uid}",
                    full_name=f"User {uid}",
                    first_seen=now,
                    last_seen=now,
                    is_banned=False,
                    awaiting_verification=False,
                    is_approved=True,
                )
            )
        for uid in banned_user_ids:
            session.add(
                User(
                    user_id=uid,
                    username=f"banned{uid}",
                    full_name=f"Banned {uid}",
                    first_seen=now,
                    last_seen=now,
                    is_banned=True,
                    awaiting_verification=False,
                    is_approved=False,
                )
            )
        session.commit()
    finally:
        session.close()

    monkeypatch.setattr("handlers.admin_handlers.asyncio.sleep", AsyncMock())

    async def scenario():
        async with application_bundle() as bundle:
            app = bundle.app

            admin_start = build_message_update(
                bundle,
                update_id=10,
                chat_id=admin_id,
                text="/admin",
                message_id=110,
                first_name="Admin",
            )
            await app.process_update(admin_start)

            admin_messages = [
                call for call in bundle.send_message.await_args_list if _chat_id_from_call(call) == admin_id
            ]
            panel_call = admin_messages[-1]

            broadcast_menu = build_callback_query_update(
                bundle,
                update_id=11,
                from_id=admin_id,
                data="admin_broadcast",
                message_text=panel_call.kwargs["text"],
                message_id=210,
                first_name="Admin",
            )
            await app.process_update(broadcast_menu)

            broadcast_content = build_message_update(
                bundle,
                update_id=12,
                chat_id=admin_id,
                text="Важное объявление",
                message_id=120,
                first_name="Admin",
            )
            await app.process_update(broadcast_content)

            preview_calls = bundle.copy_message.await_args_list
            assert preview_calls, "Сообщение предпросмотра должно быть отправлено админу"
            assert _chat_id_from_call(preview_calls[0]) == admin_id
            bundle.copy_message.reset_mock()

            confirmation_candidates = [
                call
                for call in bundle.send_message.await_args_list
                if call.kwargs.get("reply_markup")
                and any(
                    button.callback_data == "broadcast_send"
                    for row in call.kwargs["reply_markup"].inline_keyboard
                    for button in row
                )
            ]
            assert confirmation_candidates, "Ожидалось сообщение с кнопкой подтверждения рассылки"
            confirmation_call = confirmation_candidates[-1]

            confirmation_update = build_callback_query_update(
                bundle,
                update_id=13,
                from_id=admin_id,
                data="broadcast_send",
                message_text=confirmation_call.kwargs["text"],
                message_id=220,
                first_name="Admin",
            )

            send_calls_before_job = len(bundle.send_message.await_args_list)
            await app.process_update(confirmation_update)

            jobs = app.job_queue.jobs()
            assert len(jobs) == 1, "Задача рассылки должна быть запланирована"
            await jobs[0].run(app)

            delivery_calls = [
                call for call in bundle.copy_message.await_args_list if _chat_id_from_call(call) != admin_id
            ]
            assert len(delivery_calls) == len(active_user_ids)
            delivered_ids = {_chat_id_from_call(call) for call in delivery_calls}
            assert delivered_ids == set(active_user_ids)

            new_admin_messages = bundle.send_message.await_args_list[send_calls_before_job:]
            summary_call = next(
                call for call in new_admin_messages if "Рассылка завершена" in call.kwargs.get("text", "")
            )
            assert _chat_id_from_call(summary_call) == admin_id

    asyncio.run(scenario())
