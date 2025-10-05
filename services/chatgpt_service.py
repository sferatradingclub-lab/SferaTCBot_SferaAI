from typing import Any, Dict, Optional, Sequence, Union

import httpx
from telegram.ext import Application

from config import logger, CHATGPT_BASE_URL, CHATGPT_MODELS, OPENROUTER_API_KEY


_DEFAULT_ERROR_MESSAGE = "Извините, сервис временно перегружен. Пожалуйста, попробуйте позже."


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
    """
    Отправляет историю диалога в OpenRouter, используя список моделей с автоматическим переключением при ошибках.
    HTTP-клиент берётся из bot_data приложения, чтобы избежать конфликтов event loop при работе через вебхуки.
    """
    if not OPENROUTER_API_KEY:
        return "Функция ИИ-чата не настроена. Обратитесь к администратору."

    if application is None:
        logger.error("Application контекст отсутствует при попытке обращения к OpenRouter.")
        return _DEFAULT_ERROR_MESSAGE

    client: Optional[httpx.AsyncClient] = application.bot_data.get("httpx_client")

    if client is None:
        logger.error(
            "HTTPX-клиент не найден в bot_data. Убедитесь, что он был инициализирован в post_init приложения."
        )
        return _DEFAULT_ERROR_MESSAGE

    url = f"{CHATGPT_BASE_URL}/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "HTTP-Referer": "https://sferatc.com",
        "X-Title": "SferaTC Bot",
    }

    for model in CHATGPT_MODELS:
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
                    return content
                continue

            if response.status_code == 429:
                logger.warning("Достигнут лимит для модели %s. Переключаюсь на следующую.", model)
                continue

            logger.error(
                "Ошибка от API OpenRouter для модели %s: Статус %s, Ответ: %s",
                model,
                response.status_code,
                response.text,
            )
        except httpx.RequestError as error:
            logger.error("Ошибка подключения к OpenRouter с моделью %s: %s", model, error)
        except Exception as error:  # noqa: BLE001
            logger.error("Непредвиденная ошибка в chatgpt_service с моделью %s: %s", model, error)

    logger.error("Все модели из списка не ответили. Не удалось получить ответ.")
    return _DEFAULT_ERROR_MESSAGE
