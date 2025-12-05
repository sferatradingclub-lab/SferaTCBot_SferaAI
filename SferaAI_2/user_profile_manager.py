import json
import os
import logging
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UserProfileManager:
    """
    Manages the User Profile (Core Memory) - a structured JSON file containing
    persistent facts about the user (Health, Plans, Bio, etc.).
    Async version with caching.
    """
    
    def __init__(self, profiles_dir: str = "user_profiles"):
        self.profiles_dir = profiles_dir
        self._ensure_directory()
        self._cache: Dict[str, Any] = {}
        
    def _ensure_directory(self):
        if not os.path.exists(self.profiles_dir):
            os.makedirs(self.profiles_dir)
            
    def _get_profile_path(self, user_id: str) -> str:
        return os.path.join(self.profiles_dir, f"{user_id}.json")
        
    async def load_profile(self, user_id: str) -> Dict[str, Any]:
        """Loads the user profile. Uses cache if available."""
        if user_id in self._cache:
            return self._cache[user_id]

        path = self._get_profile_path(user_id)
        
        if not os.path.exists(path):
            logger.info(f"No profile found for {user_id}. Creating default.")
            return await self._create_default_profile(user_id)
            
        try:
            def _read_file():
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            
            profile = await asyncio.to_thread(_read_file)
            self._cache[user_id] = profile
            return profile
        except Exception as e:
            logger.error(f"Error loading profile for {user_id}: {e}")
            return await self._create_default_profile(user_id)

    async def _create_default_profile(self, user_id: str) -> Dict[str, Any]:
        default_profile = {
            "user_id": user_id,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "basic_info": {
                "name": "Unknown",
                "role": "Trader",
                "language": "Russian"
            },
            "bio": "No biography yet.",
            "health": [], # List of strings: ["Back pain (28.11.2024)", ...]
            "plans": [],  # List of strings: ["Trip to Dubai (Dec 2024)", ...]
            "preferences": [], # List of strings
            "topics": []  # List of strings
        }
        await self.save_profile(user_id, default_profile)
        return default_profile

    async def save_profile(self, user_id: str, profile_data: Dict[str, Any]):
        """Saves the user profile to disk and updates cache."""
        # Update cache immediately
        self._cache[user_id] = profile_data
        
        path = self._get_profile_path(user_id)
        profile_data["updated_at"] = datetime.now().isoformat()
        
        try:
            def _write_file():
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(profile_data, f, ensure_ascii=False, indent=2)
            
            await asyncio.to_thread(_write_file)
            logger.info(f"Profile saved for {user_id}")
        except Exception as e:
            logger.error(f"Error saving profile for {user_id}: {e}")

    async def update_section(self, user_id: str, section: str, content: str | list) -> str:
        """
        Updates a specific section of the profile.
        If the section is a list (health, plans), it appends.
        If it's a string/dict, it overwrites or merges.
        """
        profile = await self.load_profile(user_id)
        
        if section not in profile:
            # If section doesn't exist, create it based on content type
            if isinstance(content, list):
                profile[section] = []
            else:
                profile[section] = ""
        
        current_value = profile[section]
        
        if isinstance(current_value, list):
            if isinstance(content, list):
                profile[section].extend(content)
            else:
                timestamp = datetime.now().strftime("%d.%m.%Y")
                profile[section].append(f"{content} ({timestamp})")
        elif isinstance(current_value, dict) and isinstance(content, dict):
            profile[section].update(content)
        else:
            # Overwrite for strings or other types
            profile[section] = content
            
        await self.save_profile(user_id, profile)
        return f"Updated section '{section}' in profile."

    async def get_formatted_profile(self, user_id: str) -> str:
        """Returns a formatted string of the profile for prompt injection."""
        profile = await self.load_profile(user_id)
        
        formatted = f"""
# CORE MEMORY (USER PROFILE)
[SYSTEM NOTE: This is your source of truth about the user. You KNOW this.]

## BASIC INFO
- Name: {profile['basic_info'].get('name', 'Unknown')}
- Role: {profile['basic_info'].get('role', 'Unknown')}

## BIOGRAPHY
{profile.get('bio', 'No bio.')}

## HEALTH (Physical & Mental)
{self._format_list(profile.get('health', []))}

## PLANS & EVENTS
{self._format_list(profile.get('plans', []))}

## PREFERENCES
{self._format_list(profile.get('preferences', []))}

## TOPICS OF INTEREST
{self._format_list(profile.get('topics', []))}
"""
        return formatted

    def _format_list(self, items: list) -> str:
        if not items:
            return "- None"
        return "\n".join([f"- {item}" for item in items])

# Singleton instance
user_profile_manager = UserProfileManager()
