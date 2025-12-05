"""
Memory Loading Module for Sfera AI Agent
Handles loading of all memory types: chat history, core memory, episodic memory.
"""

import asyncio
import logging
from typing import List, Tuple, Dict, Any
from livekit.agents import ChatContext

from qdrant_memory_client import QdrantMemoryClient
from unified_user_state import get_unified_instance
from summary_manager import summary_manager


async def load_all_memory(user_id: str) -> Tuple[ChatContext, str, str, List[Dict]]:
    """
    Load all memory types for a user in parallel.
    
    Args:
        user_id: User identifier
        
    Returns:
        Tuple of (initial_chat_context, core_memory_str, episodic_memory_str, recent_memories)
    """
    logging.info(f"Starting parallel memory loading for user {user_id}...")
    
    # Get unified state instance
    unified_state = get_unified_instance()
    
    # Initialize Memory Client
    memory_client = QdrantMemoryClient()
    summary_manager.set_memory_client(memory_client)
    
    # Create tasks for parallel execution
    profile_task = unified_state.format_for_prompt(user_id)
    summary_task = summary_manager.get_last_summary(user_id)
    history_task = memory_client.get_all(filters={"user_id": user_id}, limit=30)
    
    # Execute all tasks concurrently
    core_memory_str, last_summary, results = await asyncio.gather(
        profile_task,
        summary_task,
        history_task
    )
    
    logging.info(f"Loaded Core Memory for {user_id}")
    
    # Process episodic memory (last session summary)
    episodic_memory_str = ""
    if last_summary:
        episodic_memory_str = f"# EPISODIC MEMORY (LAST SESSION SUMMARY)\\n[SYSTEM NOTE: Use this to continue the conversation naturally.]\\n{last_summary}"
        logging.info(f"Loaded Episodic Memory for {user_id}")
    
    # Process recent memories
    search_results = results.get('results', results)
    recent_memories = []
    
    if search_results:
        recent_memories = search_results
        logging.info(f"Loaded {len(recent_memories)} recent memories for user {user_id}")
    
    # Create initial chat context and add recent conversation history
    initial_ctx = ChatContext()
    
    # Add recent memories to chat context so agent remembers previous conversations
    if recent_memories:
        for memory in recent_memories[-10:]:  # Last 10 messages for context
            try:
                role = memory.get('role', 'user')
                content = memory.get('content', '')
                if role in ['user', 'assistant'] and content:
                    initial_ctx.add_message(role=role, content=content)
            except Exception as e:
                logging.warning(f"Failed to add memory to ChatContext: {e}")
    
    # Add greeting after memories
    try:
        initial_ctx.add_message(
            role="system",
            content="User connected. You MUST say exactly: 'Привет. Я Sfera AI. Твоя цифровая напарница в трейдинге. Чем сегодня займемся?' Address the user as 'ты' (informal) at all times."
        )
    except Exception:
        logging.exception("Failed to add greeting to initial ChatContext")
    
    return initial_ctx, core_memory_str, episodic_memory_str, recent_memories


def format_memory_for_context(recent_memories: List[Dict]) -> str:
    """
    Format recent memories as a string for agent context.
    
    Args:
        recent_memories: List of memory entries
        
    Returns:
        Formatted memory string
    """
    memory_lines = []
    for mem in recent_memories:
        role = mem.get("role", "unknown")
        content = mem.get("memory", "")
        if role == "user":
            memory_lines.append(f"User: {content}")
        elif role == "assistant":
            memory_lines.append(f"Assistant: {content}")
        else:
            memory_lines.append(f"{content}")
    
    return "\\n".join(memory_lines)
