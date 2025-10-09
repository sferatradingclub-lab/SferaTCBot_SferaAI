"""Проверки конфигурации, связанной с вебхуками."""

import importlib
import sys

import pytest


def _load_settings(monkeypatch, overrides: dict[str, str | None]):
    """Переинициализирует настройки с заданными переменными окружения."""

    for name in [
        "PORT",
        "WEBHOOK_PORT",
        "WEBHOOK_PATH",
        "WEBHOOK_LISTEN",
        "WEBHOOK_URL",
        "WEBHOOK_SECRET_TOKEN",
        "WEBHOOK_DROP_PENDING_UPDATES",
        "LOG_TO_FILE",
        "LOG_FILE_PATH",
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
    config = importlib.import_module("config")
    config.get_settings.cache_clear()
    return config.get_settings()


def test_webhook_path_defaults_to_token_postfix(monkeypatch):
    settings = _load_settings(monkeypatch, {})
    assert settings.WEBHOOK_PATH == "ABCDE"


def test_custom_webhook_path_is_sanitized(monkeypatch):
    settings = _load_settings(monkeypatch, {"WEBHOOK_PATH": " /custom/path/ "})
    assert settings.WEBHOOK_PATH == "custom/path"


def test_empty_webhook_path_allows_root(monkeypatch):
    settings = _load_settings(monkeypatch, {"WEBHOOK_PATH": ""})
    assert settings.WEBHOOK_PATH == ""


def test_root_webhook_path_from_slash(monkeypatch):
    settings = _load_settings(monkeypatch, {"WEBHOOK_PATH": "/"})
    assert settings.WEBHOOK_PATH == ""


def test_platform_port_has_priority(monkeypatch):
    settings = _load_settings(monkeypatch, {"PORT": "9000", "WEBHOOK_PORT": "8443"})
    assert settings.WEBHOOK_PORT == 9000


def test_invalid_port_values_raise(monkeypatch):
    with pytest.raises(ValueError):
        _load_settings(monkeypatch, {"PORT": "invalid", "WEBHOOK_PORT": "9443"})


def test_invalid_webhook_port_raises(monkeypatch):
    with pytest.raises(ValueError):
        _load_settings(monkeypatch, {"WEBHOOK_PORT": "broken"})


def test_default_port_used_when_not_set(monkeypatch):
    settings = _load_settings(monkeypatch, {})
    assert settings.WEBHOOK_PORT == 8443


def test_drop_pending_updates_flag(monkeypatch):
    settings = _load_settings(monkeypatch, {"WEBHOOK_DROP_PENDING_UPDATES": "false"})
    assert settings.WEBHOOK_DROP_PENDING_UPDATES is False
