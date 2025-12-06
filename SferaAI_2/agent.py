from datetime import datetime
from dotenv import load_dotenv
import asyncio
import json
import logging
import os
import sys
from pathlib import Path

from livekit import agents
from livekit.agents import AgentSession, function_tool, RunContext, JobContext
from pydantic import ValidationError

from config import config
from prompts import get_system_prompt
from qdrant_memory_client import QdrantMemoryClient
from summary_manager import summary_manager
from session_registry_redis import get_session_registry
from unified_user_state import get_unified_instance
from auth_utils import validate_telegram_data

from russian_numbers import replace_numbers_in_text
from models.tool_params import SearchInternetParams, SearchVideoParams
from duckduckgo_search import DDGS
import aiohttp

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import subscription service - NEW
from services.subscription_service import track_session_start, track_session_end

# Import modular components
from agent.assistant import Assistant
from agent.memory_loader import load_all_memory, format_memory_for_context
from agent.session_manager import shutdown_hook
from tools import get_crypto_price, get_weather, search_knowledge_base, search_web, start_plan, save_user_name
from monitoring import init_monitoring

# Initialize monitoring (Sentry) on module load
init_monitoring()

load_dotenv()


async def entrypoint(ctx: JobContext):
    """Main agent entrypoint - orchestrates all components."""
    
    # Validate configuration
    validation = config.validate()
    if not validation["valid"]:
        logging.error(f"Config errors: {validation['errors']}")
        raise ValueError(f"Invalid config: {validation['errors']}")
    
    # Connect and authenticate
    await ctx.connect()
    participant = await ctx.wait_for_participant()
    user_id = participant.identity
    
    # Telegram auth
    metadata = participant.metadata
    if metadata and "initData" in metadata:
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        if bot_token:
            user_data = validate_telegram_data(metadata["initData"], bot_token)
            if user_data:
                user_id = str(user_data['id'])
                logging.info(f"Telegram auth: {user_id}")
    
    # NEW: Check subscription and track session start
    try:
        user_id_int = int(user_id)
        can_start, reason = await track_session_start(user_id_int)
        
        if not can_start:
            # Send error to frontend
            logging.warning(f"User {user_id} blocked from starting session: {reason}")
            await ctx.room.local_participant.publish_data(
                json.dumps({
                    "error": "subscription_limit", 
                    "message": reason
                }).encode(),
                topic="sfera-error"
            )
            # Wait a bit for message to be delivered
            await asyncio.sleep(2)
            return
        
        session_start_time = datetime.now()
        logging.info(f"Session started for user {user_id}, tracking enabled")
    except (ValueError, TypeError) as e:
        logging.error(f"Failed to parse user_id {user_id}: {e}")
        user_id_int = None
        session_start_time = None
    
    config.memory.user_name = user_id
    
    # Load all memory using our module
    initial_ctx, core_memory, episodic_memory, recent_memories = await load_all_memory(user_id)
    memory_str = format_memory_for_context(recent_memories)
    
    # Initialize memory client and unified state BEFORE using them
    memory_client = QdrantMemoryClient()
    summary_manager.set_memory_client(memory_client)
    unified_state = get_unified_instance()
    
    # Get user name from UnifiedUserState
    user_name = await unified_state.get_user_name(user_id)
    logging.info(f"User name from unified state: {user_name}")

    # Get system prompt with personalization
    system_prompt = get_system_prompt(user_name=user_name)

    
    # Initialize memory client
    memory_client = QdrantMemoryClient()
    summary_manager.set_memory_client(memory_client)
    unified_state = get_unified_instance()
    
    # Define local tools that need ctx.room access
    @function_tool()
    async def update_profile(context: RunContext, section: str, content: str) -> str:
        """Update user profile."""
        result = await unified_state.update_section(user_id, section, content)
        return f"Profile updated: {result}"
    
    @function_tool()
    async def search_internet(context: RunContext, query: str, result_type: str = "text", multiple: bool = False) -> str:
        """Search internet with Google."""
        try:
            params_obj = SearchInternetParams(query=query, max_results=3 if multiple else 1)
            validated_query = params_obj.query
        except ValidationError as e:
            return f"Validation error: {e.errors()[0]['msg']}"
        
        api_key = os.getenv("GOOGLE_API_KEY")
        search_engine_id = os.getenv("GOOGLE_CSE_ID")
        if not api_key or not search_engine_id:
            return "Search not configured"
        
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=8)) as session:
            params = {'key': api_key, 'cx': search_engine_id, 'q': validated_query, 'num': 5}
            async with session.get("https://www.googleapis.com/customsearch/v1", params=params) as response:
                if response.status != 200:
                    return "Search service unavailable"
                data = await response.json()
                items = data.get('items', [])[:3 if multiple else 1]
                
                if not items:
                    return f"Nothing found for '{validated_query}'"
                
                if result_type == "link":
                    for item in items:
                        await ctx.room.local_participant.publish_data(
                            json.dumps({"url": item['link'], "title": item['title']}).encode(),
                            topic="sfera-link"
                        )
                    return "[FOUND] Links sent to chat"
                else:
                    result = "Found:\n"
                    for i, item in enumerate(items, 1):
                        result += f"{i}. {item['title']}\n{item.get('snippet', '')[:150]}\n"
                    return result
    
    @function_tool()
    async def search_video(context: RunContext, query: str, multiple: bool = False) -> str:
        """Search YouTube videos."""
        try:
            params_obj = SearchVideoParams(query=query)
            validated_query = params_obj.query
        except ValidationError as e:
            return f"Validation error: {e.errors()[0]['msg']}"
        
        try:
            from duckduckgo_search.exceptions import RatelimitException
            
            loop = asyncio.get_event_loop()
            videos = await loop.run_in_executor(
                None,
                lambda: list(DDGS().videos(keywords=validated_query, region="wt-wt", max_results=3 if multiple else 1))
            )
            
            if not videos:
                return f"No videos found for '{validated_query}'"
            
            for video in videos:
                title = video.get('title', '')
                link = video.get('content', '')
                thumbnail = video.get('images', {}).get('large') or video.get('image', '')
                if thumbnail and link:
                    await ctx.room.local_participant.publish_data(
                        json.dumps({"title": title, "thumbnailUrl": thumbnail, "videoUrl": link}).encode(),
                        topic="sfera-youtube"
                    )
            
            return f"[FOUND] {len(videos)} video(s) sent to chat"
            
        except RatelimitException:
            logging.error("DuckDuckGo rate limit exceeded for video search")
            return "Sorry, video search temporarily unavailable due to rate limiting. Please try again in a minute."
        except Exception as e:
            logging.error(f"Video search error: {e}")
            return f"Error searching videos: {str(e)}"
    
    # Build agent with all tools
    extra_tools = [update_profile, search_internet, search_video]
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    agent = Assistant(
        system_prompt=system_prompt,
        chat_ctx=initial_ctx,
        memory_context=memory_str,
        core_memory_context=core_memory,
        episodic_memory_context=episodic_memory,
        extra_tools=extra_tools,
        current_date=current_date
    )
    
    # Start proactive scheduler
    scheduler_task = asyncio.create_task(run_proactive_scheduler())
    
        entrypoint_fnc=entrypoint,
        initialize_process_timeout=30  # Increase timeout for Qdrant+Redis init
    ))
