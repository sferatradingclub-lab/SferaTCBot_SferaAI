"""Тесты для модуля db_session."""

from db_session import SessionLocal, get_db


def test_get_db_uses_session_local_configuration():
    """Убедиться, что get_db создает сессии с конфигурацией SessionLocal."""
    baseline_session = SessionLocal()
    try:
        with get_db() as session:
            assert session.bind is baseline_session.bind
            assert session.autoflush is baseline_session.autoflush
            assert type(session) is type(baseline_session)
    finally:
        baseline_session.close()
