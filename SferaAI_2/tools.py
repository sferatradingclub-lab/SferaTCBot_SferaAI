import asyncio
import logging
import os
import time
from livekit.agents import function_tool, RunContext
import aiohttp
import json
from pydantic import ValidationError

from knowledge_base import query_knowledge_base
from unified_user_state import get_unified_instance
from config import config
from cache_utils import TTLCache, make_cache_key
from error_handler_decorator import handle_tool_error
from russian_numbers import price_to_russian, replace_numbers_in_text
from models.tool_params import (
    CryptoPriceParams,
    WeatherParams,
    StartPlanParams,
    SaveUserNameParams,
    SearchKnowledgeBaseParams
)

# Initialize unified user state client
unified_state = get_unified_instance()

# Initialize caches
web_search_cache = TTLCache(ttl_seconds=600, max_size=50)  # 10 min for web searches
kb_cache = TTLCache(ttl_seconds=1800, max_size=100)  # 30 min for KB
crypto_price_cache = TTLCache(ttl_seconds=30, max_size=100)  # 30 sec for crypto prices

@function_tool()
async def start_plan(
    context: RunContext, # type: ignore
    plan_type: str,
    diagnosis: str,
) -> str:
    """
    Initiates a new multi-day learning or recovery plan for the user.
    Call this ONLY after the user has explicitly agreed to start a plan.
    This tool saves the initial state of the plan to Long-Term Memory.

    Args:
        plan_type (str): The unique identifier for the plan (e.g., '3-Day-Recovery', 'Risk-Management-Module-1').
        diagnosis (str): The reason the plan is being started (e.g., 'revenge_trading', 'knowledge_gap_rsi').
    """
    # Validate with Pydantic
    try:
        params = StartPlanParams(plan_type=plan_type, diagnosis=diagnosis)
        validated_plan_type = params.plan_type
        validated_diagnosis = params.diagnosis
    except ValidationError as e:
        error_msg = e.errors()[0]['msg']
        return f"Ошибка валидации: {error_msg}"
    
    try:
        user_id = config.memory.user_name
        logging.info(f"Starting plan '{validated_plan_type}' for user '{user_id}' with diagnosis '{validated_diagnosis}'.")
        
        initial_state = {
            'active_plan': validated_plan_type,
            'plan_step': 1,
            'diagnosis': validated_diagnosis,
        }
        await unified_state.update_user_state(user_id, initial_state)
        
        confirmation_message = f"План '{validated_plan_type}' был успешно запущен для пользователя {user_id}."
        logging.info(confirmation_message)
        return confirmation_message
    except Exception as e:
        error_message = f"Ошибка при запуске плана: {e}"
        logging.error(error_message)
        return error_message

@function_tool()
async def save_user_name(
    context: RunContext, # type: ignore
    name: str,
) -> str:
    """
    Saves the user's name to their long-term memory profile.
    Call this tool IMMEDIATELY after the user tells you their name for the first time.
    
    Args:
        name (str): The name the user wants to be called.
    """
    # Validate with Pydantic
    try:
        params = SaveUserNameParams(name=name)
        validated_name = params.name
    except ValidationError as e:
        error_msg = e.errors()[0]['msg']
        return f"Ошибка валидации имени: {error_msg}"
    
    try:
        user_id = config.memory.user_name 
        logging.info(f"Saving name '{validated_name}' for user_id '{user_id}'.")
        
        await unified_state.set_user_name(user_id, validated_name)
        
        return f"Имя '{validated_name}' успешно сохранено. Теперь я буду обращаться к вам так."
    except Exception as e:
        logging.error(f"Error saving user name: {e}")
        return "Ошибка при сохранении имени."

