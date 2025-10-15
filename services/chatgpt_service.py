from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, AsyncGenerator, Dict, Optional, Sequence

import json

import httpx
from telegram.ext import Application

from config import get_settings

settings = get_settings()
logger = settings.logger

_DEFAULT_ERROR_MESSAGE = "Извините, сервис временно перегружен. Пожалуйста, попробуйте позже."
HTTPX_CLIENT_KEY = "httpx_client"


async def get_chatgpt_response(
    history: Sequence[Dict[str, Any]],
    application: Optional[Application],
) -> AsyncGenerator[str, None]:
    """Отправляет историю диалога в OpenRouter, переключаясь между моделями при ошибках."""

    if not settings.OPENROUTER_API_KEY:
        yield "Функция ИИ-чата не настроена. Обратитесь к администратору."
        return

    if application is None:
        logger.error("Application контекст отсутствует при попытке обращения к OpenRouter.")
        yield _DEFAULT_ERROR_MESSAGE
        return

    client: Optional[httpx.AsyncClient] = application.bot_data.get(HTTPX_CLIENT_KEY)

    if client is None:
        logger.error(
            "HTTPX-клиент не найден в bot_data. Убедитесь, что он был инициализирован в post_init приложения."
        )
        yield _DEFAULT_ERROR_MESSAGE
        return

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
        # "X-Title" должен быть строго ASCII-строкой, иначе httpx поднимет LocalProtocolError.
        # Используем статическое значение, чтобы исключить любые нелатинские символы
        # (например, из названий чатов), попадающие в заголовок.
        "X-Title": "SferaTCBot",
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
            "stream": True,
        }

        try:
            logger.info("Пытаюсь использовать модель: %s", model)
            async with client.stream("POST", url, json=payload, headers=headers) as response:
                try:
                    response.raise_for_status()
                except httpx.HTTPStatusError:
                    status_code = response.status_code

                    if status_code == 429:
                        logger.warning(
                            "Достигнут лимит для модели %s. Переключаюсь на следующую.",
                            model,
                        )
                        continue

                    if 400 <= status_code < 500:
                        if status_code in (401, 402):
                            logger.critical(
                                (
                                    "Критическая ошибка авторизации при обращении к API OpenRouter для модели %s: "
                                    "Статус %s, Ответ: %s. Проверьте валидность API-ключа и наличие средств."
                                ),
                                model,
                                status_code,
                                response.text,
                            )
                            unrecoverable_error_detected = True
                            break

                        logger.warning(
                            (
                                "Ошибка клиента от API OpenRouter для модели %s: Статус %s, Ответ: %s. "
                                "Пробую следующую модель."
                            ),
                            model,
                            status_code,
                            response.text,
                        )
                        continue

                    if 500 <= status_code < 600:
                        logger.warning(
                            "Восстановимая ошибка сервера от API OpenRouter для модели %s: Статус %s, Ответ: %s",
                            model,
                            status_code,
                            response.text,
                        )
                        model_state["failures"] = model_state.get("failures", 0) + 1
                        continue

                    logger.error(
                        "Неожиданный ответ от API OpenRouter для модели %s: Статус %s, Ответ: %s",
                        model,
                        status_code,
                        response.text,
                    )
                    model_state["failures"] = model_state.get("failures", 0) + 1
                    continue

                received_any_chunk = False

                async for line in response.aiter_lines():
                    if not line:
                        continue

                    if line.startswith(":"):
                        # Комментарии SSE начинаются с двоеточия. Пропускаем такие строки.
                        continue

                    if not line.startswith("data:"):
                        continue

                    data_payload = line[len("data:") :].strip()

                    if not data_payload or data_payload == "[DONE]":
                        # Пустая строка или специальный маркер [DONE] сигнализируют об окончании потока.
                        break

                    try:
                        event_data = json.loads(data_payload)
                    except json.JSONDecodeError as error:
                        logger.error(
                            "Не удалось распарсить SSE-данные от модели %s: %s. Ошибка: %s",
                            model,
                            data_payload,
                            error,
                        )
                        continue

                    choices = event_data.get("choices")
                    if not isinstance(choices, list):
                        continue

                    for choice in choices:
                        delta = choice.get("delta") if isinstance(choice, dict) else None
                        if not isinstance(delta, dict):
                            continue

                        content_fragment = delta.get("content")
                        if not content_fragment:
                            continue

                        if not received_any_chunk:
                            breaker_state[model] = {"failures": 0, "disabled_until": None}
                        received_any_chunk = True
                        yield content_fragment

                if received_any_chunk:
                    # Ответ успешно получен, прекращаем переключение между моделями.
                    return

                logger.warning(
                    "Модель %s завершила поток без текстовых фрагментов. Пробую следующую.",
                    model,
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
