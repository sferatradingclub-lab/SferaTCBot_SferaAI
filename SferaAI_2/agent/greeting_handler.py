"""
Greeting Handler Module for Sfera AI Agent
Determines if greeting is needed and creates appropriate greeting messages.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

from config import GREETINGS


async def should_greet(user_id: str) -> bool:
    """
    Determine if the agent should greet the user.
    
    Currently always returns True, but can be extended to check:
    - Time since last session
    - User preferences
    - Session state
    
    Args:
        user_id: User identifier
        
    Returns:
        True if greeting should be given
    """
    # For now, always greet
    # Future: Check session registry for last session time
    return True


def create_greeting(user_name: Optional[str] = None, last_summary: Optional[str] = None) -> str:
    """
    Create an appropriate greeting message for the user.
    
    Args:
        user_name: User's name (if known)
        last_summary: Summary of last session (if available)
        
    Returns:
        Greeting message string
    """
    current_hour = datetime.now().hour
    
    # Time-based greeting
    if 5 <= current_hour < 12:
        time_greeting = "Доброе утро"
    elif 12 <= current_hour < 17:
        time_greeting = "Добрый день"
    elif 17 <= current_hour < 23:
        time_greeting = "Добрый вечер"
    else:
        time_greeting = "Доброй ночи"
    
    # Construct full greeting
    if user_name:
        greeting = f"{time_greeting}, {user_name}! Я Sfera AI. Твоя цифровая напарница в трейдинге."
    else:
        greeting = f"{time_greeting}! Я Sfera AI. Твоя цифровая напарница в трейдинге."
    
    # Add context from last session if available
    if last_summary and len(last_summary) > 20:
        greeting += f" В прошлый раз мы говорили о {last_summary[:100]}..."
    
    # Add call to action
    greeting += " Чем сегодня займемся?"
    
    logging.info(f"Created greeting: {greeting[:50]}...")
    return greeting
