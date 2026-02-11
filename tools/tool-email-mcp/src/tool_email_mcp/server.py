"""FastMCP server for Email operations with OAuth and IMAP authentication.

Exposes secure email tools through FastMCP/HTTP transport with federal-standard security.
Supports multi-provider OAuth (Gmail, Outlook) and IMAP/SMTP with session-based authentication.
"""

import os
from typing import Any

from dotenv import load_dotenv

try:
    from mcp import FastMCP
except ImportError:
    from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from starlette.requests import Request
from starlette.responses import JSONResponse

from .context import get_current_session
from .email_operations import EmailOperations
from .oauth_handler import OAuthHandler
from .providers_config import get_configured_providers
from .security import SecurityManager
from .session_manager import SessionManager

load_dotenv()
load_dotenv(".env.local")
load_dotenv(".env.imap")

# Initialize components
security_manager = SecurityManager()
email_ops = EmailOperations(security_manager)

# Session management (in-memory, cleared on restart)
session_timeout = int(os.getenv("SESSION_TIMEOUT", "3600"))  # 1 hour default
session_manager = SessionManager(default_timeout=session_timeout)
oauth_handler = OAuthHandler(session_manager)

# Note: Cleanup task will be started after event loop starts

# Check if OAuth Broker is configured via environment
# Prefer token file for auto-refresh, fall back to static token
oauth_broker_configured = all([
    os.getenv("KAMIWAZA_OAUTH_BROKER_URL"),
    os.getenv("KAMIWAZA_APP_INSTALLATION_ID"),
    (os.getenv("KAMIWAZA_TOKEN_FILE") or os.getenv("KAMIWAZA_TOKEN")),
])

# Check if IMAP credentials are configured via environment
imap_configured = all([os.getenv("IMAP_USERNAME"), os.getenv("IMAP_PASSWORD"), os.getenv("IMAP_SERVER")])

# Get OAuth providers for fallback authentication
oauth_providers = get_configured_providers()

if oauth_broker_configured:
    print("🔐 OAuth Broker integration enabled")
    print(f"   App Installation ID: {os.getenv('KAMIWAZA_APP_INSTALLATION_ID')}")
    print(f"   OAuth Broker URL: {os.getenv('KAMIWAZA_OAUTH_BROKER_URL')}")
    if os.getenv("KAMIWAZA_TOKEN_FILE"):
        print(f"   🔄 Using dynamic token from: {os.getenv('KAMIWAZA_TOKEN_FILE')}")
    else:
        print("   ⚠️ Using static token (will expire after 5 minutes)")
elif imap_configured:
    print("🔐 IMAP credentials configured via environment")
else:
    if oauth_providers:
        print(f"🔐 OAuth enabled for: {', '.join(oauth_providers)}")

print(f"⏱️  Session timeout: {session_timeout} seconds ({session_timeout // 60} minutes)")

# Disable DNS rebinding protection to allow requests via Docker networking
mcp = FastMCP(
    "tool-email-mcp",
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=False,
    ),
)


# ===== Helper Functions =====


