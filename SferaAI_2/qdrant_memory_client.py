"""
QdrantMemoryClient - Client for Sfera AI memory system using Qdrant.
"""

import os
import uuid
import json
import time
import logging
import hashlib
from datetime import datetime
from typing import List, Dict, Any, Optional

from qdrant_client import AsyncQdrantClient, models
from fastembed import TextEmbedding
from config import config
# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class QdrantMemoryClient:
    """
    Async client for Qdrant memory storage.
    """
    
    def __init__(self, use_cloud_inference: bool = False):
        self.client = AsyncQdrantClient(
            url=os.getenv("QDRANT_HOST"),
            api_key=os.getenv("QDRANT_API_KEY"),
            timeout=config.kb.qdrant_timeout,
            cloud_inference=use_cloud_inference
        )
        
        self.collection_name = "sfera_ai_memory"
        self.model_name = "sentence-transformers/all-MiniLM-L6-v2"
        self._initialized = False
        
        # Initialize embedding model once
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
        try:
            collections = await self.client.get_collections()
            collection_names = [col.name for col in collections.collections]
            
            if self.collection_name not in collection_names:
                vector_size = 384
                await self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=models.VectorParams(
                        size=vector_size,
                        distance=models.Distance.COSINE
                    )
                )
                logger.info(f"Created collection {self.collection_name}")
            
            # Create payload indices
            # Timestamp needs DATETIME index for sorting/range queries
            try:
                await self.client.create_payload_index(
                    collection_name=self.collection_name,
                    field_name="timestamp",
                    field_schema=models.PayloadSchemaType.DATETIME
                )
            except Exception:
                pass

            for field_name, field_schema in [
                ("user_id", models.PayloadSchemaType.KEYWORD),
                ("type", models.PayloadSchemaType.KEYWORD)
            ]:
                try:
                    await self.client.create_payload_index(
                        collection_name=self.collection_name,
                        field_name=field_name,
                        field_schema=field_schema
                    )
                except Exception:
                    # Index might already exist
                    pass
            
            logger.info("Verified payload indices")
                
        except Exception as e:
            logger.error(f"Failed to initialize collection: {e}")
            pass

    async def add(self, messages: List[Dict[str, str]], user_id: str) -> None:
        """
        Save messages to memory.
        """
        await self._ensure_initialized()
        
        try:
            if not self.embedding_model:
                raise ValueError("Embedding model not initialized")

            # Generate vectors
            vectors = list(self.embedding_model.embed([msg["content"] for msg in messages]))
            
            points = []
            for message, vector in zip(messages, vectors):
                # Use UUID for ID to allow multiple identical messages (conversation flow)
                point_id = str(uuid.uuid4())
                
                payload = {
                    "content": message["content"],
                    "role": message["role"],
                    "user_id": user_id,
                    "timestamp": datetime.utcnow().isoformat(),
                    "session_id": str(uuid.uuid4()) 
                }
                
                point = models.PointStruct(
                    id=point_id,
                    vector=vector,
                    payload=payload
                )
                points.append(point)
            
            await self.client.upsert(
                collection_name=self.collection_name,
                points=points
            )
            
            logger.info(f"Successfully saved {len(messages)} messages for user {user_id}")
            
        except Exception as e:
            logger.error(f"Failed to save memory: {e}")
            raise
    
    async def get_all(self, filters: Dict[str, Any], limit: int = 1000) -> Dict[str, Any]:
        """
        Get memories for a user, optionally filtered by date range.
        Args:
            filters: Dict with 'user_id' (required), 'start_date', 'end_date'.
            limit: Max number of records to return.
        """
        await self._ensure_initialized()
        
        try:
            user_id = filters.get("user_id")
            if not user_id:
                return {"results": []}
            
            must_conditions = [
                models.FieldCondition(
                    key="user_id",
                    match=models.MatchValue(value=user_id)
                )
            ]

            start_date = filters.get("start_date")
            end_date = filters.get("end_date")

            if start_date or end_date:
                range_filter = models.DatetimeRange()
                if start_date:
                    range_filter.gte = start_date
                if end_date:
                    range_filter.lte = end_date
                
                must_conditions.append(
                    models.FieldCondition(
                        key="timestamp",
                        range=range_filter
                    )
                )
            
            search_filter = models.Filter(must=must_conditions)
            
            # Use server-side sorting if we just want the latest N messages
            # For history reading (large limit), we might want chronological, but usually we want latest first for context
            
            scroll_result = await self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=search_filter,
                limit=limit,
                with_payload=True,
                order_by=models.OrderBy(
                    key="timestamp",
                    direction="desc"
                )
            )
            
            points = scroll_result.points if hasattr(scroll_result, 'points') else scroll_result[0]
            
            memories = []
            for point in points:
                memories.append({
                    "memory": point.payload["content"],
                    "updated_at": point.payload["timestamp"],
                    "role": point.payload.get("role", "unknown")
                })
            
            # If we requested a small limit (like 30 for context), we probably want them in chronological order for the LLM
            # But we fetched them DESC (newest first) to get the *latest* 30.
            # So we need to reverse them back to chronological order.
            memories.sort(key=lambda x: x["updated_at"], reverse=False)
            
            return {"results": memories}
            
        except Exception as e:
            logger.error(f"Failed to get memories: {e}")
            return {"results": []}
    
    async def search(self, query: str, user_id: str, filters: Dict[str, Any] = None, limit: int = 5) -> Dict[str, Any]:
        """Semantic search in memory."""
        await self._ensure_initialized()
        
        try:
            if not self.embedding_model:
                raise ValueError("Embedding model not initialized")

            search_conditions = [
                models.FieldCondition(
                    key="user_id",
                    match=models.MatchValue(value=user_id)
                )
            ]
            
            if filters:
                for key, value in filters.items():
                    if key != "user_id":
                        search_conditions.append(
                            models.FieldCondition(
                                key=key,
                                match=models.MatchValue(value=value)
                            )
                        )
            
            query_vectors = list(self.embedding_model.embed([query]))
            query_vector = query_vectors[0]
            
            # Use query_points instead of search for compatibility with newer clients
            search_results = await self.client.query_points(
                collection_name=self.collection_name,
                query=query_vector,
                query_filter=models.Filter(must=search_conditions),
                with_payload=True,
                limit=limit
            )
            
            memories = []
            # query_points returns QueryResponse with points
            points = search_results.points
            
            for result in points:
                memories.append({
                    "memory": result.payload["content"],
                    "updated_at": result.payload["timestamp"],
                    "score": round(result.score, 3),
                    "role": result.payload.get("role", "unknown")
                })
            
            return {"results": memories}
            
        except Exception as e:
            logger.error(f"Failed to search memories: {e}")
            return {"results": []}

    async def delete_memory(self, user_id: str) -> None:
        await self._ensure_initialized()
        try:
            await self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.FilterSelector(
                    filter=models.Filter(
                        must=[
                            models.FieldCondition(
                                key="user_id",
                                match=models.MatchValue(value=user_id),
                            )
                        ]
                    )
                ),
            )
            logger.info(f"All memories deleted for user {user_id}")
        except Exception as e:
            logger.error(f"Failed to delete memories for user {user_id}: {e}")
            raise

    async def add_summary(self, user_id: str, summary: str) -> None:
        """
        Save a session summary to memory with type='summary'.
        """
        await self._ensure_initialized()
        
        try:
            if not self.embedding_model:
                raise ValueError("Embedding model not initialized")

            # Generate vector for the summary
            vectors = list(self.embedding_model.embed([summary]))
            vector = vectors[0]
            
            point_id = str(uuid.uuid4())
            
            payload = {
                "content": summary,
                "role": "system",
                "type": "summary",
                "user_id": user_id,
                "timestamp": datetime.utcnow().isoformat(),
                "session_id": str(uuid.uuid4()) 
            }
            
            point = models.PointStruct(
                id=point_id,
                vector=vector,
                payload=payload
            )
            
            await self.client.upsert(
                collection_name=self.collection_name,
                points=[point]
            )
            
            logger.info(f"Successfully saved summary for user {user_id}")
            
        except Exception as e:
            logger.error(f"Failed to save summary: {e}")
            raise

    async def get_last_summary(self, user_id: str) -> Optional[str]:
        """
        Retrieve the most recent summary for the user.
        """
        await self._ensure_initialized()
        
        try:
            # Filter for user_id and type='summary'
            search_filter = models.Filter(
                must=[
                    models.FieldCondition(
                        key="user_id",
                        match=models.MatchValue(value=user_id)
                    ),
                    models.FieldCondition(
                        key="type",
                        match=models.MatchValue(value="summary")
                    )
                ]
            )
            
            # Sort by timestamp descending and get the first one
            scroll_result = await self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=search_filter,
                limit=1,
                with_payload=True,
                order_by=models.OrderBy(
                    key="timestamp",
                    direction="desc"
                )
            )
            
            points = scroll_result.points if hasattr(scroll_result, 'points') else scroll_result[0]
            
            if not points:
                return None
                
            return points[0].payload["content"]
            
        except Exception as e:
            logger.error(f"Failed to get last summary: {e}")
            return None