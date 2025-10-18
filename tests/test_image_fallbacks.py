import asyncio
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock

from handlers import decorators as handler_decorators
from handlers.states import UserState
from handlers.user import support_handler


def _setup_message():
    return SimpleNamespace(reply_photo=AsyncMock(), reply_text=AsyncMock())


@contextmanager
def _fake_get_db():
    yield SimpleNamespace()


def test_start_fallbacks_to_text_when_no_welcome_image(monkeypatch):
    from handlers import common_handlers as ch

    monkeypatch.setattr(ch, "get_safe_url", lambda url, context: None)
    monkeypatch.setattr(handler_decorators, "get_db", _fake_get_db)
    monkeypatch.setattr(handler_decorators, "get_user", lambda db, user_id: None)
    monkeypatch.setattr(
        handler_decorators,
        "create_user",
        lambda db, data: SimpleNamespace(is_banned=False),
    )
    monkeypatch.setattr(handler_decorators, "update_user_last_seen", lambda db, user_id: None)
    monkeypatch.setattr(ch, "get_channel_keyboard", lambda: "channel_keyboard")
    monkeypatch.setattr(ch, "get_main_menu_keyboard", lambda user_id: f"menu_{user_id}")

    async def run_test():
        message = _setup_message()
        user = SimpleNamespace(
            id=1,
            full_name="Test User",
            username="tester",
            first_name="Test",
        )
        update = SimpleNamespace(effective_user=user, message=message)
        context = SimpleNamespace(
            bot=SimpleNamespace(send_message=AsyncMock()),
            args=[],
            user_data={},
        )

        await ch.start(update, context)

        assert message.reply_photo.await_count == 0
        assert message.reply_text.await_count == 2

        welcome_call = message.reply_text.await_args_list[0]
        assert welcome_call.args == (
            "Привет, Test!\n\n"
            "Добро пожаловать в экосистему SferaTC. Здесь ты найдешь все для успешного старта в трейдинге.\n\n"
            "Чтобы быть в курсе всех обновлений, подпишись на наш основной канал!",
        )
        assert welcome_call.kwargs == {"reply_markup": "channel_keyboard"}

        menu_call = message.reply_text.await_args_list[1]
        assert menu_call.args == ("Выберите действие в меню ниже:",)
        assert menu_call.kwargs == {"reply_markup": "menu_1"}

    asyncio.run(run_test())


def test_training_menu_fallbacks_to_text_when_image_missing(monkeypatch):
    from handlers import common_handlers as ch

    monkeypatch.setattr(ch, "get_safe_url", lambda url, context: None)
    monkeypatch.setattr(handler_decorators, "get_db", _fake_get_db)
    monkeypatch.setattr(
        handler_decorators,
        "get_user",
        lambda db, user_id: SimpleNamespace(is_approved=False, is_banned=False),
    )
    monkeypatch.setattr(
        handler_decorators,
        "create_user",
        lambda db, data: SimpleNamespace(is_approved=False, is_banned=False),
    )
    monkeypatch.setattr(handler_decorators, "update_user_last_seen", lambda db, user_id: None)
    monkeypatch.setattr(
        ch,
        "get_training_keyboard",
        lambda is_approved: f"training_keyboard_{is_approved}",
    )

    async def run_test():
        message = _setup_message()
        update = SimpleNamespace(message=message, effective_user=SimpleNamespace(id=5))
        context = SimpleNamespace(user_data={})

        await ch.show_training_menu(update, context)

        assert message.reply_photo.await_count == 0
        message.reply_text.assert_awaited_once()
        call = message.reply_text.await_args_list[0]
        assert call.args == ("Наше бесплатное обучение проходит в специальном чат-боте на платформе ChatGPT.",)
        assert call.kwargs == {"reply_markup": "training_keyboard_False"}

    asyncio.run(run_test())


def test_psychologist_menu_fallbacks_to_text(monkeypatch):
    from handlers import common_handlers as ch

    monkeypatch.setattr(ch, "get_safe_url", lambda url, context: None)
    monkeypatch.setattr(ch, "get_psychologist_keyboard", lambda: "psych_keyboard")
    monkeypatch.setattr(handler_decorators, "get_db", _fake_get_db)
    monkeypatch.setattr(
        handler_decorators,
        "get_user",
        lambda db, user_id: SimpleNamespace(is_banned=False),
    )
    monkeypatch.setattr(handler_decorators, "create_user", lambda db, data: SimpleNamespace(is_banned=False))
    monkeypatch.setattr(handler_decorators, "update_user_last_seen", lambda db, user_id: None)

    async def run_test():
        message = _setup_message()
        update = SimpleNamespace(
            message=message,
            effective_user=SimpleNamespace(id=12, full_name="Test", username="tester"),
        )
        context = SimpleNamespace(user_data={}, bot=SimpleNamespace(send_message=AsyncMock()))

        await ch.show_psychologist_menu(update, context)

        assert message.reply_photo.await_count == 0
        message.reply_text.assert_awaited_once_with(
            "Наш ИИ-психолог поможет справиться со стрессом в трейдинге.",
            reply_markup="psych_keyboard",
        )

    asyncio.run(run_test())


def test_support_menu_fallbacks_to_text(monkeypatch):
    monkeypatch.setattr(support_handler, "get_safe_url", lambda url, context: None)
    monkeypatch.setattr(
        support_handler, "get_support_llm_keyboard", lambda: "support_keyboard"
    )
    monkeypatch.setattr(handler_decorators, "get_db", _fake_get_db)
    monkeypatch.setattr(
        handler_decorators,
        "get_user",
        lambda db, user_id: SimpleNamespace(is_banned=False),
    )
    monkeypatch.setattr(handler_decorators, "create_user", lambda db, data: SimpleNamespace(is_banned=False))
    monkeypatch.setattr(handler_decorators, "update_user_last_seen", lambda db, user_id: None)

    async def run_test():
        message = _setup_message()
        update = SimpleNamespace(
            message=message,
            effective_user=SimpleNamespace(id=15, full_name="Test", username="tester"),
        )
        context = SimpleNamespace(user_data={}, bot=SimpleNamespace(send_message=AsyncMock()))

        await support_handler.show_support_menu(update, context)

        assert message.reply_photo.await_count == 0
        message.reply_text.assert_awaited_once_with(
            "Я — ИИ-поддержка SferaTC и готов помочь. Опишите проблему текстом, а если понадобится человек, "
            "нажмите кнопку «Позвать администратора».",
            reply_markup="support_keyboard",
        )
        assert context.user_data['state'] == UserState.SUPPORT_LLM_ACTIVE
        assert context.user_data['support_llm_history'][0]["role"] == "system"

    asyncio.run(run_test())