async def ensure_imap_configured() -> dict[str, Any]:
    """Configure email provider from environment if available.

    Checks for OAuth Broker configuration first, then IMAP.

    Returns:
        Dict with success=True if configured, or error dict if not
    """
    # Check if already configured
    if email_ops.provider is not None:
        return {"success": True}

    # Try OAuth Broker first (preferred method for Kamiwaza deployments)
    if oauth_broker_configured:
        # Prefer token file for auto-refresh (continuously updated PAT)
        token_file = os.getenv("KAMIWAZA_TOKEN_FILE")
        config = {
            "oauth_broker_url": os.getenv("KAMIWAZA_OAUTH_BROKER_URL"),
            "app_installation_id": os.getenv("KAMIWAZA_APP_INSTALLATION_ID"),
            "tool_id": os.getenv("KAMIWAZA_TOOL_ID", "email-mcp"),
        }

        if token_file:
            config["kamiwaza_token_file"] = token_file
        else:
            # Fall back to static token (will expire)
            config["kamiwaza_token"] = os.getenv("KAMIWAZA_TOKEN")

        result = await email_ops.configure_provider("oauth-broker", config)
        return result

    # Fall back to IMAP if configured
    if imap_configured:
        result = await email_ops.configure_provider(
            "imap",
            {
                "username": os.getenv("IMAP_USERNAME"),
                "password": os.getenv("IMAP_PASSWORD"),
                "imap_server": os.getenv("IMAP_SERVER"),
                "imap_port": os.getenv("IMAP_PORT", "993"),
                "smtp_server": os.getenv("SMTP_SERVER", os.getenv("IMAP_SERVER")),
                "smtp_port": os.getenv("SMTP_PORT", "465"),
                "use_ssl": os.getenv("IMAP_USE_SSL", "true").lower() in ("true", "1", "yes"),
            },
        )
        return result

    return {
        "success": False,
        "error": "No email provider configured. Use configure_email_provider tool or set IMAP/OAuth Broker environment variables.",
    }


async def require_authentication() -> dict[str, Any]:
    """Check if current request has valid authentication.

    Returns:
        Dict with success=True if authenticated, or error dict if not
    """
    # First try IMAP from environment
    imap_result = await ensure_imap_configured()
    if imap_result.get("success"):
        return {"success": True}

    # Fall back to session-based OAuth
    session = get_current_session()

    if not session or not session.get("authenticated"):
        return {
            "success": False,
            "error": "Not authenticated. Please connect your email account.",
            "auth_required": True,
            "auth_urls": {provider: f"/oauth/authorize?provider={provider}" for provider in oauth_providers},
        }

    # Configure email operations with session provider
    await email_ops.configure_provider(
        session["provider"],
        {
            "token": session["access_token"],
            "refresh_token": None,  # No refresh token (security requirement)
            "client_id": os.getenv(f"OAUTH_{session['provider'].upper()}_CLIENT_ID", ""),
            "client_secret": os.getenv(f"OAUTH_{session['provider'].upper()}_CLIENT_SECRET", ""),
        },
    )

    return {"success": True}


# ===== Health Check Endpoint =====


@mcp.custom_route("/health", methods=["GET"])
async def health_check(request: Request):
    """Health check endpoint for Docker health checks.

    Returns:
        JSON with health status
    """
    return JSONResponse({"status": "healthy"})


# ===== OAuth Endpoints =====


@mcp.custom_route("/oauth/authorize", methods=["GET"])
async def oauth_authorize(request: Request):
    """Initiate OAuth flow.

    Query params:
        provider: "gmail" or "outlook"

    Returns:
        Redirect to provider's OAuth consent screen
    """
    return await oauth_handler.handle_authorize(request)


@mcp.custom_route("/oauth/callback", methods=["GET"])
async def oauth_callback(request: Request):
    """Handle OAuth callback from provider.

    Returns:
        HTML page showing authentication status
    """
    return await oauth_handler.handle_callback(request)


@mcp.custom_route("/oauth/status", methods=["GET"])
async def oauth_status(request: Request):
    """Get current OAuth authentication status.

    Returns:
        JSON with authentication status and available providers
    """
    session = get_current_session()

    if session and session.get("authenticated"):
        return JSONResponse({
            "authenticated": True,
            "provider": session.get("provider"),
            "email": session.get("user_email"),
            "expires_at": session.get("expires_at"),
        })

    # Check if IMAP is configured
    if imap_configured:
        return JSONResponse({
            "authenticated": True,
            "provider": "imap",
            "email": os.getenv("IMAP_USERNAME"),
            "configured_via": "environment",
        })

    return JSONResponse({
        "authenticated": False,
        "available_providers": list(oauth_providers),
        "auth_urls": {provider: f"/oauth/authorize?provider={provider}" for provider in oauth_providers},
    })


