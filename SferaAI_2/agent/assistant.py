"""
Assistant class for Sfera AI agent.
Handles LLM interaction and Russian number localization.
"""

import logging
from livekit.agents import Agent
from livekit.plugins import google

from config import config
from russian_numbers import replace_numbers_in_text
from tools import (
    search_knowledge_base,
    get_weather,
    get_crypto_price,
    save_user_name,
    start_plan,
    search_web
)



def filter_agent_reasoning(text: str) -> str:
    """Remove internal model reasoning/thinking blocks from agent response."""
    if not text:
        return text
    
    lines = text.split('\n')
    filtered_lines = []
    
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('**') and stripped.endswith('**'):
            continue
        filtered_lines.append(line)
    
    return '\n'.join(filtered_lines).strip()


class Assistant(Agent):
    """
    Main assistant class for Sfera AI.
    Extends LiveKit Agent with Russian number pronunciation.
    Persona switching is handled by the LLM via embedded system prompt.
    """
    
    def __init__(
        self, 
        system_prompt: str, 
        chat_ctx=None, 
        memory_context="", 
        core_memory_context="", 
        episodic_memory_context="", 
        extra_tools=None, 
        current_date=""
    ) -> None:
        """
        Initialize the assistant with system prompt and memory contexts.
        
        Args:
            system_prompt: Base system instructions (with embedded personas)
            chat_ctx: Chat context for conversation history
            memory_context: Long-term memory context string
            core_memory_context: Core user profile memory
            episodic_memory_context: Recent episodic memories
            extra_tools: Additional tools to register
            current_date: Current date string for context
        """
        # Combine System Prompt + Core Memory + Episodic Memory + Chat History
        final_instructions = f"""{system_prompt}

# CURRENT DATE: {current_date}

{core_memory_context}

{episodic_memory_context}

# КОНТЕКСТ ПРОШЛЫХ БЕСЕД (CHAT HISTORY)
{memory_context}

# ВАЖНОЕ НАПОМИНАНИЕ (ВЫСШИЙ ПРИОРИТЕТ)
- Обращайся к пользователю ТОЛЬКО на 'ты'.
- Используй фирменное приветствие, если это начало диалога."""
        
        # Base tools available to all personas  
        # NOTE: search_internet and search_video are passed via extra_tools with ctx.room access
        base_tools = [
            search_knowledge_base,
            get_weather,
            search_web,
            start_plan,
            get_crypto_price,
            save_user_name
        ]
        all_tools = base_tools + (extra_tools or [])
        
        super().__init__(
            instructions=final_instructions,
            llm=google.realtime.RealtimeModel(
                model=config.agent.model_name,
                voice=config.agent.voice,
                temperature=config.agent.temperature,
                thinking_config=config.get_thinking_config(),
                realtime_input_config=config.get_realtime_input_config()
            ),
            tools=all_tools,
            chat_ctx=chat_ctx
        )
    
    async def _llm_in_text(self, text: str, *, source: str) -> str:
        """
        Override to log user input and expected persona.
        NOTE: No role switching happens here - LLM handles that via system prompt.
        This is purely for debugging visibility.
        """
        query_lower = text.lower()
        
        # Detect expected role based on keywords (for logging only)
        detected_role = "👥 Partner"
        if any(kw in query_lower for kw in ["тильт", "vtilte", "fomo", "фомо", "страх", "паника", "боюсь", "нервы", "стресс"]):
            detected_role = "🧠 Psychologist"
        elif any(kw in query_lower for kw in ["объясни", "что такое", "научи", "стоп-лосс", "стоп лосс", "как работает", "расскажи про", "не понимаю"]):
            detected_role = "👨‍🏫 Mentor"
        
        logging.info(f"📝 User: {text[:80]}... | Expected persona: {detected_role}")
        
        return await super()._llm_in_text(text, source=source)
    
    async def _llm_out_text(self, text: str, *, source: str) -> str:
        """
        Override to intercept LLM output BEFORE TTS.
        This is called by LiveKit internally before sending to Gemini Realtime API.
        Convert all numbers to Russian words for proper pronunciation.
        """
        russian_text = replace_numbers_in_text(text)
        if text != russian_text:
            logging.info(f"🔢 NUM→RU: '{text[:60]}' → '{russian_text[:60]}'")
        return await super()._llm_out_text(russian_text, source=source)
