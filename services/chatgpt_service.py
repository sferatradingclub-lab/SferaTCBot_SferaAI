import asyncio
from typing import Union

import httpx

from config import logger, CHATGPT_BASE_URL, CHATGPT_MODELS, OPENROUTER_API_KEY

_async_client: httpx.AsyncClient | None = None
try:
    _client_lock = asyncio.Lock()
except RuntimeError:
    _client_lock = None


async def get_async_client() -> httpx.AsyncClient:
    """Лениво создаёт и возвращает общий экземпляр AsyncClient."""
    global _async_client, _client_lock

    if _client_lock is None:
        _client_lock = asyncio.Lock()

    if _async_client is None:
        async with _client_lock:
            if _async_client is None:
                _async_client = httpx.AsyncClient(timeout=60.0)

    return _async_client


async def close_chatgpt_client() -> None:
    """Закрывает общий AsyncClient и обнуляет ссылку."""
    global _async_client, _client_lock

    if _client_lock is None:
        _client_lock = asyncio.Lock()

    async with _client_lock:
        client = _async_client
        _async_client = None

    if client is None:
        return

    try:
        await client.aclose()
    except Exception as exc:  # noqa: BLE001
        logger.error(f"Не удалось корректно закрыть AsyncClient OpenRouter: {exc}")


async def get_chatgpt_response(history: list) -> Union[str, None]:
    """
    Отправляет историю диалога в OpenRouter, используя список моделей с автоматическим переключением при ошибках.
    """
    if not OPENROUTER_API_KEY:
        return "Функция ИИ-чата не настроена. Обратитесь к администратору."

    url = f"{CHATGPT_BASE_URL}/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "HTTP-Referer": "https://sferatc.com",  # Рекомендуемый заголовок для OpenRouter
        "X-Title": "SferaTC Bot",  # Рекомендуемый заголовок для OpenRouter
    }

    try:
        client = await get_async_client()
    except httpx.RequestError as e:
        logger.error(f"Ошибка подключения к OpenRouter при создании клиента: {e}")
        client = None
    except Exception as e:  # noqa: BLE001
        logger.error(f"Непредвиденная ошибка при работе с клиентом OpenRouter: {e}")
        client = None

    if client is None:
        logger.error("Не удалось получить клиент OpenRouter.")
        return "Извините, сервис временно перегружен. Пожалуйста, попробуйте позже."

    # Пробуем каждую модель из списка по очереди
    for model in CHATGPT_MODELS:
        payload = {
            "model": model,
            "messages": history,
        }

        try:
            logger.info(f"Пытаюсь использовать модель: {model}")
            response = await client.post(url, json=payload, headers=headers)

            # Если запрос успешен, возвращаем результат
            if response.status_code == 200:
                data = response.json()
                choices = data.get("choices") if isinstance(data, dict) else None

                if not isinstance(choices, list) or not choices:
                    logger.error(
                        f"Ответ от модели {model} не содержит массива choices или он пуст: {data}"
                    )
                    continue

                try:
                    return choices[0]["message"]["content"]
                except (KeyError, IndexError) as e:
                    logger.error(
                        f"Ответ от модели {model} не содержит ожидаемых ключей message/content: {e}"
                    )
                    continue

            # Если достигнут лимит запросов, пробуем следующую модель
            elif response.status_code == 429:
                logger.warning(f"Достигнут лимит для модели {model}. Переключаюсь на следующую.")
                continue

            # В случае другой ошибки, логируем и пробуем следующую модель
            else:
                logger.error(
                    f"Ошибка от API OpenRouter для модели {model}: Статус {response.status_code}, Ответ: {response.text}"
                )
                continue

        except httpx.RequestError as e:
            logger.error(f"Ошибка подключения к OpenRouter с моделью {model}: {e}")
            continue
        except Exception as e:  # noqa: BLE001
            logger.error(f"Непредвиденная ошибка в chatgpt_service с моделью {model}: {e}")
            continue

    # Если ни одна из моделей не сработала
    logger.error("Все модели из списка не ответили. Не удалось получить ответ.")
    return "Извините, сервис временно перегружен. Пожалуйста, попробуйте позже."
