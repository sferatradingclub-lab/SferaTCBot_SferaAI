from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Sequence, Union

import httpx
from telegram.ext import Application

from config import get_settings

settings = get_settings()
logger = settings.logger

_DEFAULT_ERROR_MESSAGE = "Извините, сервис временно перегружен. Пожалуйста, попробуйте позже."
HTTPX_CLIENT_KEY = "httpx_client"


def _extract_message_content(response_data: Dict[str, Any], model: str) -> Optional[str]:
    choices = response_data.get("choices") if isinstance(response_data, dict) else None

    if not isinstance(choices, list) or not choices:
        logger.error(
            "Ответ от модели %s не содержит массива choices или он пуст: %s",
            model,
            response_data,
        )
        return None

    try:
        return choices[0]["message"]["content"]
    except (KeyError, IndexError) as error:
        logger.error(
            "Ответ от модели %s не содержит ожидаемых ключей message/content: %s",
            model,
            error,
        )
        return None


async def get_chatgpt_response(
    history: Sequence[Dict[str, Any]],
    application: Optional[Application],
) -> Union[str, None]:
    """Отправляет историю диалога в OpenRouter, переключаясь между моделями при ошибках."""

    if not settings.OPENROUTER_API_KEY:
        return "Функция ИИ-чата не настроена. Обратитесь к администратору."

    if application is None:
        logger.error("Application контекст отсутствует при попытке обращения к OpenRouter.")
        return _DEFAULT_ERROR_MESSAGE

    client: Optional[httpx.AsyncClient] = application.bot_data.get(HTTPX_CLIENT_KEY)

    if client is None:
        logger.error(
            "HTTPX-клиент не найден в bot_data. Убедитесь, что он был инициализирован в post_init приложения."
        )
        return _DEFAULT_ERROR_MESSAGE

    if "circuit_breaker_state" not in application.bot_data:
        application.bot_data["circuit_breaker_state"] = {}

    breaker_state: Dict[str, Dict[str, Any]] = application.bot_data["circuit_breaker_state"]
    available_models: list[str] = []

    for configured_model in settings.CHATGPT_MODELS:
        state = breaker_state.get(configured_model)
        disabled_until = state.get("disabled_until") if isinstance(state, dict) else None

        if disabled_until and disabled_until > datetime.now():
            logger.warning(
                "Модель %s временно отключена circuit breaker'ом до %s. Пропускаю.",
                configured_model,
                disabled_until.isoformat(),
            )
            continue

        available_models.append(configured_model)

    if not available_models:
        logger.error("Все модели отключены circuit breaker'ом. Нет доступных моделей для запроса.")
        raise RuntimeError("Нет доступных моделей OpenRouter из-за срабатывания circuit breaker.")

    url = f"{settings.CHATGPT_BASE_URL}/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
        "HTTP-Referer": "https://sferatc.com",
        "X-Title": "SferaTC Bot",
    }

    unrecoverable_error_detected = False

    for model in available_models:
        if model not in breaker_state:
            breaker_state[model] = {"failures": 0, "disabled_until": None}

        model_state = breaker_state[model]

        current_time = datetime.now()

        if model_state.get("disabled_until") and model_state["disabled_until"] <= current_time:
            model_state["disabled_until"] = None

        payload: Dict[str, Any] = {
            "model": model,
            "messages": list(history),
        }

        try:
            logger.info("Пытаюсь использовать модель: %s", model)
            response = await client.post(url, json=payload, headers=headers)

            if response.status_code == 200:
                content = _extract_message_content(response.json(), model)
                if content:
                    breaker_state[model] = {"failures": 0, "disabled_until": None}
                    return content
                continue

            if response.status_code == 429:
                logger.warning("Достигнут лимит для модели %s. Переключаюсь на следующую.", model)
                continue

            if 400 <= response.status_code < 500:
                logger.error(
                    "Невосстановимая ошибка клиента от API OpenRouter для модели %s: Статус %s, Ответ: %s",
                    model,
                    response.status_code,
                    response.text,
                )
                logger.critical("Unrecoverable client error for model %s. Прерываю попытки.", model)
                unrecoverable_error_detected = True
                break

            if 500 <= response.status_code < 600:
                logger.warning(
                    "Восстановимая ошибка сервера от API OpenRouter для модели %s: Статус %s, Ответ: %s",
                    model,
                    response.status_code,
                    response.text,
                )
                model_state["failures"] = model_state.get("failures", 0) + 1
            else:
                logger.error(
                    "Неожиданный ответ от API OpenRouter для модели %s: Статус %s, Ответ: %s",
                    model,
                    response.status_code,
                    response.text,
                )
                model_state["failures"] = model_state.get("failures", 0) + 1
        except (httpx.RequestError, httpx.TimeoutException) as error:
            logger.error("Ошибка сети при обращении к OpenRouter с моделью %s: %s", model, error)
            model_state["failures"] = model_state.get("failures", 0) + 1
        except Exception as error:  # noqa: BLE001
            logger.error("Непредвиденная ошибка в chatgpt_service с моделью %s: %s", model, error)
            model_state["failures"] = model_state.get("failures", 0) + 1

        if model_state.get("failures", 0) >= 3:
            disable_duration = timedelta(minutes=5)
            model_state["disabled_until"] = datetime.now() + disable_duration
            model_state["failures"] = 0
            logger.warning(
                "Circuit breaker сработал для модели %s. Модель отключена на %s минут.",
                model,
                disable_duration.total_seconds() / 60,
            )

    if unrecoverable_error_detected:
        final_error_message = (
            "Запрос к OpenRouter отклонён как некорректный. Проверьте формирование сообщений для модели."
        )
    else:
        final_error_message = (
            "Все модели API из списка не ответили. Не удалось получить ответ от OpenRouter."
        )

    final_error = RuntimeError(final_error_message)
    logger.error(str(final_error))
    raise final_error
