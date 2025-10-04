import asyncio
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock


def test_ensure_manual_support_state_clears_history_once():
    from handlers.common_handlers import _ensure_manual_support_state

    context = SimpleNamespace(user_data={'state': 'support_llm_active', 'support_llm_history': ['history']})

    first_transition = _ensure_manual_support_state(context)
    assert first_transition is True
    assert 'support_llm_history' not in context.user_data
    assert context.user_data['state'] == 'awaiting_support_message'

    context.user_data['support_llm_history'] = ['keep']
    second_transition = _ensure_manual_support_state(context)
    assert second_transition is False
    assert context.user_data['support_llm_history'] == ['keep']


def test_support_messages_forwarded_while_state_active(monkeypatch):
    from handlers import verification_handlers as vh

    @contextmanager
    def fake_get_db():
        yield SimpleNamespace()

    monkeypatch.setattr(vh, "get_db", fake_get_db)
    monkeypatch.setattr(vh, "get_user", lambda db, user_id: SimpleNamespace(awaiting_verification=False))

    async def run_test():
        bot = SimpleNamespace(
            copy_message=AsyncMock(side_effect=[SimpleNamespace(message_id=2001), SimpleNamespace(message_id=2002)]),
            send_message=AsyncMock(),
        )

        context = SimpleNamespace(user_data={'state': 'awaiting_support_message', 'support_llm_history': ['keep']}, bot=bot, bot_data={})

        user = SimpleNamespace(id=42, full_name="Test User", username="tester")

        async def send_user_message(message_id: int, text: str):
            message = SimpleNamespace(text=text, message_id=message_id, reply_text=AsyncMock())
            update = SimpleNamespace(effective_user=user, message=message)
            await vh.handle_support_message(update, context)
            return message.reply_text

        first_reply = await send_user_message(10, "Первое сообщение")
        second_reply = await send_user_message(11, "Второе сообщение")

        assert first_reply.await_count == 1
        assert second_reply.await_count == 0
        assert bot.copy_message.await_count == 2
        assert bot.send_message.await_count == 2
        assert context.user_data['state'] == 'awaiting_support_message'
        assert context.user_data['support_llm_history'] == ['keep']
        assert context.user_data['support_thank_you_sent'] is True

    asyncio.run(run_test())
