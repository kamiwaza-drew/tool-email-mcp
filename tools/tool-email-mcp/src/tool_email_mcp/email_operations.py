"""Email operations with security validation.

Provides async wrappers around email providers with structured error handling
and federal-standard security controls.
"""

import os
from typing import Dict, List, Optional, Any
from .security import SecurityManager
from .providers import EmailProvider, GmailProvider, OutlookProvider
from .imap_provider import IMAPProvider
from .pop3_provider import POP3Provider
from .oauth_broker_provider import OAuthBrokerProvider


class EmailOperations:
    """Manages email operations with security validation."""

    def __init__(self, security_manager: SecurityManager):
        """Initialize email operations manager.

        Args:
            security_manager: Security manager for validation
        """
        self.security = security_manager
        self.provider: Optional[EmailProvider] = None

    def _ensure_provider(self) -> Dict[str, Any]:
        """Ensure provider is initialized.

        Returns:
            Error dict if provider not initialized, None otherwise
        """
        if self.provider is None:
            return {
                "success": False,
                "error": "Email provider not configured. Set credentials first."
            }
        return None

    async def configure_provider(
        self,
        provider_type: str,
        credentials: Dict[str, str]
    ) -> Dict[str, Any]:
        """Configure email provider with OAuth credentials, IMAP, or POP3.

        Args:
            provider_type: "gmail", "outlook", "imap", "pop3", or "oauth-broker"
            credentials: OAuth credentials dictionary or IMAP/POP3 credentials
                For IMAP:
                    - username: Email address
                    - password: Email password
                    - imap_server: IMAP server hostname
                    - imap_port: IMAP port (default 993)
                    - smtp_server: SMTP server hostname (optional, defaults to imap_server)
                    - smtp_port: SMTP port (default 465)
                    - use_ssl: Use SSL/TLS (default True)
                For POP3:
                    - username: Email address
                    - password: Email password
                    - pop_server: POP3 server hostname
                    - pop_port: POP3 port (default 995)
                    - smtp_server: SMTP server hostname
                    - smtp_port: SMTP port (default 587)
                    - use_ssl: Use SSL for POP3 (default True)
                    - use_starttls: Use STARTTLS for SMTP (default True)
                For OAuth Broker:
                    - kamiwaza_token: User's Kamiwaza PAT token
                    - oauth_broker_url: OAuth Broker base URL
                    - app_installation_id: App installation ID
                    - tool_id: Tool identifier (default "email-mcp")

        Returns:
            Dict with success status
        """
        try:
            if provider_type.lower() == "gmail":
                self.provider = GmailProvider(credentials)
                return {
                    "success": True,
                    "provider": "gmail",
                    "message": "Gmail provider configured"
                }
            elif provider_type.lower() == "outlook":
                self.provider = OutlookProvider(credentials)
                return {
                    "success": True,
                    "provider": "outlook",
                    "message": "Outlook provider configured"
                }
            elif provider_type.lower() == "oauth-broker":
                self.provider = OAuthBrokerProvider(credentials)
                return {
                    "success": True,
                    "provider": "oauth-broker",
                    "message": "OAuth Broker provider configured (Kamiwaza-managed)"
                }
            elif provider_type.lower() == "imap":
                self.provider = IMAPProvider(
                    username=credentials.get("username"),
                    password=credentials.get("password"),
                    imap_server=credentials.get("imap_server"),
                    imap_port=int(credentials.get("imap_port", 993)),
                    smtp_server=credentials.get("smtp_server"),
                    smtp_port=int(credentials.get("smtp_port", 465)),
                    use_ssl=credentials.get("use_ssl", "true").lower() == "true"
                )
                return {
                    "success": True,
                    "provider": "imap",
                    "message": f"IMAP provider configured for {credentials.get('username')}"
                }
            elif provider_type.lower() == "pop3":
                self.provider = POP3Provider(
                    username=credentials.get("username"),
                    password=credentials.get("password"),
                    pop_server=credentials.get("pop_server"),
                    pop_port=int(credentials.get("pop_port", 995)),
                    smtp_server=credentials.get("smtp_server"),
                    smtp_port=int(credentials.get("smtp_port", 587)),
                    use_ssl=credentials.get("use_ssl", "true").lower() == "true",
                    use_starttls=credentials.get("use_starttls", "true").lower() == "true"
                )
                return {
                    "success": True,
                    "provider": "pop3",
                    "message": f"POP3 provider configured for {credentials.get('username')}"
                }
            else:
                return {
                    "success": False,
                    "error": f"Unknown provider: {provider_type}. Use 'gmail', 'outlook', 'imap', 'pop3', or 'oauth-broker'"
                }

        except ImportError as e:
            return {
                "success": False,
                "error": f"Provider libraries not installed: {e}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error configuring provider: {e}"
            }

    async def list_emails(
        self,
        folder: str = "INBOX",
        limit: int = 50,
        page_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """List emails in folder.

        Args:
            folder: Folder name (Gmail: INBOX, SENT, etc.; Outlook: Inbox, SentItems, etc.)
            limit: Maximum number of emails to return
            page_token: Pagination token

        Returns:
            Dict with email list or error
        """
        try:
            error = self._ensure_provider()
            if error:
                return error

            # Validate inputs
            folder = self.security.validate_label(folder)
            limit = self.security.validate_pagination(limit)

            # Call provider
            return await self.provider.list_emails(folder, limit, page_token)

        except ValueError as e:
            return {"success": False, "error": f"Validation error: {e}"}
        except Exception as e:
            return {"success": False, "error": f"Error listing emails: {e}"}

    async def read_email(self, message_id: str) -> Dict[str, Any]:
        """Read email by ID.

        Args:
            message_id: Email message ID

        Returns:
            Dict with email content or error
        """
        try:
            error = self._ensure_provider()
            if error:
                return error

            # Validate message ID
            message_id = self.security.validate_message_id(message_id)

            # Call provider
            return await self.provider.read_email(message_id)

        except ValueError as e:
            return {"success": False, "error": f"Validation error: {e}"}
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
        """Send email.

        Args:
            to: List of recipient email addresses
            subject: Email subject
            body: Email body content
            cc: Optional CC recipients
            bcc: Optional BCC recipients
            html: Whether body is HTML

        Returns:
            Dict with send status or error
        """
        try:
            error = self._ensure_provider()
            if error:
                return error

            # Validate inputs
            to = self.security.validate_email_list(to)
            subject = self.security.validate_subject(subject)
            body = self.security.validate_body(body, allow_html=html)

            if cc:
                cc = self.security.validate_email_list(cc, max_count=50)
            if bcc:
                bcc = self.security.validate_email_list(bcc, max_count=50)

            # Check total recipient count
            total_recipients = len(to) + len(cc or []) + len(bcc or [])
            if total_recipients > self.security.MAX_RECIPIENTS:
                return {
                    "success": False,
                    "error": f"Too many total recipients (max {self.security.MAX_RECIPIENTS})"
                }

            # Call provider
            return await self.provider.send_email(to, subject, body, cc, bcc, html)

        except ValueError as e:
            return {"success": False, "error": f"Validation error: {e}"}
        except Exception as e:
            return {"success": False, "error": f"Error sending email: {e}"}

    async def reply_email(
        self,
        message_id: str,
        body: str,
        reply_all: bool = False,
        html: bool = False
    ) -> Dict[str, Any]:
        """Reply to email.

        Args:
            message_id: Original message ID
            body: Reply body content
            reply_all: Whether to reply to all recipients
            html: Whether body is HTML

        Returns:
            Dict with send status or error
        """
        try:
            error = self._ensure_provider()
            if error:
                return error

            # Validate inputs
            message_id = self.security.validate_message_id(message_id)
            body = self.security.validate_body(body, allow_html=html)

            # Call provider
            return await self.provider.reply_email(message_id, body, reply_all, html)

        except ValueError as e:
            return {"success": False, "error": f"Validation error: {e}"}
        except Exception as e:
            return {"success": False, "error": f"Error replying to email: {e}"}

    async def forward_email(
        self,
        message_id: str,
        to: List[str],
        comment: Optional[str] = None
    ) -> Dict[str, Any]:
        """Forward email.

        Args:
            message_id: Original message ID
            to: List of recipient email addresses
            comment: Optional forwarding comment

        Returns:
            Dict with send status or error
        """
        try:
            error = self._ensure_provider()
            if error:
                return error

            # Validate inputs
            message_id = self.security.validate_message_id(message_id)
            to = self.security.validate_email_list(to)

            # Read original email
            original = await self.provider.read_email(message_id)
            if not original.get("success"):
                return original

            # Build forwarded message
            subject = original.get("subject", "")
            if not subject.startswith("Fwd:"):
                subject = f"Fwd: {subject}"

            body_parts = []
            if comment:
                comment = self.security.validate_body(comment)
                body_parts.append(comment)
                body_parts.append("\n\n---------- Forwarded message ---------")

            body_parts.append(f"From: {original.get('from', '')}")
            body_parts.append(f"Date: {original.get('date', '')}")
            body_parts.append(f"Subject: {original.get('subject', '')}")
            body_parts.append(f"To: {original.get('to', '')}")
            body_parts.append("\n")
            body_parts.append(original.get("body", ""))

            body = "\n".join(body_parts)

            # Send as new email
            return await self.provider.send_email(to, subject, body)

        except ValueError as e:
            return {"success": False, "error": f"Validation error: {e}"}
        except Exception as e:
            return {"success": False, "error": f"Error forwarding email: {e}"}

    async def delete_email(self, message_id: str) -> Dict[str, Any]:
        """Delete email (move to trash).

        Args:
            message_id: Message ID to delete

        Returns:
            Dict with delete status or error
        """
        try:
            error = self._ensure_provider()
            if error:
                return error

            # Validate message ID
            message_id = self.security.validate_message_id(message_id)

            # Call provider
            return await self.provider.delete_email(message_id)

        except ValueError as e:
            return {"success": False, "error": f"Validation error: {e}"}
        except Exception as e:
            return {"success": False, "error": f"Error deleting email: {e}"}

    async def search_emails(
        self,
        query: str,
        limit: int = 50
    ) -> Dict[str, Any]:
        """Search emails.

        Args:
            query: Search query string
            limit: Maximum number of results

        Returns:
            Dict with search results or error
        """
        try:
            error = self._ensure_provider()
            if error:
                return error

            # Validate inputs
            query = self.security.validate_search_query(query)
            limit = self.security.validate_pagination(limit)

            # Call provider
            return await self.provider.search_emails(query, limit)

        except ValueError as e:
            return {"success": False, "error": f"Validation error: {e}"}
        except Exception as e:
            return {"success": False, "error": f"Error searching emails: {e}"}

    async def mark_read(
        self,
        message_id: str,
        read: bool = True
    ) -> Dict[str, Any]:
        """Mark email as read or unread.

        Args:
            message_id: Message ID
            read: True to mark as read, False for unread

        Returns:
            Dict with status or error
        """
        try:
            error = self._ensure_provider()
            if error:
                return error

            # Validate message ID
            message_id = self.security.validate_message_id(message_id)

            # Call provider
            return await self.provider.mark_read(message_id, read)

        except ValueError as e:
            return {"success": False, "error": f"Validation error: {e}"}
        except Exception as e:
            return {"success": False, "error": f"Error marking email: {e}"}

    async def get_folders(self) -> Dict[str, Any]:
        """Get list of available folders/labels.

        Returns:
            Dict with folder list or error
        """
        try:
            error = self._ensure_provider()
            if error:
                return error

            # This is provider-specific, return common folders
            if isinstance(self.provider, GmailProvider):
                folders = ["INBOX", "SENT", "DRAFT", "SPAM", "TRASH", "IMPORTANT", "STARRED"]
            else:  # Outlook
                folders = ["Inbox", "SentItems", "Drafts", "JunkEmail", "DeletedItems"]

            return {
                "success": True,
                "folders": folders
            }

        except Exception as e:
            return {"success": False, "error": f"Error getting folders: {e}"}