@function_tool()
@handle_tool_error(default_response="Не удалось выполнить поиск в базе знаний.")
async def search_knowledge_base(
    context: RunContext,  # type: ignore
    query: str,
    persona: str = "partner",
    filters: str = "{}"
) -> str:
    """
    🔥 ОБЯЗАТЕЛЬНЫЙ инструмент для ЛЮБЫХ вопросов о трейдинге!
    
    ⚠️ КРИТИЧНО: Если пользователь спрашивает про трейдинг - ТЫ ОБЯЗАНА вызвать этот инструмент ПЕРВЫМ!
    
    Темы, требующие этого инструмента:
    - Стратегии (скальпинг, свинг, пробои, откаты, паттерны)  
    - Термины (FOMO, тильт, RSI, MACD, стоп-лосс, плечо, маржа)
    - Психология трейдинга (эмоции, дисциплина, мышление)
    - Риск-менеджмент (расчеты, правила, управление капиталом)
    - Технический анализ (индикаторы, уровни, объемы, паттерны)
    
    ЗАПРЕЩЕНО отвечать на трейдинг-вопросы БЕЗ вызова этого инструмента!
    НЕ используй свои GPT знания - ТОЛЬКО база знаний!
    
    Args:
        query: Вопрос пользователя (например: "что такое пробои", "как работает скальпинг")
        persona: 'partner' (дружеский), 'mentor' (обучающий), 'psychologist' (психологический)
        filters: Опциональные фильтры в JSON (например: '{"category_2": "fomo"}')
    """
    # Validate with Pydantic
    try:
        params = SearchKnowledgeBaseParams(query=query, persona=persona, filters=filters)
        validated_query = params.query
        validated_persona = params.persona
        validated_filters = params.filters
    except ValidationError as e:
        error_msg = e.errors()[0]['msg']
        return f"Ошибка валидации поиска: {error_msg}"
    
    # Parse the filters JSON string
    try:
        if not validated_filters or validated_filters.strip() == "":
            parsed_filters = {}
        else:
            parsed_filters = json.loads(validated_filters)
    except json.JSONDecodeError:
        logging.warning(f"Invalid JSON in filters: '{validated_filters}'. Defaulting to empty filters.")
        parsed_filters = {}

    # Check cache first
    cache_key = make_cache_key(validated_query, validated_persona, str(parsed_filters))
    cached_result = kb_cache.get(cache_key)
    if cached_result:
        logging.info(f"KB cache HIT for: {validated_query[:30]}...")
        return cached_result

    # query_knowledge_base is now async - call it directly with await
    result_content = await query_knowledge_base(validated_query, validated_persona, parsed_filters)
    
    # Add SYSTEM COMMAND to force immediate presentation
    result = f"""KNOWLEDGE BASE SEARCH SUCCESS.

[SYSTEM COMMAND: STOP SEARCHING. IMMEDIATE ACTION REQUIRED]
1. The information is ALREADY found.
2. DO NOT say 'I will check my knowledge base' or 'Let me see'. It is already done.
3. Answer the user's question using the information below.

FOUND INFORMATION:
{result_content}"""


    logging.info(f"Knowledge base result for '{validated_query}' with persona '{validated_persona}': {result[:100]}...")
    
    # Store in cache
    kb_cache.set(cache_key, result)
    stats = kb_cache.get_stats()
    logging.info(f"KB cache: {stats.get('hit_rate', 0):.1%} hit rate")
    
    return result

