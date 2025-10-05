from typing import Union
import httpx
from config import logger, CHATGPT_BASE_URL, CHATGPT_MODELS, OPENROUTER_API_KEY

async def get_chatgpt_response(history: list) -> Union[str, None]:
    """
    Отправляет историю диалога в OpenRouter, используя список моделей с автоматическим переключением при ошибках.
    """
    if not OPENROUTER_API_KEY:
        return "Функция ИИ-чата не настроена. Обратитесь к администратору."

    url = f"{CHATGPT_BASE_URL}/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "HTTP-Referer": "https://sferatc.com", # Рекомендуемый заголовок для OpenRouter
        "X-Title": "SferaTC Bot", # Рекомендуемый заголовок для OpenRouter
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
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
                        return data["choices"][0]["message"]["content"]

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
                except Exception as e:
                    logger.error(f"Непредвиденная ошибка в chatgpt_service с моделью {model}: {e}")
                    continue
    except httpx.RequestError as e:
        logger.error(f"Ошибка подключения к OpenRouter при создании клиента: {e}")
    except Exception as e:
        logger.error(f"Непредвиденная ошибка при работе с клиентом OpenRouter: {e}")

    # Если ни одна из моделей не сработала
    logger.error("Все модели из списка не ответили. Не удалось получить ответ.")
    return "Извините, сервис временно перегружен. Пожалуйста, попробуйте позже."
