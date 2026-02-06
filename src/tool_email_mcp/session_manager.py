"""Session management for OAuth authentication.

In-memory session storage with automatic expiry.
Sessions are cleared on container restart (by design).
"""

import asyncio
import secrets
import time
from typing import Dict, Optional, Any
from dataclasses import dataclass, asdict


@dataclass
class EmailSession:
    """Email session with OAuth credentials."""

    session_id: str
    provider: str
    access_token: str
    user_email: str
    expires_at: float
    created_at: float

    def is_expired(self) -> bool:
        """Check if session has expired."""
        return time.time() > self.expires_at

    def minutes_remaining(self) -> int:
        """Get minutes until session expires."""
        remaining = max(0, self.expires_at - time.time())
        return int(remaining / 60)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (without sensitive data for API responses)."""
        return {
            "session_id": self.session_id,
            "provider": self.provider,
            "user_email": self.user_email,
            "expires_at": self.expires_at,
            "created_at": self.created_at,
            "expired": self.is_expired(),
            "minutes_remaining": self.minutes_remaining()
        }


@dataclass
class OAuthState:
    """OAuth state token for CSRF protection."""

    state: str
    provider: str
    created_at: float

    def is_expired(self, max_age: int = 300) -> bool:
        """Check if state token has expired.

        Args:
            max_age: Maximum age in seconds (default: 5 minutes)
        """
        return time.time() - self.created_at > max_age


class SessionManager:
    """Manages in-memory email sessions."""

    def __init__(self, default_timeout: int = 3600):
        """Initialize session manager.

        Args:
            default_timeout: Default session timeout in seconds (default: 1 hour)
        """
        self.default_timeout = default_timeout
        self._sessions: Dict[str, EmailSession] = {}
        self._oauth_states: Dict[str, OAuthState] = {}
        self._cleanup_task: Optional[asyncio.Task] = None

    def start_cleanup_task(self):
        """Start background task to clean expired sessions."""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())

    async def _cleanup_loop(self):
        """Background task to clean expired sessions and states."""
        while True:
            await asyncio.sleep(60)  # Check every minute

            # Clean expired sessions
            now = time.time()
            expired_sessions = [
                sid for sid, session in self._sessions.items()
                if now > session.expires_at
            ]

            for sid in expired_sessions:
                print(f"🗑️  Cleaning expired session: {sid[:8]}...")
                self._sessions.pop(sid, None)

            # Clean expired OAuth states (5 min expiry)
            expired_states = [
                state for state, data in self._oauth_states.items()
                if data.is_expired()
            ]

            for state in expired_states:
                self._oauth_states.pop(state, None)

            if expired_sessions or expired_states:
                print(f"✅ Cleaned {len(expired_sessions)} sessions, {len(expired_states)} states")

    def create_oauth_state(self, provider: str) -> str:
        """Create OAuth state token for CSRF protection.

        Args:
            provider: Provider name

        Returns:
            State token string
        """
        state = secrets.token_urlsafe(32)
        self._oauth_states[state] = OAuthState(
            state=state,
            provider=provider,
            created_at=time.time()
        )
        return state

    def verify_oauth_state(self, state: str) -> Optional[str]:
        """Verify OAuth state token and return provider.

        Args:
            state: State token to verify

        Returns:
            Provider name if valid, None otherwise
        """
        oauth_state = self._oauth_states.pop(state, None)
        if not oauth_state:
            return None

        if oauth_state.is_expired():
            return None

        return oauth_state.provider

    def create_session(
        self,
        provider: str,
        access_token: str,
        user_email: str,
        timeout: Optional[int] = None
    ) -> str:
        """Create a new email session.

        Args:
            provider: Provider name ("gmail" or "outlook")
            access_token: OAuth access token
            user_email: User's email address
            timeout: Session timeout in seconds (default: use default_timeout)

        Returns:
            Session ID
        """
        session_id = secrets.token_urlsafe(32)
        timeout = timeout or self.default_timeout

        session = EmailSession(
            session_id=session_id,
            provider=provider,
            access_token=access_token,
            user_email=user_email,
            expires_at=time.time() + timeout,
            created_at=time.time()
        )

        self._sessions[session_id] = session

        print(f"🔐 Session created: {session_id[:8]}... - {user_email} ({provider})")

        return session_id

    def get_session(self, session_id: str) -> Optional[EmailSession]:
        """Get session by ID.

        Args:
            session_id: Session ID

        Returns:
            EmailSession if valid and not expired, None otherwise
        """
        session = self._sessions.get(session_id)
        if not session:
            return None

        if session.is_expired():
            self._sessions.pop(session_id, None)
            return None

        return session

    def delete_session(self, session_id: str) -> bool:
        """Delete a session.

        Args:
            session_id: Session ID

        Returns:
            True if session was deleted, False if not found
        """
        session = self._sessions.pop(session_id, None)
        if session:
            print(f"🗑️  Session deleted: {session_id[:8]}... - {session.user_email}")
            return True
        return False

    def list_sessions(self) -> list[Dict[str, Any]]:
        """List all active sessions (without access tokens).

        Returns:
            List of session info dicts
        """
        return [
            session.to_dict()
            for session in self._sessions.values()
            if not session.is_expired()
        ]

    def get_session_count(self) -> int:
        """Get count of active sessions."""
        return len([s for s in self._sessions.values() if not s.is_expired()])

    def clear_all_sessions(self):
        """Clear all sessions (used for testing or emergency shutdown)."""
        count = len(self._sessions)
        self._sessions.clear()
        self._oauth_states.clear()
        print(f"🗑️  Cleared all sessions ({count} total)")
