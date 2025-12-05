"""
Search tools for Sfera AI agent.
Internet search and video search functionality.
"""

import os
import asyncio
import logging
from livekit.agents import function_tool, RunContext
import aiohttp
from duckduckgo_search import DDGS
from error_handler_decorator import handle_tool_error

logger = logging.getLogger(__name__)


@function_tool()
@handle_tool_error(default_response="Не удалось выполнить поиск в интернете.")
async def search_internet(
    context: RunContext,
    query: str,
    result_type: str = "text",
    multiple: bool = False
) -> str:
    """
    Поиск текстовой информации или ссылок в интернете.
    
    Args:
        query: Запрос пользователя
        result_type: 'text' для текстовых ответов (проговорить), 'link' для ссылок (не проговаривать)
        multiple: True = 3 результата, False = 1 результат
    """
    num_results = 3 if multiple else 1
    logger.info(f"🔍 INTERNET SEARCH: '{query}' | Type: {result_type} | Multiple: {multiple} | Results: {num_results}")
    
    api_key = os.getenv("GOOGLE_API_KEY")
    search_engine_id = os.getenv("GOOGLE_CSE_ID")
    
    if not api_key or not search_engine_id:
        return "ОШИБКА: Поиск не настроен."
    
    timeout = aiohttp.ClientTimeout(total=8)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        params = {
            'key': api_key,
            'cx': search_engine_id,
            'q': query,
            'num': num_results + 2
        }
        
        async with session.get("https://www.googleapis.com/customsearch/v1", params=params) as response:
            if response.status != 200:
                return "ОШИБКА: Поисковый сервис недоступен."
            
            data = await response.json()
            items = data.get('items', [])
            
            if not items:
                return f"РЕЗУЛЬТАТ: Ничего не найдено по запросу '{query}'."
            
            items = items[:num_results]
            
            if result_type == "link":
                response_text = "[SYSTEM COMMAND: НАЙДЕНЫ ССЫЛКИ]\n"
                response_text += "ИНСТРУКЦИЯ: Скажи 'Я скинула ссылку в чат'\n\n"
                
                for i, item in enumerate(items, 1):
                    title = item.get('title', 'Без названия')
                    link = item.get('link', '#')
                    response_text += f"{i}. {title}\n{link}\n\n"
                
                return response_text
            else:
                response_text = "[SYSTEM COMMAND: НАЙДЕНА ИНФОРМАЦИЯ]\n"
                response_text += "ИНСТРУКЦИЯ: Скажи 'Посмотри, я отправила тебе в чат то, что ты просил' и проговори информацию\n\n"
                
                for i, item in enumerate(items, 1):
                    title = item.get('title', 'Без названия')
                    snippet = item.get('snippet', 'Нет описания')
                    link = item.get('link', '')
                    
                    response_text += f"\n{i}. {title}\n"
                    response_text += f"   {snippet}\n"
                    response_text += f"   Источник: {link}\n"
                
                return response_text


@function_tool()
@handle_tool_error(default_response="Не удалось найти видео.")
async def search_video(
    context: RunContext,
    query: str,
    multiple: bool = False
) -> str:
    """
    Поиск видео на YouTube.
    
    Args:
        query: Запрос для поиска видео
        multiple: True = 3 видео, False = 1 видео
    """
    num_videos = 3 if multiple else 1
    logger.info(f"📺 VIDEO SEARCH: '{query}' | Multiple: {multiple}")
    
    loop = asyncio.get_event_loop()
    
    def _search():
        with DDGS() as ddgs:
            return list(ddgs.videos(
                keywords=query,
                region="wt-wt",
                safesearch="off",
                max_results=num_videos + 2
            ))
    
    videos = await loop.run_in_executor(None, _search)
    
    if not videos:
        return f"РЕЗУЛЬТАТ: Видео не найдены по запросу '{query}'."
    
    videos = videos[:num_videos]
    
    response_text = "[SYSTEM COMMAND: НАЙДЕНЫ ВИДЕО]\n"
    
    if len(videos) == 1:
        video_title = videos[0].get('title', 'Без названия')
        response_text += f"ИНСТРУКЦИЯ: Скажи 'Я скинула видео \"{video_title}\" в чат'\n\n"
    else:
        response_text += "ИНСТРУКЦИЯ: Скажи 'Я скинула видео в чат'\n\n"
    
    for i, video in enumerate(videos, 1):
        title = video.get('title', 'Без названия')
        link = video.get('content', '#')
        
        response_text += f"{i}. {title}\n"
        response_text += f"   URL: {link}\n\n"
    
    return response_text