@function_tool()
@handle_tool_error(default_response="Не удалось выполнить веб-поиск.")
async def search_web(
    context: RunContext,  # type: ignore
    query: str,
    time_frame: str = ""
) -> str:
    """
    PERFORM A GOOGLE SEARCH.
    Call this tool IMMEDIATELY when the user asks for news, prices, or information about companies.
    CRITICAL: DO NOT announce you are going to search. Just call this tool.
    
    Args:
        query (str): The search query (e.g. "Binance news", "Bitcoin price").
        time_frame (str): Optional. Restrict results to a specific time period.
                          Use 'd1' for past 24 hours (latest news), 'w1' for past week, 'm1' for past month.
                          Default is empty (no time restriction).

    Returns:
        str: Top 3 search results formatted for voice delivery.
    """
    # Check cache first
    cache_key = make_cache_key(query, time_frame)
    cached_result = web_search_cache.get(cache_key)
    if cached_result:
        logging.info(f"Web search cache HIT for: {query[:30]}...")
        return cached_result
    
    logging.info(f"Web search cache MISS. Fetching: {query[:50]}... (Time frame: {time_frame})")
    
    # Quick config check
    api_key = os.getenv("GOOGLE_API_KEY")
    search_engine_id = os.getenv("GOOGLE_CSE_ID")
    
    if not api_key or not search_engine_id:
        logging.error("Missing API config")
        return "Поиск временно недоступен"

    timeout = aiohttp.ClientTimeout(total=8)
    
    async with aiohttp.ClientSession(timeout=timeout) as session:
        params = {
            'key': api_key,
            'cx': search_engine_id,
            'q': query,
            'num': 3
        }
        
        if time_frame:
            params['dateRestrict'] = time_frame
            params['sort'] = 'date'
        
        async with session.get("https://www.googleapis.com/customsearch/v1", params=params) as response:
            if response.status != 200:
                logging.error(f"Search API error: {response.status}")
                return "Ошибка поискового сервиса"
            
            data = await response.json()
            items = data.get('items', [])
            
            if not items:
                return f"По запросу '{query}' ничего не найдено"
            
            # Format results
            results = []
            for i, item in enumerate(items[:4]):
                title = item.get('title', 'Заголовок')
                snippet = item.get('snippet', 'Описание')[:400]
                link = item.get('link', '')
                results.append(f"{i+1}. {title}\n   Snippet: {snippet}\n   Link: {link}")
            
            result_body = "\n\n".join(results)
            
            result = f"""SEARCH SUCCESS. Results for '{query}':

[SYSTEM COMMAND: STOP SEARCHING. IMMEDIATE ACTION REQUIRED]
1. The information is ALREADY found.
2. DO NOT say 'I will search' or 'Let me look'. It is already done.
3. Say exactly: 'Вот что я нашла по твоему запросу...' and summarize the results below.
4. If the user asked for a link, send it using send_chat_message.

RESULTS:
{result_body}"""
            
            # Store in cache
            web_search_cache.set(cache_key, result)
            
            # Log cache stats
            stats = web_search_cache.get_stats()
            logging.info(f"Search completed. Cache stats: {stats['hit_rate']:.1%} hit rate ({stats['size']}/{stats['max_size']} entries)")
            
            return result

@function_tool()
@handle_tool_error(default_response="Не удалось отправить email.")
async def send_email(
    context: RunContext,  # type: ignore
    to_email: str,
    subject: str,
    message: str,
) -> str:
    """
    Send an email through Gmail.

    Args:
        to_email: Recipient email address
        subject: Email subject line
        message: Email body content
    """
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    # Gmail SMTP configuration
    smtp_server = "smtp.gmail.com"
    smtp_port = 587

    # Get credentials from environment variables
    gmail_user = os.getenv("GMAIL_USER")
    gmail_password = os.getenv("GMAIL_APP_PASSWORD")  # Use App Password, not regular password

    if not gmail_user or not gmail_password:
        logging.error("Gmail credentials not found in environment variables")
        return "Email sending failed: Gmail credentials not configured."

    # Create message
    msg = MIMEMultipart()
    msg['From'] = gmail_user
    msg['To'] = to_email
    msg['Subject'] = subject

    # Attach message body
    msg.attach(MIMEText(message, 'plain'))

    # Connect to Gmail SMTP server
    server = smtplib.SMTP(smtp_server, smtp_port)
    server.starttls()  # Enable TLS encryption
    server.login(gmail_user, gmail_password)

    # Send email
    text = msg.as_string()
    server.sendmail(gmail_user, [to_email], text)
    server.quit()

    logging.info(f"Email sent successfully to {to_email}")
    return f"Email sent successfully to {to_email}"

