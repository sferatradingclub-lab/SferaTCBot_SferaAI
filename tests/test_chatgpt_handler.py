import asyncio
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock


def test_handle_message_prompts_for_text_when_missing(monkeypatch):
    from handlers import common_handlers as ch

    keyboard = object()

    @contextmanager
    def fake_get_db():
        yield SimpleNamespace()

    monkeypatch.setattr(ch, "get_db", fake_get_db)
    monkeypatch.setattr(
        ch,
        "get_user",
        lambda db, user_id: SimpleNamespace(is_banned=False, awaiting_verification=False),
    )
    monkeypatch.setattr(ch, "create_user", lambda db, data: data)
    monkeypatch.setattr(ch, "update_user_last_seen", lambda db, user_id: None)
    monkeypatch.setattr(ch, "get_chatgpt_keyboard", lambda: keyboard)

    prompt_text = (
        "Пожалуйста, отправьте текстовое сообщение для ИИ-ассистента "
        "или завершите диалог с помощью кнопки ниже."
    )

    async def run_test():
        user = SimpleNamespace(id=1, full_name="Tester", username="tester")
        message = SimpleNamespace(text=None, reply_text=AsyncMock())
        initial_history = [{"role": "system", "content": "context"}]
        context = SimpleNamespace(
            user_data={"state": "chatgpt_active", "chat_history": initial_history.copy()},
            bot=SimpleNamespace(send_message=AsyncMock()),
        )
        update = SimpleNamespace(
            effective_user=user,
            message=message,
            effective_chat=SimpleNamespace(id=999),
        )

        await ch.handle_message(update, context)

        message.reply_text.assert_awaited_once()
        awaited_call = message.reply_text.await_args
        assert awaited_call.args == (prompt_text,)
        assert awaited_call.kwargs == {"reply_markup": keyboard}
        assert context.user_data["chat_history"] == initial_history
        assert all(entry.get("content") is not None for entry in context.user_data["chat_history"])

    asyncio.run(run_test())
