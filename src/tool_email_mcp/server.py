"""FastMCP server for Email operations.

Exposes secure email tools through FastMCP/HTTP transport with federal-standard security.
"""

import os
from typing import List, Optional, Any, Dict

from dotenv import load_dotenv

try:
    from mcp import FastMCP
except ImportError:
    from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from starlette.requests import Request
from starlette.responses import JSONResponse

from .security import SecurityManager
from .email_operations import EmailOperations

load_dotenv()
load_dotenv(".env.local")

# Initialize security and operations
security_manager = SecurityManager()
email_ops = EmailOperations(security_manager)

# Disable DNS rebinding protection to allow requests via Docker networking
mcp = FastMCP(
    "tool-email-mcp",
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=False,
    ),
)


@mcp.custom_route("/health", methods=["GET"])
async def health_check(_request: Request) -> JSONResponse:
    """Health check endpoint."""
    return JSONResponse({
        "status": "healthy",
        "provider_configured": email_ops.provider is not None,
        "security_enabled": True
    })


# Configuration

@mcp.tool()
async def configure_email_provider(
    provider: str,
    credentials: Dict[str, str]
) -> Dict[str, Any]:
    """Configure email provider with OAuth credentials.

    Args:
        provider: Email provider ("gmail" or "outlook")
        credentials: OAuth credentials dictionary
            For Gmail:
                - token: Access token
                - refresh_token: Refresh token
                - client_id: OAuth client ID
                - client_secret: OAuth client secret
            For Outlook:
                - access_token: Access token

    Returns:
        Dict with configuration status

    Security:
        - Uses OAuth 2.0 (no password storage)
        - Credentials never logged or persisted
        - Federal-standard authentication
    """
    return await email_ops.configure_provider(provider, credentials)


# Email Reading

@mcp.tool()
async def list_emails(
    folder: str = "INBOX",
    limit: int = 50,
    page_token: Optional[str] = None
) -> Dict[str, Any]:
    """List emails in a folder.

    Args:
        folder: Folder name (Gmail: INBOX, SENT; Outlook: Inbox, SentItems)
        limit: Maximum emails to return (default: 50, max: 100)
        page_token: Pagination token for next page

    Returns:
        Dict with email list, count, and next_page_token

    Security:
        - Requires configured provider
        - Folder name validated
        - Pagination limits enforced
    """
    return await email_ops.list_emails(folder, limit, page_token)


@mcp.tool()
async def read_email(message_id: str) -> Dict[str, Any]:
    """Read full email content by ID.

    Args:
        message_id: Email message ID from list_emails

    Returns:
        Dict with email details (from, to, cc, subject, date, body)

    Security:
        - Message ID validated
        - No path traversal possible
        - Sanitized output
    """
    return await email_ops.read_email(message_id)


@mcp.tool()
async def search_emails(
    query: str,
    limit: int = 50
) -> Dict[str, Any]:
    """Search emails by query.

    Args:
        query: Search query string
            Gmail: Use Gmail search syntax (from:user@example.com, subject:meeting)
            Outlook: Use KQL syntax (from:user@example.com AND subject:meeting)
        limit: Maximum results (default: 50, max: 100)

    Returns:
        Dict with matching emails

    Security:
        - Query validated for injection attacks
        - XSS patterns blocked
        - Result limits enforced
    """
    return await email_ops.search_emails(query, limit)


# Email Writing

@mcp.tool()
async def send_email(
    to: List[str],
    subject: str,
    body: str,
    cc: Optional[List[str]] = None,
    bcc: Optional[List[str]] = None,
    html: bool = False
) -> Dict[str, Any]:
    """Send new email.

    Args:
        to: List of recipient email addresses (max 100)
        subject: Email subject (max 998 chars)
        body: Email body content (max 10MB)
        cc: Optional CC recipients (max 50)
        bcc: Optional BCC recipients (max 50)
        html: Whether body contains HTML

    Returns:
        Dict with send status and message ID

    Security:
        - All email addresses validated (RFC 5322)
        - Subject checked for header injection
        - Body scanned for XSS/malicious content
        - Recipient limits enforced (prevent spam)
        - HTML sanitized if enabled
    """
    return await email_ops.send_email(to, subject, body, cc, bcc, html)


@mcp.tool()
async def reply_email(
    message_id: str,
    body: str,
    reply_all: bool = False,
    html: bool = False
) -> Dict[str, Any]:
    """Reply to an email.

    Args:
        message_id: Original message ID
        body: Reply content (max 10MB)
        reply_all: Whether to reply to all recipients
        html: Whether body contains HTML

    Returns:
        Dict with send status

    Security:
        - Message ID validated
        - Body scanned for malicious content
        - Reply-to headers validated
    """
    return await email_ops.reply_email(message_id, body, reply_all, html)


@mcp.tool()
async def forward_email(
    message_id: str,
    to: List[str],
    comment: Optional[str] = None
) -> Dict[str, Any]:
    """Forward an email to new recipients.

    Args:
        message_id: Original message ID
        to: List of recipient email addresses (max 100)
        comment: Optional forwarding comment

    Returns:
        Dict with send status

    Security:
        - All recipients validated
        - Comment scanned for malicious content
        - Original message sanitized
    """
    return await email_ops.forward_email(message_id, to, comment)


# Email Management

@mcp.tool()
async def delete_email(message_id: str) -> Dict[str, Any]:
    """Delete email (move to trash).

    Args:
        message_id: Message ID to delete

    Returns:
        Dict with delete status

    Security:
        - Message ID validated
        - Soft delete (trash, not permanent)
        - Audit logged
    """
    return await email_ops.delete_email(message_id)


@mcp.tool()
async def mark_email_read(
    message_id: str,
    read: bool = True
) -> Dict[str, Any]:
    """Mark email as read or unread.

    Args:
        message_id: Message ID
        read: True to mark as read, False for unread

    Returns:
        Dict with status

    Security:
        - Message ID validated
        - No side effects
    """
    return await email_ops.mark_read(message_id, read)


@mcp.tool()
async def get_folders() -> Dict[str, Any]:
    """Get list of available email folders/labels.

    Returns:
        Dict with folder names

    Security:
        - No user input required
        - Safe metadata operation
    """
    return await email_ops.get_folders()


# Create FastAPI application
app = mcp.streamable_http_app()
