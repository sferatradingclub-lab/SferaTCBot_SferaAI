import os
import logging
import json
from datetime import datetime
from typing import List, Dict, Optional
from google import genai
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SummaryManager:
    """
    Manages Episodic Memory by generating and storing daily summaries of conversations.
    """
    
    def __init__(self):
        self.api_key = os.getenv("GOOGLE_API_KEY")
        self.memory_client = None
        if not self.api_key:
            logger.warning("GOOGLE_API_KEY not found. Summarization will be disabled.")
            self.client = None
        else:
            self.client = genai.Client(api_key=self.api_key)

    def set_memory_client(self, memory_client):
        self.memory_client = memory_client

    async def generate_summary(self, messages: List[Dict[str, str]]) -> str:
        """
        Generates a concise summary of the provided messages using Gemini.
        """
        if not self.client or not messages:
            return ""

        # Format conversation for the model
        conversation_text = ""
        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            conversation_text += f"{role}: {content}\n"

        prompt = f"""
        Analyze the following conversation between a User and an AI Assistant (Sfera).
        Create a concise summary (3-5 sentences) capturing:
        1. Main topics discussed.
        2. Key decisions or plans made by the user.
        3. User's emotional state or important personal details revealed.
        
        Output ONLY the summary in Russian.
        
        Conversation:
        {conversation_text}
        """

        models_to_try = ["gemini-2.0-flash-001", "gemini-2.0-flash-exp", "gemini-1.5-flash"]
        
        for model_name in models_to_try:
            try:
                logger.info(f"Attempting summary with model: {model_name}")
                response = self.client.models.generate_content(
                    model=model_name, 
                    contents=prompt
                )
                return response.text.strip()
            except Exception as e:
                logger.warning(f"Model {model_name} failed: {e}")
                continue
        
        logger.error("All summarization models failed.")
        return "Не удалось сгенерировать саммари."

    async def save_summary(self, user_id: str, summary: str):
        """Saves the summary to Qdrant."""
        if not summary or not self.memory_client:
            return

        try:
            await self.memory_client.add_summary(user_id, summary)
            logger.info(f"Summary saved for {user_id} to Qdrant")
        except Exception as e:
            logger.error(f"Error saving summary: {e}")

    async def get_last_summary(self, user_id: str) -> str:
        """Retrieves the most recent summary for the user from Qdrant."""
        if not self.memory_client:
            return ""
            
        try:
            summary = await self.memory_client.get_last_summary(user_id)
            return summary if summary else ""
        except Exception as e:
            logger.error(f"Error reading last summary: {e}")
            return ""

# Singleton instance
summary_manager = SummaryManager()