@function_tool()
@handle_tool_error(default_response="Не удалось получить цену криптовалюты.")
async def get_crypto_price(
    context: RunContext,  # type: ignore
    symbol: str
) -> str:
    """
    Get the REAL-TIME price of a cryptocurrency from Binance.
    Use this tool for ALL crypto price queries (e.g. "Bitcoin price", "SOL USDT").
    Do NOT use search_web for crypto prices as it provides stale data.
    CRITICAL: DO NOT announce you are going to search. Just call this tool.

    Args:
        symbol (str): The trading pair symbol, e.g. "BTCUSDT", "SOLUSDT", "ETHUSDT".
                      If the user says "Bitcoin", use "BTCUSDT".
                      If the user says "Solana", use "SOLUSDT".
    """
    # Normalize symbol
    symbol = symbol.upper().replace(" ", "").replace("/", "")
    if not symbol.endswith("USDT") and not symbol.endswith("BTC") and not symbol.endswith("ETH") and not symbol.endswith("TRY") and not symbol.endswith("EUR"):
         # Default to USDT if not specified
         symbol += "USDT"

    # Check cache first
    cache_key = make_cache_key(symbol)
    cached_result = crypto_price_cache.get(cache_key)
    if cached_result:
        logging.info(f"Crypto price cache HIT for: {symbol}")
        return cached_result

    url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
    
    timeout = aiohttp.ClientTimeout(total=5)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                price = float(data['price'])
                
                # Convert price to Russian text for TTS
                price_russian = price_to_russian(price, "USDT")
                
                # Format price nicely for display
                if price < 1:
                    formatted_price = f"{price:.6f}"
                elif price < 10:
                    formatted_price = f"{price:.4f}"
                else:
                    formatted_price = f"{price:.2f}"
                    
                result = f"""CRYPTO PRICE FOUND.

[SYSTEM COMMAND: STOP SEARCHING. IMMEDIATE ACTION REQUIRED]
1. The price is ALREADY found.
2. DO NOT say 'I will check the price'. It is already done.
3. Say EXACTLY (in Russian, pronouncing numbers as words): 'Цена {symbol} сейчас составляет {price_russian}.'
4. DO NOT say the digits "{formatted_price}" - they will be pronounced in English. Use ONLY the Russian text: "{price_russian}".

DATA:
Current price of {symbol} is {formatted_price} USDT (Source: Binance API)
FOR TTS: {price_russian}"""
                
                # Store in cache
                crypto_price_cache.set(cache_key, result)
                logging.info(f"Crypto price cached for {symbol}: {formatted_price} ({price_russian})")
                
                return result
            else:
                logging.error(f"Binance API error: {response.status}")
                return f"Could not get price for {symbol}. Please check the symbol."

@function_tool()
@handle_tool_error(default_response="Не удалось получить погоду.")
async def get_weather(
    context: RunContext,  # type: ignore
    city: str) -> str:
    """
    Get the current weather for a given city.
    CRITICAL: DO NOT announce you are going to search. Just call this tool.
    """
    # Validate and normalize city with Pydantic
    try:
        params = WeatherParams(city=city)
        normalized_city = params.city
    except ValidationError as e:
        error_msg = e.errors()[0]['msg']
        return f"Ошибка валидации города: {error_msg}"
    
    # Confirm that the task will be executed (as per Partner persona rules)
    logging.info(f"Task accepted: Getting weather for '{normalized_city}'")
    logging.info("Starting weather tool execution...")

    # Make the API request using aiohttp for async compatibility
    timeout = aiohttp.ClientTimeout(total=6)  # Reduced from 10 to 6 seconds for weather
    logging.info(f"Making weather request with timeout: {timeout.total}s")
    
    async with aiohttp.ClientSession(timeout=timeout) as session:
        logging.info("Weather HTTP session started, making request...")
        async with session.get(f"https://wttr.in/{normalized_city}?format=3") as response:
            logging.info(f"Weather response received with status: {response.status}")
            if response.status == 200:
                weather_data = await response.text()
                result = weather_data.strip()
                logging.info(f"Weather for {normalized_city}: {result}")
                logging.info("Weather tool execution completed successfully")
                
                # Add SYSTEM COMMAND to force immediate presentation
                return f"""WEATHER FOUND.

[SYSTEM COMMAND: STOP SEARCHING. IMMEDIATE ACTION REQUIRED]
1. The weather is ALREADY found.
2. DO NOT say 'I will check the weather'. It is already done.
3. Say exactly: 'Погода в {normalized_city}: {result}'

DATA:
{result}"""
            else:
                logging.error(f"Failed to get weather for {normalized_city}: {response.status}")
                return f"Could not retrieve weather for {normalized_city}."