@mcp.custom_route("/oauth/logout", methods=["POST"])
async def oauth_logout(request: Request):
    """Logout current session.

    Returns:
        JSON with logout status
    """
    session = get_current_session()
    if session:
        session_id = session.get("session_id")
        if session_id:
            session_manager.delete_session(session_id)

    return JSONResponse({"success": True, "message": "Logged out successfully"})


# ===== MCP Tools =====


@mcp.tool()
async def configure_email_provider(provider: str, credentials: dict) -> dict[str, Any]:
    """Configure email provider with credentials.

    Args:
        provider: Provider type ("gmail", "outlook", or "imap")
        credentials: Provider-specific credentials
            For Gmail:
                - token: OAuth access token
                - refresh_token: OAuth refresh token
                - client_id: OAuth client ID
                - client_secret: OAuth client secret
            For Outlook:
                - access_token: OAuth access token
            For IMAP:
                - username: Email address
                - password: Email password
                - imap_server: IMAP server hostname
                - imap_port: IMAP port (default 993)
                - smtp_server: SMTP server (optional, defaults to imap_server)
                - smtp_port: SMTP port (default 465)
                - use_ssl: Use SSL/TLS (default "true")

    Returns:
        Dict with configuration status
    """
    validation = security_manager.validate_provider_config(provider, credentials)
    if not validation["valid"]:
        return {"success": False, "error": validation["error"]}

    return await email_ops.configure_provider(provider, credentials)


@mcp.tool()
async def list_emails(folder: str = "INBOX", limit: int = 50, page_token: str | None = None) -> dict[str, Any]:
    """List emails in a folder.

    Args:
        folder: Folder name (default: "INBOX")
        limit: Maximum number of emails to return (1-500)
        page_token: Pagination token from previous response

    Returns:
        Dict with email list and pagination info
    """
    auth_check = await require_authentication()
    if not auth_check.get("success"):
        return auth_check

    validation = security_manager.validate_list_params(folder, limit)
    if not validation["valid"]:
        return {"success": False, "error": validation["error"]}

    return await email_ops.list_emails(folder, limit, page_token)


@mcp.tool()
async def read_email(message_id: str) -> dict[str, Any]:
    """Read full email content by ID.

    Args:
        message_id: Email message ID

    Returns:
        Dict with full email details
    """
    auth_check = await require_authentication()
    if not auth_check.get("success"):
        return auth_check

    # Validate message ID (raises ValueError if invalid)
    try:
        validated_id = security_manager.validate_message_id(message_id)
    except ValueError as e:
        return {"success": False, "error": str(e)}

    return await email_ops.read_email(validated_id)


@mcp.tool()
async def send_email(
    to: list[str],
    subject: str,
    body: str,
    cc: list[str] | None = None,
    bcc: list[str] | None = None,
    html: bool = False,
) -> dict[str, Any]:
    """Send a new email.

    Args:
        to: Recipient email addresses (max 100)
        subject: Email subject
        body: Email body content
        cc: CC recipients (optional)
        bcc: BCC recipients (optional)
        html: Whether body is HTML (default: False)

    Returns:
        Dict with send status and message ID
    """
    auth_check = await require_authentication()
    if not auth_check.get("success"):
        return auth_check

    # Validate all send_email parameters
    try:
        validated_to = security_manager.validate_email_list(to, max_count=100)
        validated_subject = security_manager.validate_subject(subject)
        validated_body = security_manager.validate_body(body, allow_html=html)

        validated_cc = None
        if cc:
            validated_cc = security_manager.validate_email_list(cc, max_count=100)

        validated_bcc = None
        if bcc:
            validated_bcc = security_manager.validate_email_list(bcc, max_count=100)

    except ValueError as e:
        return {"success": False, "error": str(e)}

    return await email_ops.send_email(
        validated_to, validated_subject, validated_body, validated_cc, validated_bcc, html
    )


