"""Email provider implementations for Gmail and Outlook.

Uses OAuth 2.0 for authentication following federal security standards.
"""

import base64
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from datetime import datetime

try:
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    from google.oauth2.credentials import Credentials
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False

try:
    import msal
    import requests
    MICROSOFT_AVAILABLE = True
except ImportError:
    MICROSOFT_AVAILABLE = False


class EmailProvider(ABC):
    """Abstract base class for email providers."""

    @abstractmethod
    async def list_emails(
        self,
        folder: str = "INBOX",
        limit: int = 50,
        page_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """List emails in folder."""
        pass

    @abstractmethod
    async def read_email(self, message_id: str) -> Dict[str, Any]:
        """Read email by ID."""
        pass

    @abstractmethod
    async def send_email(
        self,
        to: List[str],
        subject: str,
        body: str,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        html: bool = False
    ) -> Dict[str, Any]:
        """Send email."""
        pass

    @abstractmethod
    async def reply_email(
        self,
        message_id: str,
        body: str,
        reply_all: bool = False,
        html: bool = False
    ) -> Dict[str, Any]:
        """Reply to email."""
        pass

    @abstractmethod
    async def delete_email(self, message_id: str) -> Dict[str, Any]:
        """Delete email."""
        pass

    @abstractmethod
    async def search_emails(
        self,
        query: str,
        limit: int = 50
    ) -> Dict[str, Any]:
        """Search emails."""
        pass

    @abstractmethod
    async def mark_read(self, message_id: str, read: bool = True) -> Dict[str, Any]:
        """Mark email as read/unread."""
        pass


class GmailProvider(EmailProvider):
    """Gmail provider using Google API."""

    def __init__(self, credentials_dict: Dict[str, str]):
        """Initialize Gmail provider.

        Args:
            credentials_dict: OAuth credentials dictionary with:
                - token: Access token
                - refresh_token: Refresh token
                - client_id: OAuth client ID
                - client_secret: OAuth client secret
        """
        if not GOOGLE_AVAILABLE:
            raise ImportError("Google API libraries not installed")

        self.credentials = Credentials(
            token=credentials_dict.get("token"),
            refresh_token=credentials_dict.get("refresh_token"),
            token_uri="https://oauth2.googleapis.com/token",
            client_id=credentials_dict.get("client_id"),
            client_secret=credentials_dict.get("client_secret"),
        )

        self.service = build("gmail", "v1", credentials=self.credentials)

    async def list_emails(
        self,
        folder: str = "INBOX",
        limit: int = 50,
        page_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """List emails in folder."""
        try:
            params = {
                "userId": "me",
                "labelIds": [folder],
                "maxResults": min(limit, 500),
            }
            if page_token:
                params["pageToken"] = page_token

            results = self.service.users().messages().list(**params).execute()
            messages = results.get("messages", [])

            # Fetch message details
            emails = []
            for msg in messages:
                msg_data = self.service.users().messages().get(
                    userId="me",
                    id=msg["id"],
                    format="metadata",
                    metadataHeaders=["From", "To", "Subject", "Date"]
                ).execute()

                headers = {h["name"]: h["value"] for h in msg_data.get("payload", {}).get("headers", [])}
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
                "next_page_token": results.get("nextPageToken")
            }

        except HttpError as e:
            return {"success": False, "error": f"Gmail API error: {e}"}
        except Exception as e:
            return {"success": False, "error": f"Error listing emails: {e}"}

    async def read_email(self, message_id: str) -> Dict[str, Any]:
        """Read email by ID."""
        try:
            message = self.service.users().messages().get(
                userId="me",
                id=message_id,
                format="full"
            ).execute()

            headers = {h["name"]: h["value"] for h in message.get("payload", {}).get("headers", [])}

            # Extract body
            body = ""
            if "parts" in message["payload"]:
                for part in message["payload"]["parts"]:
                    if part["mimeType"] == "text/plain":
                        body = base64.urlsafe_b64decode(
                            part["body"].get("data", "")
                        ).decode("utf-8")
                        break
            else:
                body_data = message["payload"]["body"].get("data", "")
                if body_data:
                    body = base64.urlsafe_b64decode(body_data).decode("utf-8")

            return {
                "success": True,
                "id": message["id"],
                "from": headers.get("From", ""),
                "to": headers.get("To", ""),
                "cc": headers.get("Cc", ""),
                "subject": headers.get("Subject", ""),
                "date": headers.get("Date", ""),
                "body": body,
                "labels": message.get("labelIds", [])
            }

        except HttpError as e:
            return {"success": False, "error": f"Gmail API error: {e}"}
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
        """Send email."""
        try:
            from email.mime.text import MIMEText

            message = MIMEText(body, "html" if html else "plain")
            message["To"] = ", ".join(to)
            message["Subject"] = subject
            if cc:
                message["Cc"] = ", ".join(cc)
            if bcc:
                message["Bcc"] = ", ".join(bcc)

            raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
            result = self.service.users().messages().send(
                userId="me",
                body={"raw": raw}
            ).execute()

            return {
                "success": True,
                "message_id": result["id"],
                "thread_id": result["threadId"]
            }

        except HttpError as e:
            return {"success": False, "error": f"Gmail API error: {e}"}
        except Exception as e:
            return {"success": False, "error": f"Error sending email: {e}"}

    async def reply_email(
        self,
        message_id: str,
        body: str,
        reply_all: bool = False,
        html: bool = False
    ) -> Dict[str, Any]:
        """Reply to email."""
        try:
            # Get original message
            original = self.service.users().messages().get(
                userId="me",
                id=message_id,
                format="metadata",
                metadataHeaders=["From", "To", "Cc", "Subject", "Message-ID"]
            ).execute()

            headers = {h["name"]: h["value"] for h in original["payload"]["headers"]}

            # Build reply
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

            raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
            result = self.service.users().messages().send(
                userId="me",
                body={"raw": raw, "threadId": original["threadId"]}
            ).execute()

            return {
                "success": True,
                "message_id": result["id"],
                "thread_id": result["threadId"]
            }

        except HttpError as e:
            return {"success": False, "error": f"Gmail API error: {e}"}
        except Exception as e:
            return {"success": False, "error": f"Error replying to email: {e}"}

    async def delete_email(self, message_id: str) -> Dict[str, Any]:
        """Delete email (move to trash)."""
        try:
            self.service.users().messages().trash(
                userId="me",
                id=message_id
            ).execute()

            return {
                "success": True,
                "message_id": message_id,
                "status": "trashed"
            }

        except HttpError as e:
            return {"success": False, "error": f"Gmail API error: {e}"}
        except Exception as e:
            return {"success": False, "error": f"Error deleting email: {e}"}

    async def search_emails(
        self,
        query: str,
        limit: int = 50
    ) -> Dict[str, Any]:
        """Search emails."""
        try:
            results = self.service.users().messages().list(
                userId="me",
                q=query,
                maxResults=min(limit, 500)
            ).execute()

            messages = results.get("messages", [])
            emails = []
            for msg in messages:
                msg_data = self.service.users().messages().get(
                    userId="me",
                    id=msg["id"],
                    format="metadata",
                    metadataHeaders=["From", "Subject", "Date"]
                ).execute()

                headers = {h["name"]: h["value"] for h in msg_data["payload"]["headers"]}
                emails.append({
                    "id": msg["id"],
                    "from": headers.get("From", ""),
                    "subject": headers.get("Subject", ""),
                    "date": headers.get("Date", ""),
                    "snippet": msg_data.get("snippet", "")
                })

            return {
                "success": True,
                "emails": emails,
                "count": len(emails)
            }

        except HttpError as e:
            return {"success": False, "error": f"Gmail API error: {e}"}
        except Exception as e:
            return {"success": False, "error": f"Error searching emails: {e}"}

    async def mark_read(self, message_id: str, read: bool = True) -> Dict[str, Any]:
        """Mark email as read/unread."""
        try:
            if read:
                self.service.users().messages().modify(
                    userId="me",
                    id=message_id,
                    body={"removeLabelIds": ["UNREAD"]}
                ).execute()
            else:
                self.service.users().messages().modify(
                    userId="me",
                    id=message_id,
                    body={"addLabelIds": ["UNREAD"]}
                ).execute()

            return {
                "success": True,
                "message_id": message_id,
                "status": "read" if read else "unread"
            }

        except HttpError as e:
            return {"success": False, "error": f"Gmail API error: {e}"}
        except Exception as e:
            return {"success": False, "error": f"Error marking email: {e}"}


class OutlookProvider(EmailProvider):
    """Outlook provider using Microsoft Graph API."""

    def __init__(self, credentials_dict: Dict[str, str]):
        """Initialize Outlook provider.

        Args:
            credentials_dict: OAuth credentials dictionary with access_token
        """
        if not MICROSOFT_AVAILABLE:
            raise ImportError("Microsoft Graph libraries not installed")

        self.access_token = credentials_dict.get("access_token")
        self.graph_endpoint = "https://graph.microsoft.com/v1.0"
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }

    async def list_emails(
        self,
        folder: str = "Inbox",
        limit: int = 50,
        page_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """List emails in folder."""
        try:
            url = f"{self.graph_endpoint}/me/mailFolders/{folder}/messages"
            params = {"$top": min(limit, 999), "$orderby": "receivedDateTime DESC"}
            if page_token:
                url = page_token  # Skip token is full URL

            response = requests.get(url, headers=self.headers, params=params if not page_token else None)
            response.raise_for_status()
            data = response.json()

            emails = []
            for msg in data.get("value", []):
                emails.append({
                    "id": msg["id"],
                    "from": msg["from"]["emailAddress"]["address"] if msg.get("from") else "",
                    "to": ", ".join([r["emailAddress"]["address"] for r in msg.get("toRecipients", [])]),
                    "subject": msg.get("subject", ""),
                    "date": msg.get("receivedDateTime", ""),
                    "snippet": msg.get("bodyPreview", "")
                })

            return {
                "success": True,
                "emails": emails,
                "count": len(emails),
                "next_page_token": data.get("@odata.nextLink")
            }

        except requests.exceptions.RequestException as e:
            return {"success": False, "error": f"Graph API error: {e}"}
        except Exception as e:
            return {"success": False, "error": f"Error listing emails: {e}"}

    async def read_email(self, message_id: str) -> Dict[str, Any]:
        """Read email by ID."""
        try:
            url = f"{self.graph_endpoint}/me/messages/{message_id}"
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            msg = response.json()

            return {
                "success": True,
                "id": msg["id"],
                "from": msg["from"]["emailAddress"]["address"] if msg.get("from") else "",
                "to": ", ".join([r["emailAddress"]["address"] for r in msg.get("toRecipients", [])]),
                "cc": ", ".join([r["emailAddress"]["address"] for r in msg.get("ccRecipients", [])]),
                "subject": msg.get("subject", ""),
                "date": msg.get("receivedDateTime", ""),
                "body": msg["body"]["content"] if msg.get("body") else "",
                "is_read": msg.get("isRead", False)
            }

        except requests.exceptions.RequestException as e:
            return {"success": False, "error": f"Graph API error: {e}"}
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
        """Send email."""
        try:
            url = f"{self.graph_endpoint}/me/sendMail"
            message = {
                "message": {
                    "subject": subject,
                    "body": {
                        "contentType": "HTML" if html else "Text",
                        "content": body
                    },
                    "toRecipients": [{"emailAddress": {"address": addr}} for addr in to]
                }
            }

            if cc:
                message["message"]["ccRecipients"] = [{"emailAddress": {"address": addr}} for addr in cc]
            if bcc:
                message["message"]["bccRecipients"] = [{"emailAddress": {"address": addr}} for addr in bcc]

            response = requests.post(url, headers=self.headers, json=message)
            response.raise_for_status()

            return {
                "success": True,
                "status": "sent"
            }

        except requests.exceptions.RequestException as e:
            return {"success": False, "error": f"Graph API error: {e}"}
        except Exception as e:
            return {"success": False, "error": f"Error sending email: {e}"}

    async def reply_email(
        self,
        message_id: str,
        body: str,
        reply_all: bool = False,
        html: bool = False
    ) -> Dict[str, Any]:
        """Reply to email."""
        try:
            action = "replyAll" if reply_all else "reply"
            url = f"{self.graph_endpoint}/me/messages/{message_id}/{action}"

            payload = {
                "comment": body
            }

            response = requests.post(url, headers=self.headers, json=payload)
            response.raise_for_status()

            return {
                "success": True,
                "status": "sent"
            }

        except requests.exceptions.RequestException as e:
            return {"success": False, "error": f"Graph API error: {e}"}
        except Exception as e:
            return {"success": False, "error": f"Error replying to email: {e}"}

    async def delete_email(self, message_id: str) -> Dict[str, Any]:
        """Delete email."""
        try:
            url = f"{self.graph_endpoint}/me/messages/{message_id}"
            response = requests.delete(url, headers=self.headers)
            response.raise_for_status()

            return {
                "success": True,
                "message_id": message_id,
                "status": "deleted"
            }

        except requests.exceptions.RequestException as e:
            return {"success": False, "error": f"Graph API error: {e}"}
        except Exception as e:
            return {"success": False, "error": f"Error deleting email: {e}"}

    async def search_emails(
        self,
        query: str,
        limit: int = 50
    ) -> Dict[str, Any]:
        """Search emails."""
        try:
            url = f"{self.graph_endpoint}/me/messages"
            params = {
                "$search": f'"{query}"',
                "$top": min(limit, 999)
            }

            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            data = response.json()

            emails = []
            for msg in data.get("value", []):
                emails.append({
                    "id": msg["id"],
                    "from": msg["from"]["emailAddress"]["address"] if msg.get("from") else "",
                    "subject": msg.get("subject", ""),
                    "date": msg.get("receivedDateTime", ""),
                    "snippet": msg.get("bodyPreview", "")
                })

            return {
                "success": True,
                "emails": emails,
                "count": len(emails)
            }

        except requests.exceptions.RequestException as e:
            return {"success": False, "error": f"Graph API error: {e}"}
        except Exception as e:
            return {"success": False, "error": f"Error searching emails: {e}"}

    async def mark_read(self, message_id: str, read: bool = True) -> Dict[str, Any]:
        """Mark email as read/unread."""
        try:
            url = f"{self.graph_endpoint}/me/messages/{message_id}"
            payload = {"isRead": read}

            response = requests.patch(url, headers=self.headers, json=payload)
            response.raise_for_status()

            return {
                "success": True,
                "message_id": message_id,
                "status": "read" if read else "unread"
            }

        except requests.exceptions.RequestException as e:
            return {"success": False, "error": f"Graph API error: {e}"}
        except Exception as e:
            return {"success": False, "error": f"Error marking email: {e}"}
