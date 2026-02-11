"""Middleware for session authentication.

Extracts session from cookies and makes it available to tools via context variables.
"""

from collections.abc import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from .context import session_context, set_current_request_token
from .session_manager import SessionManager


class SessionAuthMiddleware(BaseHTTPMiddleware):
    """Middleware to handle session authentication for MCP tools."""

    def __init__(self, app, session_manager: SessionManager):
        """Initialize middleware.

        Args:
            app: ASGI application
            session_manager: Session manager instance
        """
        super().__init__(app)
        self.session_manager = session_manager

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and inject session context.

        Args:
            request: Incoming request
            call_next: Next middleware/handler

        Returns:
            Response from handler
        """
        # Extract Kamiwaza PAT token from Authorization header (for OAuth Broker)
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]  # Remove "Bearer " prefix
            set_current_request_token(token)

        # Extract session ID from cookie
        session_id = request.cookies.get("email_session")

        # Get session if present
        session_data = None
        if session_id:
            session = self.session_manager.get_session(session_id)
            if session:
                session_data = {
                    "session_id": session.session_id,
                    "provider": session.provider,
                    "user_email": session.user_email,
                    "access_token": session.access_token,
                    "expires_at": session.expires_at,
                    "authenticated": True,
                }

        # Set context for this request
        with session_context(session_data):
            response = await call_next(request)
            return response
