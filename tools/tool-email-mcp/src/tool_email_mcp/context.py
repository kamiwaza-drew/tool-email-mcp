"""Request context management for session handling.

Provides a way to store and access request-scoped data (like session info)
across tool invocations without modifying tool signatures.
"""

from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any

# Context variable to store current request's session info
_current_session: ContextVar[dict[str, Any] | None] = ContextVar("current_session", default=None)

# Context variable to store current request's Kamiwaza PAT token
# Used by OAuth Broker provider for per-request authentication
_current_request_token: ContextVar[str | None] = ContextVar("current_request_token", default=None)

# Context variable to store current request's forwarded host
# Used to construct OAuth Broker URL
_current_request_host: ContextVar[str | None] = ContextVar("current_request_host", default=None)

# Context variable to store current request's deployment ID
# Used as app_installation_id for OAuth Broker
_current_deployment_id: ContextVar[str | None] = ContextVar("current_deployment_id", default=None)


def set_current_session(session_data: dict[str, Any]):
    """Set the current session data for this request context.

    Args:
        session_data: Session information dict
    """
    _current_session.set(session_data)


def get_current_session() -> dict[str, Any] | None:
    """Get the current session data.

    Returns:
        Session data dict or None if not authenticated
    """
    return _current_session.get()


def clear_current_session():
    """Clear the current session data."""
    _current_session.set(None)


def set_current_request_token(token: str):
    """Set the current request's Kamiwaza PAT token.

    Args:
        token: Kamiwaza PAT token from Authorization header
    """
    _current_request_token.set(token)


def get_current_request_token() -> str | None:
    """Get the current request's Kamiwaza PAT token.

    Returns:
        PAT token string or None if not set
    """
    return _current_request_token.get()


def clear_current_request_token():
    """Clear the current request's PAT token."""
    _current_request_token.set(None)


def set_current_request_host(host: str):
    """Set the current request's forwarded host.

    Args:
        host: Forwarded host from X-Forwarded-Host header
    """
    _current_request_host.set(host)


def get_current_request_host() -> str | None:
    """Get the current request's forwarded host.

    Returns:
        Forwarded host string or None if not set
    """
    return _current_request_host.get()


def set_current_deployment_id(deployment_id: str):
    """Set the current request's deployment ID.

    Args:
        deployment_id: Deployment ID from X-Kz-Deployment-Id header
    """
    _current_deployment_id.set(deployment_id)


def get_current_deployment_id() -> str | None:
    """Get the current request's deployment ID.

    Returns:
        Deployment ID string or None if not set
    """
    return _current_deployment_id.get()


@contextmanager
def session_context(session_data: dict[str, Any] | None):
    """Context manager for setting session data.

    Args:
        session_data: Session information dict

    Example:
        with session_context(session_data):
            # Tool calls here have access to session
            result = await some_tool()
    """
    token = _current_session.set(session_data)
    try:
        yield
    finally:
        _current_session.reset(token)
