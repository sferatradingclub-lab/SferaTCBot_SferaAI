"""Проверки конфигурации, связанной с вебхуками."""

import importlib
import sys


def _load_config(monkeypatch, overrides: dict[str, str | None]):
    """Переинициализирует модуль config с заданными переменными окружения."""

    # Очистка переменных окружения, которые могут влиять на конфигурацию вебхука.
    for name in [
        "PORT",
        "WEBHOOK_PORT",
        "WEBHOOK_PATH",
        "WEBHOOK_LISTEN",
        "WEBHOOK_URL",
        "WEBHOOK_SECRET_TOKEN",
        "WEBHOOK_DROP_PENDING_UPDATES",
    ]:
        monkeypatch.delenv(name, raising=False)

    defaults = {
        "TELEGRAM_TOKEN": "12345:ABCDE",
        "ADMIN_CHAT_ID": "1",
    }

    for key, value in defaults.items():
        monkeypatch.setenv(key, value)

    for key, value in overrides.items():
        if value is None:
            monkeypatch.delenv(key, raising=False)
        else:
            monkeypatch.setenv(key, value)

    sys.modules.pop("config", None)
    return importlib.import_module("config")


def test_webhook_path_defaults_to_token_postfix(monkeypatch):
    config = _load_config(monkeypatch, {})
    assert config.WEBHOOK_PATH == "ABCDE"


def test_custom_webhook_path_is_sanitized(monkeypatch):
    config = _load_config(monkeypatch, {"WEBHOOK_PATH": " /custom/path/ "})
    assert config.WEBHOOK_PATH == "custom/path"


def test_platform_port_has_priority(monkeypatch):
    config = _load_config(monkeypatch, {"PORT": "9000", "WEBHOOK_PORT": "8443"})
    assert config.WEBHOOK_PORT == 9000


def test_fallback_to_explicit_webhook_port(monkeypatch):
    config = _load_config(monkeypatch, {"PORT": "invalid", "WEBHOOK_PORT": "9443"})
    assert config.WEBHOOK_PORT == 9443


def test_default_port_used_on_invalid_values(monkeypatch):
    config = _load_config(monkeypatch, {"PORT": "invalid", "WEBHOOK_PORT": "broken"})
    assert config.WEBHOOK_PORT == 8443


def test_drop_pending_updates_flag(monkeypatch):
    config = _load_config(monkeypatch, {"WEBHOOK_DROP_PENDING_UPDATES": "false"})
    assert config.WEBHOOK_DROP_PENDING_UPDATES is False
