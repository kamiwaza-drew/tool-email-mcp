"""OAuth Broker provider for email operations.

Uses Kamiwaza OAuth Broker as a proxy to Gmail API, with automatic token management
and refresh. The tool never handles OAuth tokens directly - all token operations
are managed by the OAuth Broker service.
"""

import base64
import json
import logging
import os
from typing import Any

import requests
import urllib3

from .providers import EmailProvider

# Disable SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)

# Keycloak token endpoint (use KAMIWAZA_URL from env, fallback to localhost)
KAMIWAZA_URL = os.getenv("KAMIWAZA_URL", "https://localhost")
KEYCLOAK_TOKEN_ENDPOINT = f"{KAMIWAZA_URL}/realms/kamiwaza/protocol/openid-connect/token"


class OAuthBrokerProvider(EmailProvider):
    """Email provider that uses Kamiwaza OAuth Broker as proxy to Gmail."""

    def __init__(self, credentials_dict: dict[str, str]):
        """Initialize OAuth Broker provider.

        Args:
            credentials_dict: Configuration dictionary with:
                - kamiwaza_token_file: Path to file containing Kamiwaza PAT token (preferred)
                - kamiwaza_token: User's Kamiwaza PAT token (fallback, static)
                - oauth_broker_url: OAuth Broker base URL
                - app_installation_id: App installation ID
                - tool_id: Tool identifier for policy enforcement
        """
        # Support dynamic token reading from file (preferred for auto-refresh)
        self.token_file = credentials_dict.get("kamiwaza_token_file")
        self.static_token = credentials_dict.get("kamiwaza_token")

        self.broker_url = credentials_dict.get("oauth_broker_url")
        self.app_id = credentials_dict.get("app_installation_id")
        self.tool_id = credentials_dict.get("tool_id", "email-mcp")

        if not (self.token_file or self.static_token):
            raise ValueError("OAuth Broker provider requires either kamiwaza_token_file or kamiwaza_token")

        if not all([self.broker_url, self.app_id]):
            raise ValueError("OAuth Broker provider requires oauth_broker_url and app_installation_id")

        # Remove trailing slash from broker URL
        self.broker_url = self.broker_url.rstrip("/")

        # Log configuration mode
        if self.token_file:
            logger.info("OAuth Broker configured with dynamic token from file: %s", self.token_file)
        else:
            logger.warning("OAuth Broker configured with static token (will expire)")

    def _is_refresh_token(self, token: str) -> bool:
        """Check if token is a refresh token by decoding JWT payload.

        Args:
            token: JWT token string

        Returns:
            True if token type is "Offline" (refresh token), False otherwise
        """
        try:
            # Decode JWT payload (second part)
            parts = token.split(".")
            if len(parts) != 3:
                return False

            # Decode base64 payload
            payload_b64 = parts[1]
            # Add padding if needed
            padding = 4 - len(payload_b64) % 4
            if padding != 4:
                payload_b64 += "=" * padding

            payload_json = base64.urlsafe_b64decode(payload_b64).decode("utf-8")
            payload = json.loads(payload_json)

            # Check token type
            return payload.get("typ") == "Offline"
        except Exception as e:
            logger.warning(f"Could not decode token to check type: {e}")
            return False

    def _exchange_refresh_token(self, refresh_token: str) -> str:
        """Exchange refresh token for access token via Keycloak.

        Args:
            refresh_token: Offline/refresh token

        Returns:
            Access token string

        Raises:
            ConnectionError: If token exchange fails
        """
        try:
            response = requests.post(
                KEYCLOAK_TOKEN_ENDPOINT,
                data={"grant_type": "refresh_token", "client_id": "kamiwaza-platform", "refresh_token": refresh_token},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=10,
                verify=False,  # noqa: S501 Self-signed cert in development
            )

            if response.status_code != 200:
                logger.error("Token exchange failed: %s %s", response.status_code, response.text)
                raise ConnectionError(f"Failed to exchange refresh token: {response.status_code}")

            token_data = response.json()
            access_token = token_data.get("access_token")

            if not access_token:
                raise ConnectionError("No access_token in token exchange response")

            logger.debug(
                "Exchanged refresh token for access token (expires in %ss)",
                token_data.get("expires_in"),
            )
            return access_token  # noqa: TRY300

        except requests.exceptions.RequestException as e:
            logger.exception("Token exchange request failed")
            raise ConnectionError("Token exchange failed: ") from e

    def _get_token(self) -> str:
        """Get current Kamiwaza access token.

        Priority order:
        1. Request context (per-request token from MCP bridge)
        2. Token file (dynamic refresh)
        3. Static token from env var

        Automatically exchanges refresh tokens for access tokens when needed.

        Returns:
            Current access token string
        """
        logger.debug("Retrieving authentication token")

        # Try request context first (per-request token from MCP bridge)
        try:
            from .context import get_current_request_token

            request_token = get_current_request_token()
            if request_token:
                logger.debug("Using per-request token from context")
                # Check if it's a refresh token and exchange if needed
                if self._is_refresh_token(request_token):
                    logger.debug("Exchanging refresh token for access token")
                    return self._exchange_refresh_token(request_token)
                return request_token
        except Exception as e:
            logger.debug("Could not retrieve request token: %s", str(e))

        # Fall back to token file (dynamic refresh)
        if self.token_file:
            try:
                with open(self.token_file) as f:
                    token = f.read().strip()
                    if not token:
                        raise ValueError(f"Token file {self.token_file} is empty")  # noqa: TRY301

                    logger.debug("Using token from file: %s", self.token_file)
                    # Check if it's a refresh token and exchange if needed
                    if self._is_refresh_token(token):
                        logger.debug("Exchanging refresh token for access token")
                        return self._exchange_refresh_token(token)

                    return token
            except FileNotFoundError:
                raise ConnectionError(f"Token file not found: {self.token_file}") from None
            except Exception as e:
                raise ConnectionError("Error reading token file") from e
        else:
            logger.debug("Using static token from configuration")
            # Static token - check if it's a refresh token
            if self._is_refresh_token(self.static_token):
                logger.debug("Exchanging refresh token for access token")
                return self._exchange_refresh_token(self.static_token)

            return self.static_token

    def _extract_body(self, payload: dict[str, Any]) -> str:
        """Extract email body from Gmail payload structure.

        Args:
            payload: Gmail message payload

        Returns:
            Email body text (decoded)
        """
        body = ""

        # Handle simple body (text/plain or text/html)
        if "body" in payload and payload["body"].get("data"):
            body = base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="ignore")

        # Handle multipart messages
        elif "parts" in payload:
            for part in payload["parts"]:
                mime_type = part.get("mimeType", "")

                # Prefer text/plain, fallback to text/html
                if mime_type == "text/plain" and part.get("body", {}).get("data"):
                    body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="ignore")
                    break
                elif mime_type == "text/html" and not body and part.get("body", {}).get("data"):
                    body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="ignore")

                # Handle nested multipart
                elif mime_type.startswith("multipart/") and "parts" in part:
                    body = self._extract_body(part)
                    if body:
                        break

        return body

    def _proxy_call(self, endpoint: str, data: dict[str, Any]) -> dict[str, Any]:  # noqa: C901
        """Make proxy call to OAuth Broker.

        Args:
            endpoint: Gmail API endpoint (e.g., "search", "getMessage", "send")
            data: Request data to send to Gmail API

        Returns:
            API response as dict

        Raises:
            ConnectionError: If not authenticated with Google (401 response)
            requests.HTTPError: For other HTTP errors
        """
        # Get fresh token on each request (supports dynamic refresh)
        token = self._get_token()

        url = f"{self.broker_url}/proxy/google/gmail/{endpoint}"
        params = {"app_id": self.app_id, "tool_id": self.tool_id}

        # Safe debug logging (no tokens, no request body)
        logger.debug("OAuth Broker proxy call: endpoint=%s url=%s params=%s", endpoint, url, params)

        # Use full token for actual request
        real_headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        try:
            response = requests.post(
                url,
                params=params,
                json=data,
                headers=real_headers,
                timeout=30,
                verify=False,  # noqa: S501 Disable SSL verification for self-signed certificates
            )

            logger.debug("OAuth Broker response: status=%s", response.status_code)

            try:
                response_json = response.json()
            except Exception:  # Intentionally catch all JSON parsing errors
                response_json = None
                logger.debug("OAuth Broker non-JSON response (truncated): %s", response.text[:500])

            # Handle authentication errors
            if response.status_code == 401:
                logger.error("401 UNAUTHORIZED from OAuth Broker")

                error_msg = (
                    "GOOGLE ACCOUNT NOT CONNECTED\n\n"
                    "Your Google account is not connected to this Kamiwaza app installation. "
                    "To use email features, you need to authenticate with Google.\n\n"
                    "STEPS TO FIX:\n"
                    "1. Go to Kamiwaza UI -> Settings -> External Connectors\n"
                    "2. Connect your Google Workspace / Gmail account\n"
                    "3. Review and approve the requested Gmail permissions\n\n"
                    "REQUIRED PERMISSIONS:\n"
                    "- gmail.readonly (read emails and settings)\n"
                    "- gmail.send (send emails)\n"
                    "- gmail.modify (mark as read/unread, apply labels)\n\n"
                    "Once connected, this tool will automatically use your Google account "
                    "for all email operations."
                )
                raise ConnectionError(error_msg)  # noqa: TRY301

            # Handle insufficient scope errors (500 with Gmail 401)
            if response.status_code == 500:
                try:
                    error_detail = (response_json or {}).get("detail", "")
                    if "401" in error_detail and "Unauthorized" in error_detail:
                        logger.error("INSUFFICIENT SCOPES - Gmail API returned 401")
                        logger.error("=" * 70)
                        logger.error("MISSING OAUTH SCOPE ERROR")
                        logger.error("=" * 70)
                        logger.error(f"Operation '{endpoint}' requires additional Gmail permissions.")
                        logger.error("")

                        # Construct helpful scope error message
                        kamiwaza_url = os.getenv("KAMIWAZA_URL", "https://localhost")
                        disconnect_url = f"{kamiwaza_url}/api/oauth-broker/connections/disconnect?app_id={self.app_id}&provider=google"
                        reconnect_url = f"{kamiwaza_url}/api/oauth-broker/google/start?app_id={self.app_id}"

                        # Provide specific guidance based on endpoint
                        if endpoint == "send":
                            logger.error("REQUIRED SCOPE: https://www.googleapis.com/auth/gmail.send")
                            logger.error("")
                            logger.error("USER ACTION NEEDED:")
                            logger.error("1. Go to Kamiwaza UI -> Settings -> External Connectors")
                            logger.error("2. Disconnect your Google Workspace connection")
                            logger.error("3. Reconnect and grant the 'Send email' permission when prompted")
                            logger.error("")
                        elif endpoint in ["labels", "trash"]:
                            logger.error("REQUIRED SCOPE: https://www.googleapis.com/auth/gmail.modify")
                            logger.error("")
                            logger.error("USER ACTION NEEDED:")
                            logger.error("1. Go to Kamiwaza UI -> Settings -> External Connectors")
                            logger.error("2. Disconnect your Google Workspace connection")
                            logger.error("3. Reconnect and grant the 'Modify email' permission when prompted")
                            logger.error("")

                        logger.error("CURRENT OPERATION FAILED:")
                        logger.error(f"  Endpoint: {endpoint}")
                        logger.error("  This requires permissions that weren't granted during initial connection.")
                        logger.error("=" * 70)

                        # Create comprehensive, LLM-friendly error message
                        scope_requirements = {
                            "send": ("gmail.send", "send emails on your behalf"),
                            "labels": ("gmail.modify", "modify email labels and settings"),
                            "trash": ("gmail.modify", "move emails to trash"),
                            "modify": ("gmail.modify", "modify email properties"),
                        }

                        scope_info = scope_requirements.get(endpoint, ("gmail.modify", "perform this operation"))
                        required_scope, operation_desc = scope_info

                        error_msg = (
                            f"INSUFFICIENT GMAIL PERMISSIONS\n\n"
                            f"The operation '{endpoint}' requires a Gmail permission that wasn't granted "
                            f"when you connected your Google account.\n\n"
                            f"MISSING PERMISSION:\n"
                            f"- Scope: {required_scope}\n"
                            f"- Allows: {operation_desc}\n\n"
                            f"STEPS TO FIX:\n"
                            f"1. Disconnect your Google account:\n"
                            f"   {disconnect_url}\n\n"
                            f"2. Reconnect with expanded permissions:\n"
                            f"   {reconnect_url}\n\n"
                            f"3. When prompted by Google, make sure to approve ALL requested permissions\n\n"
                            f"TIP: To avoid this issue, grant all Gmail permissions during initial connection:\n"
                            f"- gmail.readonly (read emails)\n"
                            f"- gmail.send (send emails)\n"
                            f"- gmail.modify (organize and manage emails)\n\n"
                            f"Once reconnected with the required permissions, this operation will work automatically."
                        )

                        if endpoint == "send":
                            error_msg = (
                                "INSUFFICIENT GMAIL PERMISSIONS\n\n"
                                "The operation 'send' requires a Gmail permission that wasn't granted "
                                "when you connected your Google account.\n\n"
                                "MISSING PERMISSION:\n"
                                "- Scope: gmail.send\n"
                                "- Allows: send emails on your behalf\n\n"
                                "STEPS TO FIX:\n"
                                f"1. Disconnect your Google account:\n"
                                f"   {disconnect_url}\n\n"
                                f"2. Reconnect with expanded permissions:\n"
                                f"   {reconnect_url}\n\n"
                                "3. When prompted by Google, make sure to approve the 'Send email' permission\n\n"
                                "TIP: Grant all Gmail permissions to avoid future issues."
                            )
                        elif endpoint in ["labels", "trash", "modify"]:
                            error_msg = (
                                f"INSUFFICIENT GMAIL PERMISSIONS\n\n"
                                f"The operation '{endpoint}' requires the 'gmail.modify' permission which allows "
                                f"organizing and managing your emails (labels, read/unread status, trash, etc.).\n\n"
                                f"STEPS TO FIX:\n"
                                f"1. Disconnect your Google account:\n"
                                f"   {disconnect_url}\n\n"
                                f"2. Reconnect with expanded permissions:\n"
                                f"   {reconnect_url}\n\n"
                                "3. When prompted by Google, approve the 'Modify email' permission\n\n"
                                "TIP: The modify permission is safe - it only allows organizing emails, not deleting permanently."
                            )

                        logger.error(error_msg)

                        if endpoint == "send":
                            error_msg = (
                                "Cannot send emails: Missing Gmail permission 'gmail.send'. "
                                "RECONNECT REQUIRED: Visit the disconnect URL above, then reconnect with 'Send email' permission."
                            )
                        elif endpoint in ["labels", "trash"]:
                            error_msg = (
                                f"Cannot {endpoint}: Missing Gmail permission 'gmail.modify'. "
                                "USER ACTION REQUIRED: Go to Kamiwaza UI -> Settings -> External Connectors, "
                                "disconnect Google Workspace, then reconnect and grant 'Modify email' permission."
                            )
                        else:
                            error_msg = (
                                f"Operation '{endpoint}' requires additional Gmail permissions. "
                                "USER ACTION REQUIRED: Reconnect Google account with broader permissions."
                            )

                        raise ConnectionError(error_msg)  # noqa: TRY301
                except ConnectionError:
                    raise  # Re-raise our helpful error message
                except Exception:  # noqa: S110 Intentionally catch all JSON parsing errors
                    pass  # Fall through to generic error handling

            response.raise_for_status()
            logger.debug("Request successful")
            return response.json()

        except requests.exceptions.ConnectionError as e:
            logger.exception("Connection error")
            raise ConnectionError("Cannot connect to OAuth Broker") from e
        except requests.exceptions.Timeout:
            logger.exception("Timeout error")
            raise ConnectionError("OAuth Broker request timed out") from None
        except Exception:
            logger.exception("Unexpected error")
            raise

    async def list_emails(
        self, folder: str = "INBOX", limit: int = 50, page_token: str | None = None
    ) -> dict[str, Any]:
        """List emails in folder."""
        try:
            # Use Gmail search API through OAuth Broker
            label_query = f"in:{folder.lower()}"
            data = {"query": label_query, "max_results": min(limit, 500), "page_token": page_token}

            result = self._proxy_call("search", data)

            # OAuth Broker returns raw Gmail API response (no "success" field)
            # Errors are handled via exceptions in _proxy_call
            # Transform OAuth Broker response to match expected format
            messages = result.get("messages", [])
            emails = []

            for msg in messages:
                # Get message details
                msg_data = self._proxy_call(
                    "getMessage",
                    {
                        "message_id": msg["id"],
                        "format": "metadata",
                        "metadata_headers": ["From", "To", "Subject", "Date"],
                    },
                )

                # Extract headers from Gmail API format
                headers_list = msg_data.get("payload", {}).get("headers", [])
                headers = {h["name"]: h["value"] for h in headers_list}

                emails.append({
                    "id": msg["id"],
                    "from": headers.get("From", ""),
                    "to": headers.get("To", ""),
                    "subject": headers.get("Subject", ""),
                    "date": headers.get("Date", ""),
                    "snippet": msg_data.get("snippet", ""),
                })

            return {
                "success": True,
                "emails": emails,
                "count": len(emails),
                "next_page_token": result.get("next_page_token"),
            }

        except ConnectionError as e:
            return {"success": False, "error": str(e)}
        except Exception as e:
            return {"success": False, "error": f"Error listing emails: {e}"}

    async def read_email(self, message_id: str) -> dict[str, Any]:
        """Read email by ID."""
        try:
            result = self._proxy_call("getMessage", {"message_id": message_id, "format": "full"})

            # Extract headers from Gmail API format
            headers_list = result.get("payload", {}).get("headers", [])
            headers = {h["name"]: h["value"] for h in headers_list}

            # Extract body from payload
            body = self._extract_body(result.get("payload", {}))

            return {
                "success": True,
                "id": message_id,
                "from": headers.get("From", ""),
                "to": headers.get("To", ""),
                "cc": headers.get("Cc", ""),
                "subject": headers.get("Subject", ""),
                "date": headers.get("Date", ""),
                "body": body,
                "labels": result.get("labelIds", []),
            }

        except ConnectionError as e:
            return {"success": False, "error": str(e)}
        except Exception as e:
            return {"success": False, "error": f"Error reading email: {e}"}

    async def send_email(
        self,
        to: list[str],
        subject: str,
        body: str,
        cc: list[str] | None = None,
        bcc: list[str] | None = None,
        html: bool = False,
    ) -> dict[str, Any]:
        """Send email."""
        try:
            # Construct MIME message
            from email.mime.text import MIMEText

            message = MIMEText(body, "html" if html else "plain")
            message["To"] = ", ".join(to)
            message["Subject"] = subject
            if cc:
                message["Cc"] = ", ".join(cc)
            if bcc:
                message["Bcc"] = ", ".join(bcc)

            # Encode for Gmail API
            raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")

            result = self._proxy_call("send", {"raw_message": raw})

            if not result.get("success"):
                return result

            return {"success": True, "message_id": result.get("id"), "thread_id": result.get("threadId")}

        except ConnectionError as e:
            return {"success": False, "error": str(e)}
        except Exception as e:
            return {"success": False, "error": f"Error sending email: {e}"}

    async def reply_email(
        self, message_id: str, body: str, reply_all: bool = False, html: bool = False
    ) -> dict[str, Any]:
        """Reply to email."""
        try:
            # Get original message to build reply
            original = self._proxy_call(
                "getMessage",
                {
                    "message_id": message_id,
                    "format": "metadata",
                    "metadata_headers": ["From", "To", "Cc", "Subject", "Message-ID"],
                },
            )

            if not original.get("success"):
                return original

            headers = original.get("headers", {})

            # Build reply message
            from email.mime.text import MIMEText

            message = MIMEText(body, "html" if html else "plain")
            message["To"] = headers.get("From", "")
            if reply_all and headers.get("Cc"):
                message["Cc"] = headers.get("Cc", "")

            subject = headers.get("Subject", "")
            if not subject.startswith("Re:"):
                subject = f"Re: {subject}"
            message["Subject"] = subject
            message["In-Reply-To"] = headers.get("Message-ID", "")

            # Encode for Gmail API
            raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")

            result = self._proxy_call("send", {"raw_message": raw, "thread_id": original.get("threadId")})

            if not result.get("success"):
                return result

            return {"success": True, "message_id": result.get("id"), "thread_id": result.get("threadId")}

        except ConnectionError as e:
            return {"success": False, "error": str(e)}
        except Exception as e:
            return {"success": False, "error": f"Error replying to email: {e}"}

    async def delete_email(self, message_id: str) -> dict[str, Any]:
        """Delete email (move to trash)."""
        try:
            # Use Gmail labels API to trash the message
            result = self._proxy_call("labels", {"message_id": message_id, "action": "trash"})

            if not result.get("success"):
                return result

            return {"success": True, "message_id": message_id, "status": "trashed"}  # noqa: TRY300

        except ConnectionError as e:
            return {"success": False, "error": str(e)}
        except Exception as e:
            return {"success": False, "error": f"Error deleting email: {e}"}

    async def search_emails(self, query: str, limit: int = 50) -> dict[str, Any]:
        """Search emails."""
        try:
            result = self._proxy_call("search", {"query": query, "max_results": min(limit, 500)})

            if not result.get("success"):
                return result

            messages = result.get("messages", [])
            emails = []

            for msg in messages:
                # Get message metadata
                msg_data = self._proxy_call(
                    "getMessage",
                    {"message_id": msg["id"], "format": "metadata", "metadata_headers": ["From", "Subject", "Date"]},
                )

                if msg_data.get("success"):
                    headers = msg_data.get("headers", {})
                    emails.append({
                        "id": msg["id"],
                        "from": headers.get("From", ""),
                        "subject": headers.get("Subject", ""),
                        "date": headers.get("Date", ""),
                        "snippet": msg_data.get("snippet", ""),
                    })

            return {"success": True, "emails": emails, "count": len(emails)}

        except ConnectionError as e:
            return {"success": False, "error": str(e)}
        except Exception as e:
            return {"success": False, "error": f"Error searching emails: {e}"}

    async def mark_read(self, message_id: str, read: bool = True) -> dict[str, Any]:
        """Mark email as read/unread."""
        try:
            action = "remove_unread" if read else "add_unread"
            result = self._proxy_call("labels", {"message_id": message_id, "action": action})

            if not result.get("success"):
                return result

            return {"success": True, "message_id": message_id, "status": "read" if read else "unread"}  # noqa: TRY300

        except ConnectionError as e:
            return {"success": False, "error": str(e)}
        except Exception as e:
            return {"success": False, "error": f"Error marking email: {e}"}
