"""
Tools Registration Module for Sfera AI Agent
Centralizes tool registration and management.
"""

import logging
from typing import List
from livekit.agents import function_tool, llm

from tools import (
    get_crypto_price,
    get_weather,
    search_knowledge_base,
    search_web,
    start_plan,
    save_user_name
)


def register_core_tools() -> List[function_tool]:
    """
    Register core tools available to the agent.
    
    Returns:
        List of function tools
    """
    core_tools = [
        get_crypto_price,
        get_weather,
        search_knowledge_base,
        search_web,
        start_plan,
        save_user_name
    ]
    
    logging.info(f"Registered {len(core_tools)} core tools")
    return core_tools


def get_all_tools(user_id: str = None) -> List[function_tool]:
    """
    Get all tools available for the agent session.
    
    Args:
        user_id: Optional user identifier for context
        
    Returns:
        List of all function tools
    """
    # Get core tools
    all_tools = register_core_tools()
    
    # Additional session-specific tools can be added here
    # based on user_id, permissions, etc.
    
    logging.info(f"Total tools available: {len(all_tools)}")
    return all_tools


# Tool categories for organization
CRYPTO_TOOLS = ["get_crypto_price"]
WEATHER_TOOLS = ["get_weather"]
KNOWLEDGE_TOOLS = ["search_knowledge_base", "search_web"]
MEMORY_TOOLS = ["start_plan", "save_user_name"]

# Tool descriptions for documentation
TOOL_DESCRIPTIONS = {
    "get_crypto_price": "Get real-time cryptocurrency prices from Binance",
    "get_weather": "Get weather information for any city",
    "search_knowledge_base": "Search trading knowledge base",
    "search_web": "Search the internet for information",
    "start_plan": "Start a multi-day learning or recovery plan",
    "save_user_name": "Save user's name to long-term memory"
}


def get_tool_info(tool_name: str) -> str:
    """
    Get description for a specific tool.
    
    Args:
        tool_name: Name of the tool
        
    Returns:
        Tool description or "Unknown tool"
    """
    return TOOL_DESCRIPTIONS.get(tool_name, "Unknown tool")
