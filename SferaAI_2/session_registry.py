"""
Session Registry for Proactive Messaging
Tracks active user sessions to enable agent-initiated communication
"""

import logging
from typing import Dict, Optional
from livekit.agents import RunContext

logger = logging.getLogger(__name__)


class SessionRegistry:
    """Thread-safe registry of active user sessions"""
    
    def __init__(self):
        self._sessions: Dict[str, dict] = {}
    
    def register(self, user_id: str, ctx: RunContext, agent: any) -> None:
        """Register an active session for a user"""
        self._sessions[user_id] = {'ctx': ctx, 'agent': agent}
        logger.info(f"Session registered for user: {user_id}")
    
    def unregister(self, user_id: str) -> None:
        """Remove a session from registry"""
        if user_id in self._sessions:
            del self._sessions[user_id]
            logger.info(f"Session unregistered for user: {user_id}")
    
    def get_session(self, user_id: str) -> Optional[dict]:
        """Get the session dict (with ctx and agent) for an active user"""
        return self._sessions.get(user_id)
    
    def get_context(self, user_id: str) -> Optional[RunContext]:
        """Get the RunContext for an active user session"""
        session = self._sessions.get(user_id)
        return session['ctx'] if session else None
    
    def get_agent(self, user_id: str):
        """Get the agent instance for an active user session"""
        session = self._sessions.get(user_id)
        return session['agent'] if session else None
    
    def is_active(self, user_id: str) -> bool:
        """Check if user has an active session"""
        return user_id in self._sessions
    
    def get_active_users(self) -> list[str]:
        """Get list of all users with active sessions"""
        return list(self._sessions.keys())
    
    def clear(self) -> None:
        """Clear all sessions (for cleanup)"""
        self._sessions.clear()
        logger.info("All sessions cleared from registry")


# Global singleton instance
session_registry = SessionRegistry()
