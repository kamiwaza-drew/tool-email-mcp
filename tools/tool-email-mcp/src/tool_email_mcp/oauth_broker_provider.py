"""OAuth Broker provider for Email MCP Tool.

Uses Kamiwaza OAuth Broker as a proxy for Gmail API operations,
providing secure token management with automatic refresh.
"""

import base64
import json
from typing import Dict, List, Optional, Any
from email.mime.text import MIMEText

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

from .providers import EmailProvider


class OAuthBrokerProvider(EmailProvider):
    """Email provider that uses Kamiwaza OAuth Broker as proxy.

    This provider never sees or stores OAuth tokens. All Gmail API calls
    are proxied through the OAuth Broker which handles token management,
    refresh, and policy enforcement.
    """

    def __init__(self, credentials_dict: Dict[str, str]):
        """Initialize OAuth Broker provider.

        Args:
            credentials_dict: Configuration dictionary with:
                - kamiwaza_token: Kamiwaza API token for authentication
                - oauth_broker_url: Base URL of OAuth Broker service
                - app_installation_id: App installation ID
                - tool_id: Tool identifier (default: "email-mcp")
        """
        if not REQUESTS_AVAILABLE:
            raise ImportError("requests library not installed")

        self.kamiwaza_token = credentials_dict.get("kamiwaza_token")
        self.broker_url = credentials_dict.get("oauth_broker_url")
        self.app_id = credentials_dict.get("app_installation_id")
        self.tool_id = credentials_dict.get("tool_id", "email-mcp")

        if not all([self.kamiwaza_token, self.broker_url, self.app_id]):
            raise ValueError(
                "Missing required credentials: kamiwaza_token, oauth_broker_url, app_installation_id"
            )

    def _proxy_call(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Make proxy call to OAuth Broker.

        Args:
            endpoint: Proxy endpoint name (e.g., "search", "getMessage")
            data: Request payload

        Returns:
            Response data from OAuth Broker

        Raises:
            ConnectionError: If not authenticated with Google
            requests.HTTPError: If request fails
        """
        url = f"{self.broker_url}/proxy/google/gmail/{endpoint}"
        params = {
            "app_id": self.app_id,
            "tool_id": self.tool_id
        }

        try:
            response = requests.post(
                url,
                params=params,
                json=data,
                headers={
                    "Authorization": f"Bearer {self.kamiwaza_token}",
                    "Content-Type": "application/json"
                },
                timeout=30
            )

            if response.status_code == 401:
                raise ConnectionError(
                    "Not authenticated with Google. Please connect your Google account."
                )

            response.raise_for_status()
            return response.json()

        except requests.exceptions.Timeout:
            raise TimeoutError("OAuth Broker request timed out")
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"OAuth Broker request failed: {e}")

    def _construct_message(
        self,
        to: List[str],
        subject: str,
        body: str,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        html: bool = False
    ) -> str:
        """Construct RFC 2822 email message.

        Args:
            to: Recipient email addresses
            subject: Email subject
            body: Email body
            cc: CC recipients
            bcc: BCC recipients
            html: Whether body is HTML

        Returns:
            Email message as string
        """
        message = MIMEText(body, "html" if html else "plain")
        message["To"] = ", ".join(to)
        message["Subject"] = subject
        if cc:
            message["Cc"] = ", ".join(cc)
        if bcc:
            message["Bcc"] = ", ".join(bcc)

        return message.as_string()

    async def list_emails(
        self,
        folder: str = "INBOX",
        limit: int = 50,
        page_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """List emails in folder via OAuth Broker."""
        try:
            # OAuth Broker search endpoint supports label filtering
            payload = {
                "query": f"in:{folder.lower()}",
                "max_results": min(limit, 500)
            }
            if page_token:
                payload["page_token"] = page_token

            result = self._proxy_call("search", payload)

            # Transform response to match EmailProvider interface
            emails = []
            for msg in result.get("messages", []):
                emails.append({
                    "id": msg.get("id"),
                    "from": msg.get("from", ""),
                    "to": msg.get("to", ""),
                    "subject": msg.get("subject", ""),
                    "date": msg.get("date", ""),
                    "snippet": msg.get("snippet", "")
                })

            return {
                "success": True,
                "emails": emails,
                "count": len(emails),
                "next_page_token": result.get("next_page_token")
            }

        except ConnectionError as e:
            return {
                "success": False,
                "error": str(e),
                "auth_required": True
            }
        except Exception as e:
            return {"success": False, "error": f"Error listing emails: {e}"}

    async def read_email(self, message_id: str) -> Dict[str, Any]:
        """Read email by ID via OAuth Broker."""
        try:
            payload = {
                "message_id": message_id,
                "format": "full"
            }

            result = self._proxy_call("getMessage", payload)

            # Transform response to match EmailProvider interface
            return {
                "success": True,
                "id": result.get("id"),
                "from": result.get("from", ""),
                "to": result.get("to", ""),
                "cc": result.get("cc", ""),
                "subject": result.get("subject", ""),
                "date": result.get("date", ""),
                "body": result.get("body", ""),
                "labels": result.get("labels", [])
            }

        except ConnectionError as e:
            return {
                "success": False,
                "error": str(e),
                "auth_required": True
            }
        except Exception as e:
            return {"success": False, "error": f"Error reading email: {e}"}

    async def send_email(
        self,
        to: List[str],
        subject: str,
        body: str,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        html: bool = False
    ) -> Dict[str, Any]:
        """Send email via OAuth Broker."""
        try:
            # Construct RFC 2822 message
            message = self._construct_message(to, subject, body, cc, bcc, html)

            # Encode as base64 URL-safe string
            raw = base64.urlsafe_b64encode(message.encode()).decode()

            payload = {
                "raw_message": raw
            }

            result = self._proxy_call("send", payload)

            return {
                "success": True,
                "message_id": result.get("id"),
                "thread_id": result.get("threadId")
            }

        except ConnectionError as e:
            return {
                "success": False,
                "error": str(e),
                "auth_required": True
            }
        except Exception as e:
            return {"success": False, "error": f"Error sending email: {e}"}

    async def reply_email(
        self,
        message_id: str,
        body: str,
        reply_all: bool = False,
        html: bool = False
    ) -> Dict[str, Any]:
        """Reply to email via OAuth Broker."""
        try:
            # First get the original message to extract headers
            original = await self.read_email(message_id)
            if not original.get("success"):
                return original

            # Build reply message
            message = MIMEText(body, "html" if html else "plain")
            message["To"] = original.get("from", "")
            if reply_all and original.get("cc"):
                message["Cc"] = original.get("cc", "")

            subject = original.get("subject", "")
            if not subject.startswith("Re:"):
                subject = f"Re: {subject}"
            message["Subject"] = subject

            # Note: In-Reply-To and References headers would require
            # message-id from original, which may not be available
            # through the simplified proxy interface

            raw = base64.urlsafe_b64encode(message.as_string().encode()).decode()

            payload = {
                "raw_message": raw
            }

            result = self._proxy_call("send", payload)

            return {
                "success": True,
                "message_id": result.get("id"),
                "thread_id": result.get("threadId")
            }

        except ConnectionError as e:
            return {
                "success": False,
                "error": str(e),
                "auth_required": True
            }
        except Exception as e:
            return {"success": False, "error": f"Error replying to email: {e}"}

    async def delete_email(self, message_id: str) -> Dict[str, Any]:
        """Delete email via OAuth Broker.

        Note: Gmail API trash operation would require a separate proxy endpoint.
        For now, we use the modify labels approach to add TRASH label.
        """
        try:
            # Use modify endpoint to add TRASH label
            payload = {
                "message_id": message_id,
                "add_labels": ["TRASH"],
                "remove_labels": ["INBOX"]
            }

            # Note: This assumes a "modify" proxy endpoint exists
            # If not available, this operation will need to be implemented
            result = self._proxy_call("modify", payload)

            return {
                "success": True,
                "message_id": message_id,
                "status": "trashed"
            }

        except ConnectionError as e:
            return {
                "success": False,
                "error": str(e),
                "auth_required": True
            }
        except Exception as e:
            # If modify endpoint doesn't exist, provide helpful error
            if "404" in str(e):
                return {
                    "success": False,
                    "error": "Delete operation not yet supported via OAuth Broker"
                }
            return {"success": False, "error": f"Error deleting email: {e}"}

    async def search_emails(
        self,
        query: str,
        limit: int = 50
    ) -> Dict[str, Any]:
        """Search emails via OAuth Broker."""
        try:
            payload = {
                "query": query,
                "max_results": min(limit, 500)
            }

            result = self._proxy_call("search", payload)

            # Transform response
            emails = []
            for msg in result.get("messages", []):
                emails.append({
                    "id": msg.get("id"),
                    "from": msg.get("from", ""),
                    "subject": msg.get("subject", ""),
                    "date": msg.get("date", ""),
                    "snippet": msg.get("snippet", "")
                })

            return {
                "success": True,
                "emails": emails,
                "count": len(emails)
            }

        except ConnectionError as e:
            return {
                "success": False,
                "error": str(e),
                "auth_required": True
            }
        except Exception as e:
            return {"success": False, "error": f"Error searching emails: {e}"}

    async def mark_read(self, message_id: str, read: bool = True) -> Dict[str, Any]:
        """Mark email as read/unread via OAuth Broker."""
        try:
            # Use modify endpoint to add/remove UNREAD label
            payload = {
                "message_id": message_id,
                "add_labels": [] if read else ["UNREAD"],
                "remove_labels": ["UNREAD"] if read else []
            }

            result = self._proxy_call("modify", payload)

            return {
                "success": True,
                "message_id": message_id,
                "status": "read" if read else "unread"
            }

        except ConnectionError as e:
            return {
                "success": False,
                "error": str(e),
                "auth_required": True
            }
        except Exception as e:
            # If modify endpoint doesn't exist, provide helpful error
            if "404" in str(e):
                return {
                    "success": False,
                    "error": "Mark read operation not yet supported via OAuth Broker"
                }
            return {"success": False, "error": f"Error marking email: {e}"}
