from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, AsyncGenerator, Dict, Optional, Sequence
import json
import asyncio

import httpx
from telegram.ext import Application

from config import get_settings
from services.cache_service import ChatGPTCache

settings = get_settings()
logger = settings.logger

_DEFAULT_ERROR_MESSAGE = "Извините, сервис временно перегружен. Пожалуйста, попробуйте позже."
HTTPX_CLIENT_KEY = "httpx_client"


class OpenRouterClient:
    """Инкапсулирует взаимодействие с OpenRouter и circuit breaker."""
    
    def __init__(self, application: Optional[Application]) -> None:
        self._application = application
        self._settings = get_settings()
        self._logger = self._settings.logger
        self._bot_data: Optional[Dict[str, Any]] = None
        self._client: Optional[httpx.AsyncClient] = None
        self._breaker_state: Dict[str, Dict[str, Any]] = {}
        
        if self._application is not None:
            self._bot_data = self._application.bot_data
            if self._bot_data is not None:
                self._client = self._bot_data.get(HTTPX_CLIENT_KEY)
                self._breaker_state = self._bot_data.setdefault("circuit_breaker_state", {})
    
    def _get_available_models(self) -> list[str]:
        available_models: list[str] = []
        
        for configured_model in self._settings.CHATGPT_MODELS:
            state = self._breaker_state.get(configured_model)
            disabled_until = state.get("disabled_until") if isinstance(state, dict) else None
            
            if disabled_until and disabled_until > datetime.now():
                self._logger.warning(
                    "Модель %s временно отключена circuit breaker'ом до %s. Пропускаю.",
                    configured_model,
                    disabled_until.isoformat(),
                )
                continue
            
            available_models.append(configured_model)
        
        if not available_models:
            self._logger.error(
                "Все модели отключены circuit breaker'ом. Нет доступных моделей для запроса."
            )
            raise RuntimeError(
                "Нет доступных моделей OpenRouter из-за срабатывания circuit breaker."
            )
        
        return available_models
    
    async def stream_chat_completion(
        self, history: Sequence[Dict[str, Any]]
    ) -> AsyncGenerator[str, None]:
        """Стримит ответ OpenRouter, управляя circuit breaker."""
        
        # Проверяем кеш перед обращением к API
        for model in self._get_available_models():
            cached_response = ChatGPTCache.get_cached_response(list(history), model)
            if cached_response:
                # Возвращаем кешированный ответ
                yield cached_response
                return
        
        if not self._settings.OPENROUTER_API_KEY:
            yield "Функция ИИ-чата не настроена. Обратитесь к администратору."
            return
        
        if self._application is None:
            self._logger.error(
                "Application контекст отсутствует при попытке обращения к OpenRouter."
            )
            yield _DEFAULT_ERROR_MESSAGE
            return
        
        if self._client is None:
            self._logger.error(
                "HTTPX-клиент не найден в bot_data. Убедитесь, что он был инициализирован в post_init приложения."
            )
            yield _DEFAULT_ERROR_MESSAGE
            return
        
        try:
            available_models = self._get_available_models()
        except RuntimeError as error:
            self._logger.error(str(error))
            raise
        
        url = f"{self._settings.CHATGPT_BASE_URL}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._settings.OPENROUTER_API_KEY}",
            "HTTP-Referer": "https://sferatc.com",
            "X-Title": "SferaTCBot",
        }
        
        unrecoverable_error_detected = False
        full_response = ""  # Для кеширования полного ответа
        
        for model in available_models:
            if model not in self._breaker_state:
                self._breaker_state[model] = {"failures": 0, "disabled_until": None}
            
            model_state = self._breaker_state[model]
            
            current_time = datetime.now()
            
            if model_state.get("disabled_until") and model_state["disabled_until"] <= current_time:
                model_state["disabled_until"] = None
            
            payload: Dict[str, Any] = {
                "model": model,
                "messages": list(history),
                "stream": True,
            }
            
            try:
                self._logger.info("Пытаюсь использовать модель: %s", model)
                async with self._client.stream(
                    "POST", url, json=payload, headers=headers
                ) as response:
                    try:
                        response.raise_for_status()
                    except httpx.HTTPStatusError:
                        status_code = response.status_code
                        
                        if status_code == 429:
                            self._logger.warning(
                                "Достигнут лимит для модели %s. Переключаюсь на следующую.",
                                model,
                            )
                            continue
                        
                        if 400 <= status_code < 500:
                            if status_code in (401, 402):
                                self._logger.critical(
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
                            
                            self._logger.warning(
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
                            self._logger.warning(
                                "Восстановимая ошибка сервера от API OpenRouter для модели %s: Статус %s, Ответ: %s",
                                model,
                                status_code,
                                response.text,
                            )
                            model_state["failures"] = model_state.get("failures", 0) + 1
                            continue
                        
                        self._logger.error(
                            "Неожиданный ответ от API OpenRouter для модели %s: Статус %s, Ответ: %s",
                            model,
                            status_code,
                            response.text,
                        )
                        model_state["failures"] = model_state.get("failures", 0) + 1
                        continue
                    
                    received_any_chunk = False
                    response_buffer = []  # Буфер для кеширования полного ответа
                    
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
                            self._logger.error(
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
                                self._breaker_state[model] = {
                                    "failures": 0,
                                    "disabled_until": None,
                                }
                            received_any_chunk = True
                            
                            # Добавляем фрагмент в буфер для кеширования
                            response_buffer.append(content_fragment)
                            
                            yield content_fragment
                    
                    if received_any_chunk:
                        # Сохраняем полный ответ в кеш
                        full_response = "".join(response_buffer)
                        ChatGPTCache.cache_response(list(history), model, full_response)
                        
                        # Ответ успешно получен, прекращаем переключение между моделями.
                        return
                    
                    self._logger.warning(
                        "Модель %s завершила поток без текстовых фрагментов. Пробую следующую.",
                        model,
                    )
                    model_state["failures"] = model_state.get("failures", 0) + 1
            except (httpx.RequestError, httpx.TimeoutException) as error:
                self._logger.error(
                    "Ошибка сети при обращении к OpenRouter с моделью %s: %s",
                    model,
                    error,
                )
                model_state["failures"] = model_state.get("failures", 0) + 1
            except Exception as error:  # noqa: BLE001
                self._logger.error(
                    "Непредвиденная ошибка в chatgpt_service с моделью %s: %s",
                    model,
                    error,
                )
                model_state["failures"] = model_state.get("failures", 0) + 1
            
            if model_state.get("failures", 0) >= 3:
                disable_duration = timedelta(minutes=5)
                model_state["disabled_until"] = datetime.now() + disable_duration
                model_state["failures"] = 0
                self._logger.warning(
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
        self._logger.error(str(final_error))
        raise final_error



async def get_chatgpt_response(
    history: Sequence[Dict[str, Any]],
    application: Optional[Application],
) -> AsyncGenerator[str, None]:
    client = OpenRouterClient(application)
    async for chunk in client.stream_chat_completion(history):
        yield chunk
