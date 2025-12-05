"""
Unified User State Management for Sfera AI
Combines LTM (Long-Term Memory) and User Profile functionality into a single Qdrant-based solution.
Backward compatible with both ltm_client.py and user_profile_manager.py APIs.
"""

import os
import uuid
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List, Union
from dotenv import load_dotenv

from qdrant_client import AsyncQdrantClient, models
from fastembed import TextEmbedding

from config import config

# Load environment variables
load_dotenv()

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class UnifiedUserState:
    """
    Unified client for user state management combining:
    - LTM: active_plan, plan_step, diagnosis, name
    - Profile: basic_info, bio, health, plans, preferences, topics
    
    All data stored in Qdrant for unified access and better performance.
    Backward compatible with both LTMClient and UserProfileManager APIs.
    """
    
    def __init__(self):
        self.client = AsyncQdrantClient(
            url=os.getenv("QDRANT_HOST"),
            api_key=os.getenv("QDRANT_API_KEY"),
            timeout=config.kb.qdrant_timeout
        )
        
        self.collection_name = "sfera_user_state"
        self.model_name = "sentence-transformers/all-MiniLM-L6-v2"
        self._initialized = False
        
        # Initialize embedding model for bio/topics semantic search
        try:
            logger.info(f"Initializing embedding model: {self.model_name}")
            self.embedding_model = TextEmbedding(model_name=self.model_name)
        except Exception as e:
            logger.error(f"Failed to initialize embedding model: {e}")
            self.embedding_model = None
    
    async def _ensure_initialized(self):
        if not self._initialized:
            await self._init_collection()
            self._initialized = True
    
    async def _init_collection(self):
        """Initialize Qdrant collection with proper schema"""
        try:
            collections = await self.client.get_collections()
            collection_names = [col.name for col in collections.collections]
            
            if self.collection_name not in collection_names:
                vector_size = 384  # all-MiniLM-L6-v2 dimension
                await self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=models.VectorParams(
                        size=vector_size,
                        distance=models.Distance.COSINE
                    )
                )
                logger.info(f"Created collection {self.collection_name}")
            
            # Create payload indices for fast filtering
            for field_name, field_schema in [
                ("user_id", models.PayloadSchemaType.KEYWORD),
                ("type", models.PayloadSchemaType.KEYWORD),
                ("active_plan", models.PayloadSchemaType.KEYWORD),
            ]:
                try:
                    await self.client.create_payload_index(
                        collection_name=self.collection_name,
                        field_name=field_name,
                        field_schema=field_schema
                    )
                except Exception:
                    pass  # Index might already exist
            
            logger.info("Verified payload indices for user_state collection")
                
        except Exception as e:
            logger.error(f"Failed to initialize collection: {e}")
            raise
    
    def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text (bio, topics)"""
        if not self.embedding_model or not text:
            # Return zero vector if no model or empty text
            return [0.0] * 384
        
        try:
            vectors = list(self.embedding_model.embed([text]))
            return vectors[0] if vectors else [0.0] * 384
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            return [0.0] * 384
    
    # =============================================================================
    # LTM-Compatible Methods (from ltm_client.py)
    # =============================================================================
    
    async def get_user_state(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get complete user state (LTM-compatible).
        Returns dict with: user_id, name, active_plan, plan_step, diagnosis, etc.
        """
        await self._ensure_initialized()
        
        try:
            # Query by user_id
            search_filter = models.Filter(
                must=[
                    models.FieldCondition(
                        key="user_id",
                        match=models.MatchValue(value=user_id)
                    ),
                    models.FieldCondition(
                        key="type",
                        match=models.MatchValue(value="user_state")
                    )
                ]
            )
            
            scroll_result = await self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=search_filter,
                limit=1,
                with_payload=True
            )
            
            points = scroll_result[0] if isinstance(scroll_result, tuple) else scroll_result.points
            
            if not points:
                return None
            
            return points[0].payload
            
        except Exception as e:
            logger.error(f"Failed to get user state: {e}")
            return None
    
    async def update_user_state(self, user_id: str, new_state: Dict[str, Any]) -> None:
        """
        Update or create user state (LTM-compatible).
        Merges new_state with existing state.
        """
        await self._ensure_initialized()
        
        try:
            # Get existing state
            existing_state = await self.get_user_state(user_id)
            
            if existing_state:
                # Merge with existing
                merged_state = {**existing_state, **new_state, "user_id": user_id}
                point_id = existing_state.get("point_id", str(uuid.uuid4()))
            else:
                # Create new
                merged_state = {
                    "user_id": user_id,
                    "type": "user_state",
                    "created_at": datetime.now().isoformat(),
                    **new_state
                }
                point_id = str(uuid.uuid4())
            
            # Update timestamp
            merged_state["updated_at"] = datetime.now().isoformat()
            merged_state["point_id"] = point_id
            
            # Generate embedding from bio + topics
            bio = merged_state.get("bio", "")
            topics = " ".join(merged_state.get("topics", []))
            embedding_text = f"{bio} {topics}".strip()
            vector = self._generate_embedding(embedding_text or "user profile")
            
            # Upsert to Qdrant
            point = models.PointStruct(
                id=point_id,
                vector=vector,
                payload=merged_state
            )
            
            await self.client.upsert(
                collection_name=self.collection_name,
                points=[point]
            )
            
            logger.info(f"Updated user state for {user_id}")
            
        except Exception as e:
            logger.error(f"Failed to update user state: {e}")
            raise
    
    async def set_user_name(self, user_id: str, name: str) -> None:
        """Set user name (LTM-compatible)"""
        await self.update_user_state(user_id, {'name': name})
    
    async def get_user_name(self, user_id: str) -> Optional[str]:
        """Get user name (LTM-compatible)"""
        state = await self.get_user_state(user_id)
        return state.get('name') if state else None
    
    async def get_all_active_users(self) -> List[Dict[str, Any]]:
        """
        Get all users with active plans (LTM-compatible).
        Used by proactive scheduler.
        """
        await self._ensure_initialized()
        
        try:
            # Get all user_state documents
            search_filter = models.Filter(
                must=[
                    models.FieldCondition(
                        key="type",
                        match=models.MatchValue(value="user_state")
                    )
                ]
            )
            
            scroll_result = await self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=search_filter,
                limit=1000,  # Increased limit for many users
                with_payload=True
            )
            
            points = scroll_result[0] if isinstance(scroll_result, tuple) else scroll_result.points
            
            # Filter in Python for users with active_plan
            # (Qdrant doesn't have a great way to check field exists and is not None)
            active_users = []
            for point in points:
                active_plan = point.payload.get("active_plan")
                # Check if active_plan exists and is not None/empty
                if active_plan and active_plan != "":
                    active_users.append(point.payload)
            
            return active_users
            
        except Exception as e:
            logger.error(f"Failed to get active users: {e}")
            return []

    
    async def clear_user_state(self, user_id: str):
        """Delete user state completely (LTM-compatible)"""
        await self._ensure_initialized()
        
        try:
            await self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.FilterSelector(
                    filter=models.Filter(
                        must=[
                            models.FieldCondition(
                                key="user_id",
                                match=models.MatchValue(value=user_id)
                            )
                        ]
                    )
                )
            )
            logger.info(f"Cleared user state for {user_id}")
        except Exception as e:
            logger.error(f"Failed to clear user state: {e}")
            raise
    
    # =============================================================================
    # Profile-Compatible Methods (from user_profile_manager.py)
    # =============================================================================
    
    async def load_profile(self, user_id: str) -> Dict[str, Any]:
        """
        Load user profile (Profile-compatible).
        Returns full state including LTM + Profile fields.
        Creates default profile if not exists.
        """
        state = await self.get_user_state(user_id)
        
        if not state:
            # Create default profile
            return await self._create_default_profile(user_id)
        
        return state
    
    async def _create_default_profile(self, user_id: str) -> Dict[str, Any]:
        """Create default profile for new user"""
        default_profile = {
            "user_id": user_id,
            "type": "user_state",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "name": "Unknown",
            "basic_info": {
                "role": "Trader",
                "language": "Russian"
            },
            "bio": "No biography yet.",
            "health": [],
            "plans": [],
            "preferences": [],
            "topics": []
        }
        await self.update_user_state(user_id, default_profile)
        return default_profile
    
    async def save_profile(self, user_id: str, profile_data: Dict[str, Any]):
        """Save complete profile (Profile-compatible)"""
        await self.update_user_state(user_id, profile_data)
    
    async def update_section(self, user_id: str, section: str, content: Union[str, list]) -> str:
        """
        Update specific profile section (Profile-compatible).
        IMPORTANT: Normalizes section name to lowercase for consistency.
        """
        # Normalize to lowercase to avoid Bio/bio confusion
        section = section.lower()
        
        profile = await self.load_profile(user_id)
        
        # Valid sections
        valid_sections = ["bio", "health", "plans", "preferences", "topics"]
        if section not in valid_sections:
            raise ValueError(f"Invalid section: {section}. Must be one of {valid_sections}")
        
        # Ensure section is a list
        if not isinstance(profile.get(section), list):
            profile[section] = []
        
        # Add content to section (avoid duplicates)
        if isinstance(content, str):
            if content not in profile[section]:
                profile[section].append(content)
        elif isinstance(content, list):
            for item in content:
                if item not in profile[section]:
                    profile[section].append(item)
        
        await self.save_profile(user_id, profile)
        return f"Section '{section}' updated for user {user_id}"
    
    async def get_section(self, user_id: str, section: str) -> Any:
        """Get specific profile section (Profile-compatible)"""
        profile = await self.load_profile(user_id)
        return profile.get(section)
    
    async def format_for_prompt(self, user_id: str) -> str:
        """
        Format profile as Core Memory for LLM prompt (Profile-compatible).
        """
        profile = await self.load_profile(user_id)
        
        name = profile.get('name', 'Unknown')
        
        # Read bio from BOTH 'bio' and 'Bio' for backward compatibility
        bio = profile.get('bio', 'No biography yet.')
        if bio == 'No biography yet.' and 'Bio' in profile:
            # Fallback to 'Bio' if 'bio' is empty
            bio_data = profile['Bio']
            if isinstance(bio_data, list) and bio_data:
                bio = ' '.join(bio_data)
            elif isinstance(bio_data, str):
                bio = bio_data
        
        health = profile.get('health', [])
        plans = profile.get('plans', [])
        preferences = profile.get('preferences', [])
        
        # Format as Core Memory
        memory_text = f"""# CORE MEMORY for {name}

**Bio:** {bio}

**Health:**
"""
        if health:
            for item in health:
                memory_text += f"- {item}\n"
        else:
            memory_text += "- No health issues recorded.\n"
        
        memory_text += "\n**Plans:**\n"
        if plans:
            for item in plans:
                memory_text += f"- {item}\n"
        else:
            memory_text += "- No plans recorded.\n"
        
        memory_text += "\n**Preferences:**\n"
        if preferences:
            for item in preferences:
                memory_text += f"- {item}\n"
        else:
            memory_text += "- No preferences recorded.\n"
        
        return memory_text.strip()


# Singleton instance for backward compatibility
_unified_instance = None
_instance_loop = None

def get_unified_instance() -> UnifiedUserState:
    """Get singleton instance, reset if event loop changed"""
    global _unified_instance, _instance_loop
    
    try:
        current_loop = asyncio.get_running_loop()
    except RuntimeError:
        current_loop = None
    
    # Reset instance if we're in a different event loop
    if _instance_loop is not None and _instance_loop != current_loop:
        logger.info("Event loop changed, resetting UnifiedUserState instance")
        _unified_instance = None
        _instance_loop = None
    
    if _unified_instance is None:
        _unified_instance = UnifiedUserState()
        _instance_loop = current_loop
        
    return _unified_instance