@mcp.tool()
async def reply_email(message_id: str, body: str, reply_all: bool = False, html: bool = False) -> dict[str, Any]:
    """Reply to an email.

    Args:
        message_id: Original email message ID
        body: Reply body content
        reply_all: Whether to reply to all recipients (default: False)
        html: Whether body is HTML (default: False)

    Returns:
        Dict with send status
    """
    auth_check = await require_authentication()
    if not auth_check.get("success"):
        return auth_check

    # Validate message ID (raises ValueError if invalid)
    try:
        validated_id = security_manager.validate_message_id(message_id)
    except ValueError as e:
        return {"success": False, "error": str(e)}

    return await email_ops.reply_email(validated_id, body, reply_all, html)


@mcp.tool()
async def forward_email(message_id: str, to: list[str], comment: str | None = None) -> dict[str, Any]:
    """Forward an email to new recipients.

    Args:
        message_id: Original email message ID
        to: Recipient email addresses (max 100)
        comment: Optional comment to add before forwarded content

    Returns:
        Dict with send status
    """
    auth_check = await require_authentication()
    if not auth_check.get("success"):
        return auth_check

    validation = security_manager.validate_recipients(to)
    if not validation["valid"]:
        return {"success": False, "error": validation["error"]}

    return await email_ops.forward_email(message_id, to, comment)


@mcp.tool()
async def delete_email(message_id: str) -> dict[str, Any]:
    """Delete an email (move to trash).

    Args:
        message_id: Email message ID to delete

    Returns:
        Dict with deletion status
    """
    auth_check = await require_authentication()
    if not auth_check.get("success"):
        return auth_check

    # Validate message ID (raises ValueError if invalid)
    try:
        validated_id = security_manager.validate_message_id(message_id)
    except ValueError as e:
        return {"success": False, "error": str(e)}

    return await email_ops.delete_email(validated_id)


@mcp.tool()
async def mark_email_read(message_id: str, read: bool = True) -> dict[str, Any]:
    """Mark an email as read or unread.

    Args:
        message_id: Email message ID
        read: True to mark as read, False to mark as unread

    Returns:
        Dict with operation status
    """
    auth_check = await require_authentication()
    if not auth_check.get("success"):
        return auth_check

    # Validate message ID (raises ValueError if invalid)
    try:
        validated_id = security_manager.validate_message_id(message_id)
    except ValueError as e:
        return {"success": False, "error": str(e)}

    return await email_ops.mark_read(validated_id, read)


@mcp.tool()
async def search_emails(query: str, limit: int = 50) -> dict[str, Any]:
    """Search emails using provider-specific query syntax.

    Args:
        query: Search query (syntax varies by provider)
            Gmail: "from:sender@example.com subject:urgent after:2024/01/01"
            Outlook: "from:sender@example.com AND subject:urgent"
            IMAP: Simple text search
        limit: Maximum number of results (1-500)

    Returns:
        Dict with matching emails
    """
    auth_check = await require_authentication()
    if not auth_check.get("success"):
        return auth_check

    # Validate query only (limit validation happens in email_ops)
    try:
        validated_query = security_manager.validate_search_query(query)
    except ValueError as e:
        return {"success": False, "error": str(e)}

    return await email_ops.search_emails(validated_query, limit)


@mcp.tool()
async def get_folders() -> dict[str, Any]:
    """Get list of available email folders/labels.

    Returns:
        Dict with folder list
    """
    auth_check = await require_authentication()
    if not auth_check.get("success"):
        return auth_check

    return await email_ops.get_folders()


# Note: Middleware for session tracking is handled by FastMCP internally


# Expose for uvicorn
app = mcp.streamable_http_app()

if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8000))

    # Note: Session cleanup task not started for IMAP-only mode
    # OAuth sessions will be cleaned up on restart

    # Run with uvicorn
    uvicorn.run("tool_email_mcp.server:app", host="0.0.0.0", port=port)  # noqa: S104
