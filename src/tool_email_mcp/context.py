"""Request context management for session handling.

Provides a way to store and access request-scoped data (like session info)
across tool invocations without modifying tool signatures.
"""

from contextlib import contextmanager
from contextvars import ContextVar
from typing import Optional, Dict, Any

# Context variable to store current request's session info
_current_session: ContextVar[Optional[Dict[str, Any]]] = ContextVar(
    "current_session",
    default=None
)


def set_current_session(session_data: Dict[str, Any]):
    """Set the current session data for this request context.

    Args:
        session_data: Session information dict
    """
    _current_session.set(session_data)


def get_current_session() -> Optional[Dict[str, Any]]:
    """Get the current session data.

    Returns:
        Session data dict or None if not authenticated
    """
    return _current_session.get()


def clear_current_session():
    """Clear the current session data."""
    _current_session.set(None)


@contextmanager
def session_context(session_data: Optional[Dict[str, Any]]):
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
