"""Middleware for session authentication.

Extracts session from cookies and makes it available to tools via context variables.
"""

import logging
from collections.abc import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from .context import session_context, set_current_deployment_id, set_current_request_host, set_current_request_token
from .session_manager import SessionManager

logger = logging.getLogger(__name__)


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
        logger.debug(f"Processing request: {request.method} {request.url.path}")

        # Extract Kamiwaza PAT token from Authorization header (for OAuth Broker)
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]  # Remove "Bearer " prefix
            set_current_request_token(token)
            logger.debug("Authorization token extracted from header")

        # Extract forwarded host to construct OAuth Broker URL
        forwarded_host = request.headers.get("x-forwarded-host") or request.headers.get("host", "localhost")
        forwarded_proto = request.headers.get("x-forwarded-proto", "https")
        set_current_request_host(f"{forwarded_proto}://{forwarded_host}")

        # Extract deployment ID to use as app_installation_id
        deployment_id = request.headers.get("x-kz-deployment-id")
        if deployment_id:
            set_current_deployment_id(deployment_id)
            logger.debug(f"Deployment ID: {deployment_id}")

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
                logger.debug(f"Session authenticated: {session.user_email}")

        # Set context for this request
        with session_context(session_data):
            response = await call_next(request)
            return response
