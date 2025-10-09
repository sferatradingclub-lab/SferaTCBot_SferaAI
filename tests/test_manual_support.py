import asyncio
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock

from handlers import decorators as handler_decorators
from handlers.states import UserState


class DummyDBContext:
    def __enter__(self):
        return SimpleNamespace()

    def __exit__(self, exc_type, exc, tb):
        return False


def test_ensure_manual_support_state_detects_first_transition():
    from handlers.common_handlers import _ensure_manual_support_state

    context = SimpleNamespace(
        user_data={
            'state': UserState.SUPPORT_LLM_ACTIVE,
            'support_llm_history': ['history'],
        }
    )

    first_transition = _ensure_manual_support_state(context)
    assert first_transition is True
    assert context.user_data['state'] == UserState.AWAITING_SUPPORT_MESSAGE

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

        context = SimpleNamespace(
            user_data={
                'state': UserState.AWAITING_SUPPORT_MESSAGE,
                'support_llm_history': ['keep'],
            },
            bot=bot,
            bot_data={},
        )

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
        assert context.user_data['state'] == UserState.AWAITING_SUPPORT_MESSAGE
        assert context.user_data['support_llm_history'] == ['keep']
        assert context.user_data['support_thank_you_sent'] is True

    asyncio.run(run_test())


def test_escalation_prompt_sent_once_on_manual_support_transition(monkeypatch):
    from handlers import common_handlers as ch

    async def run_test():
        monkeypatch.setattr(handler_decorators, "get_db", lambda: DummyDBContext())
        monkeypatch.setattr(
            handler_decorators,
            "get_user",
            lambda db, user_id: SimpleNamespace(is_banned=False, awaiting_verification=False),
        )
        monkeypatch.setattr(handler_decorators, "create_user", lambda db, data: data)
        monkeypatch.setattr(handler_decorators, "update_user_last_seen", lambda db, user_id: None)

        context = SimpleNamespace(
            user_data={
                'state': UserState.SUPPORT_LLM_ACTIVE,
                'support_llm_history': ['history'],
                'support_thank_you_sent': True,
            }
        )

        message = SimpleNamespace(
            text="Нужна помощь",
            caption=None,
            reply_text=AsyncMock(),
            edit_reply_markup=AsyncMock(),
            edit_caption=AsyncMock(),
        )

        query = SimpleNamespace(answer=AsyncMock(), message=message)
        update = SimpleNamespace(
            callback_query=query,
            effective_user=SimpleNamespace(id=1, full_name="Tester", username="tester"),
        )

        await ch.escalate_support_to_admin(update, context)

        query.answer.assert_awaited_once()
        message.edit_reply_markup.assert_awaited_once_with(reply_markup=None)
        message.reply_text.assert_awaited_once_with(ch.SUPPORT_ESCALATION_PROMPT)
        assert context.user_data['state'] == UserState.AWAITING_SUPPORT_MESSAGE
        assert 'support_llm_history' not in context.user_data
        assert context.user_data['support_thank_you_sent'] is False

        message.reply_text.reset_mock()
        context.user_data['support_llm_history'] = ['keep']

        await ch.escalate_support_to_admin(update, context)

        message.reply_text.assert_not_awaited()
        assert context.user_data['support_llm_history'] == ['keep']

    asyncio.run(run_test())
