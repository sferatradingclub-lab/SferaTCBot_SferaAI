"""
Session Manager Module for Sfera AI Agent
Handles session shutdown, summary generation, and cleanup.
"""

import logging
import traceback
from typing import List, Dict

from livekit.agents import ChatContext
from qdrant_memory_client import QdrantMemoryClient
from summary_manager import summary_manager


async def shutdown_hook(
    chat_ctx: ChatContext,
    memory_client: QdrantMemoryClient,
    user_id: str
) -> None:
    """
    Handle session shutdown tasks: save conversation and generate summary.
    
    Args:
        chat_ctx: Chat context with conversation history
        memory_client: Memory client for storage
        user_id: User identifier
    """
    try:
        logging.info(f"Running shutdown hook for user {user_id}...")
        
        # Save messages to memory
        messages_to_add = []
        
        # Handle different ChatContext types (messages vs items)
        items = getattr(chat_ctx, 'messages', None) or getattr(chat_ctx, 'items', [])
        
        for msg in items:
            # Extract role and content
            role = getattr(msg, 'role', None)
            content = getattr(msg, 'content', '')
            
            # Handle list content
            if isinstance(content, list):
                content = ''.join(str(c) for c in content)
            
            if role == "user":
                messages_to_add.append({
                    "role": "user",
                    "content": content  # Use 'content' not 'memory'
                })
            elif role == "assistant":
                # Filter out system messages
                if not content.startswith("[SYSTEM"):
                    messages_to_add.append({
                        "role": "assistant",
                        "content": content  # Use 'content' not 'memory'
                    })
        
        if messages_to_add:
            logging.info(f"Saving {len(messages_to_add)} messages to memory")
            # Pass as list with user_id (correct signature)
            await memory_client.add(messages_to_add, user_id)
            logging.info("Chat context saved to memory.")
        else:
            logging.info("No messages to save to memory.")
        
        # Generate and save summary
        await generate_session_summary(chat_ctx, user_id)
        
    except Exception as e:
        logging.error(f"Error in shutdown hook: {e}")
        logging.error(traceback.format_exc())


async def generate_session_summary(chat_ctx: ChatContext, user_id: str) -> None:
    """
    Generate and save a summary of the current session.
    
    Args:
        chat_ctx: Chat context to summarize
        user_id: User identifier
    """
    try:
        logging.info("Generating session summary...")
        
        # Build messages as List[Dict] for summary manager
        messages = []
        items = getattr(chat_ctx, 'messages', None) or getattr(chat_ctx, 'items', [])
        
        for msg in items:
            role = getattr(msg, 'role', None)
            content = getattr(msg, 'content', '')
            
            if isinstance(content, list):
                content = ''.join(str(c) for c in content)
            
            if role in ["user", "assistant"]:
                messages.append({"role": role, "content": content})
        
        if messages:
            # Generate summary using summary manager
            summary = await summary_manager.generate_summary(messages)
            
            if summary:
                # Save summary for this user
                await summary_manager.save_summary(user_id, summary)
                logging.info(f"Session summary generated and saved: {summary[:100]}...")
            else:
                logging.warning("Summary generation returned empty result")
        else:
            logging.info("No conversation to summarize")
            
    except Exception as e:
        logging.error(f"Error generating session summary: {e}")
        logging.error(traceback.format_exc())


async def save_session_summary(user_id: str, summary: str) -> None:
    """
    Save a pre-generated summary for the user.
    
    Args:
        user_id: User identifier
        summary: Summary text to save
    """
    try:
        await summary_manager.save_summary(user_id, summary)
        logging.info(f"Saved session summary for user {user_id}")
    except Exception as e:
        logging.error(f"Error saving summary: {e}")
