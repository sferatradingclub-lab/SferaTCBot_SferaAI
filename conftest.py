import json
import os
import sys
from contextlib import asynccontextmanager, contextmanager
from datetime import datetime
from itertools import count
from pathlib import Path
from types import SimpleNamespace
from typing import Callable, Dict, Iterable
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    Filters,
)
from telegram.request import BaseRequest

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("TELEGRAM_TOKEN", "123:TEST")
os.environ.setdefault("ADMIN_CHAT_ID", "123456")
os.environ.setdefault("BOT_USERNAME", "sferatc_bot")

from handlers import admin_handlers, decorators, verification_handlers
from handlers.common_handlers import handle_message, start
from handlers.verification_handlers import user_actions_handler
from models.base import Base


class DummyRequest(BaseRequest):
    async def initialize(self) -> None:  # pragma: no cover - trivial
        return None

    async def shutdown(self) -> None:  # pragma: no cover - trivial
        return None

    async def do_request(self, url: str, method: str, request_data=None, **kwargs):  # noqa: ANN001
        if url.endswith("getMe"):
            payload: Dict[str, object] = {
                "ok": True,
                "result": {
                    "id": 999999,
                    "is_bot": True,
                    "first_name": "TestBot",
                    "username": os.environ.get("BOT_USERNAME", "sferatc_bot"),
                    "can_join_groups": True,
                    "can_read_all_group_messages": False,
                    "supports_inline_queries": False,
                },
            }
        else:
            payload = {"ok": True, "result": True}
        return 200, json.dumps(payload).encode()


@pytest.fixture
def admin_id() -> int:
    return int(os.environ["ADMIN_CHAT_ID"])


@pytest.fixture
def sqlite_session_factory(monkeypatch):
    engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False})
    testing_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    @contextmanager
    def _get_db():
        db = testing_session()
        try:
            yield db
        finally:
            db.close()

    monkeypatch.setattr("db_session.get_db", _get_db)
    monkeypatch.setattr(decorators, "get_db", _get_db)
    monkeypatch.setattr(verification_handlers, "get_db", _get_db)
    monkeypatch.setattr(admin_handlers, "get_db", _get_db)

    try:
        yield testing_session
    finally:
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def application_bundle(monkeypatch, sqlite_session_factory):
    @asynccontextmanager
    async def _context():
        application = (
            ApplicationBuilder()
            .token(os.environ["TELEGRAM_TOKEN"])
            .updater(None)
            .request(DummyRequest())
            .build()
        )

        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("admin", admin_handlers.show_admin_panel))
        application.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
        application.add_handler(CallbackQueryHandler(user_actions_handler, pattern="^user_"))
        application.add_handler(CallbackQueryHandler(admin_handlers.admin_menu_handler, pattern="^admin_"))
        application.add_handler(CallbackQueryHandler(admin_handlers.broadcast_confirmation_handler, pattern="^broadcast_"))

        await application.initialize()
        await application.start()

        id_counter = count(1000)

        async def _send_message_stub(*args, **kwargs):  # noqa: ANN001
            return SimpleNamespace(message_id=next(id_counter))

        async def _copy_message_stub(*args, **kwargs):  # noqa: ANN001
            return SimpleNamespace(message_id=next(id_counter))

        send_message_mock = AsyncMock(side_effect=_send_message_stub)
        copy_message_mock = AsyncMock(side_effect=_copy_message_stub)
        edit_message_mock = AsyncMock(side_effect=_send_message_stub)

        object.__setattr__(application.bot, "send_message", send_message_mock)
        object.__setattr__(application.bot, "copy_message", copy_message_mock)
        object.__setattr__(application.bot, "edit_message_text", edit_message_mock)

        bundle = SimpleNamespace(
            app=application,
            send_message=send_message_mock,
            copy_message=copy_message_mock,
            edit_message=edit_message_mock,
        )

        try:
            yield bundle
        finally:
            await application.stop()
            await application.shutdown()

    return _context
