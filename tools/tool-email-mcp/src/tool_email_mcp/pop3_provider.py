"""POP3/SMTP provider for email accounts (like Gmail POP).

POP3 is simpler than IMAP but more limited:
- Only accesses INBOX (no folder support)
- Basic operations: list, read, delete
- No native search, mark read, or folder operations
"""

import poplib
import smtplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import parseaddr, formataddr
from typing import Dict, List, Optional, Any
from datetime import datetime
import asyncio

from .providers import EmailProvider


class POP3Provider(EmailProvider):
    """Generic POP3/SMTP provider for email accounts (Gmail, etc)."""

    def __init__(
        self,
        username: str,
        password: str,
        pop_server: str,
        pop_port: int = 995,
        smtp_server: str = None,
        smtp_port: int = 587,
        use_ssl: bool = True,
        use_starttls: bool = True
    ):
        """Initialize POP3/SMTP provider.

        Args:
            username: Email address
            password: Email password (or app-specific password for Gmail)
            pop_server: POP3 server hostname
            pop_port: POP3 port (default 995 for SSL)
            smtp_server: SMTP server hostname (defaults to pop_server)
            smtp_port: SMTP port (default 587 for STARTTLS)
            use_ssl: Use SSL for POP3 (default True)
            use_starttls: Use STARTTLS for SMTP (default True)
        """
        self.username = username
        self.password = password
        self.pop_server = pop_server
        self.pop_port = pop_port
        self.smtp_server = smtp_server or pop_server
        self.smtp_port = smtp_port
        self.use_ssl = use_ssl
        self.use_starttls = use_starttls
        self._pop = None

    def _get_pop_connection(self) -> poplib.POP3_SSL:
        """Get or create POP3 connection."""
        if self._pop is None:
            if self.use_ssl:
                self._pop = poplib.POP3_SSL(self.pop_server, self.pop_port)
            else:
                self._pop = poplib.POP3(self.pop_server, self.pop_port)
            self._pop.user(self.username)
            self._pop.pass_(self.password)
        return self._pop

    async def list_emails(
        self,
        folder: str = "INBOX",
        limit: int = 50,
        page_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """List emails (POP3 only supports INBOX)."""
        def _list():
            pop = self._get_pop_connection()

            # Get message count
            num_messages = len(pop.list()[1])

            if num_messages == 0:
                return {
                    "success": True,
                    "emails": [],
                    "count": 0,
                    "next_page_token": None
                }

            # Calculate range for pagination
            start_idx = int(page_token) if page_token else 0
            end_idx = min(start_idx + limit, num_messages)

            emails = []
            # POP3 messages are numbered from 1
            for i in range(num_messages - start_idx, max(0, num_messages - end_idx), -1):
                try:
                    # Get message headers only
                    response, lines, octets = pop.top(i, 0)
                    msg = email.message_from_bytes(b'\r\n'.join(lines))

                    emails.append({
                        "id": str(i),  # POP3 uses numeric IDs
                        "from": msg.get("From", ""),
                        "to": msg.get("To", ""),
                        "subject": msg.get("Subject", ""),
                        "date": msg.get("Date", ""),
                        "snippet": ""  # Would need full body for snippet
                    })
                except Exception as e:
                    continue

            next_token = str(end_idx) if end_idx < num_messages else None

            return {
                "success": True,
                "emails": emails,
                "count": len(emails),
                "next_page_token": next_token
            }

        return await asyncio.get_event_loop().run_in_executor(None, _list)

    async def read_email(self, message_id: str) -> Dict[str, Any]:
        """Read email by ID (POP3 numeric ID)."""
        def _read():
            pop = self._get_pop_connection()
            msg_num = int(message_id)

            # Retrieve full message
            response, lines, octets = pop.retr(msg_num)
            msg = email.message_from_bytes(b'\r\n'.join(lines))

            # Extract body
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        payload = part.get_payload(decode=True)
                        if payload:
                            body = payload.decode('utf-8', errors='ignore')
                            break
            else:
                payload = msg.get_payload(decode=True)
                if payload:
                    body = payload.decode('utf-8', errors='ignore')

            return {
                "success": True,
                "id": message_id,
                "from": msg.get("From", ""),
                "to": msg.get("To", ""),
                "cc": msg.get("Cc", ""),
                "subject": msg.get("Subject", ""),
                "date": msg.get("Date", ""),
                "body": body,
                "labels": []  # POP3 doesn't have labels
            }

        return await asyncio.get_event_loop().run_in_executor(None, _read)

    async def send_email(
        self,
        to: List[str],
        subject: str,
        body: str,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        html: bool = False
    ) -> Dict[str, Any]:
        """Send email via SMTP."""
        def _send():
            # Create message
            if html:
                msg = MIMEMultipart()
                msg.attach(MIMEText(body, 'html'))
            else:
                msg = MIMEText(body, 'plain')

            msg['From'] = self.username
            msg['To'] = ', '.join(to)
            msg['Subject'] = subject

            if cc:
                msg['Cc'] = ', '.join(cc)

            # Combine all recipients
            all_recipients = to + (cc or []) + (bcc or [])

            # Connect to SMTP server
            smtp = smtplib.SMTP(self.smtp_server, self.smtp_port)

            if self.use_starttls:
                smtp.starttls()

            smtp.login(self.username, self.password)
            smtp.send_message(msg, from_addr=self.username, to_addrs=all_recipients)
            smtp.quit()

            return {
                "success": True,
                "message_id": msg.get('Message-ID', 'unknown'),
                "thread_id": None
            }

        return await asyncio.get_event_loop().run_in_executor(None, _send)

    async def reply_email(
        self,
        message_id: str,
        body: str,
        reply_all: bool = False,
        html: bool = False
    ) -> Dict[str, Any]:
        """Reply to email."""
        # First, read the original message
        original = await self.read_email(message_id)
        if not original.get("success"):
            return original

        # Parse original sender
        from_addr = parseaddr(original["from"])[1]
        subject = original["subject"]
        if not subject.startswith("Re: "):
            subject = f"Re: {subject}"

        # Send reply
        to = [from_addr]
        if reply_all:
            # Add CC recipients
            cc_addrs = [parseaddr(addr)[1] for addr in original.get("cc", "").split(",") if addr]
            return await self.send_email(to, subject, body, cc=cc_addrs, html=html)
        else:
            return await self.send_email(to, subject, body, html=html)

    async def forward_email(
        self,
        message_id: str,
        to: List[str],
        comment: Optional[str] = None
    ) -> Dict[str, Any]:
        """Forward email."""
        # Read original message
        original = await self.read_email(message_id)
        if not original.get("success"):
            return original

        subject = original["subject"]
        if not subject.startswith("Fwd: "):
            subject = f"Fwd: {subject}"

        # Build forwarded body
        body = ""
        if comment:
            body = f"{comment}\n\n"
        body += f"---------- Forwarded message ---------\n"
        body += f"From: {original['from']}\n"
        body += f"Date: {original['date']}\n"
        body += f"Subject: {original['subject']}\n"
        body += f"To: {original['to']}\n\n"
        body += original['body']

        return await self.send_email(to, subject, body)

    async def delete_email(self, message_id: str) -> Dict[str, Any]:
        """Delete email from server."""
        def _delete():
            pop = self._get_pop_connection()
            msg_num = int(message_id)
            pop.dele(msg_num)
            return {"success": True}

        return await asyncio.get_event_loop().run_in_executor(None, _delete)

    async def search_emails(
        self,
        query: str,
        limit: int = 50
    ) -> Dict[str, Any]:
        """Search emails (POP3 doesn't support server-side search).

        This downloads all message headers and searches locally.
        """
        def _search():
            pop = self._get_pop_connection()
            num_messages = len(pop.list()[1])

            emails = []
            query_lower = query.lower()

            # Search through messages
            for i in range(num_messages, 0, -1):
                if len(emails) >= limit:
                    break

                try:
                    response, lines, octets = pop.top(i, 10)  # Get headers + first 10 lines
                    msg = email.message_from_bytes(b'\r\n'.join(lines))

                    # Simple text search in subject, from, to
                    searchable = f"{msg.get('Subject', '')} {msg.get('From', '')} {msg.get('To', '')}".lower()

                    if query_lower in searchable:
                        emails.append({
                            "id": str(i),
                            "from": msg.get("From", ""),
                            "to": msg.get("To", ""),
                            "subject": msg.get("Subject", ""),
                            "date": msg.get("Date", ""),
                            "snippet": ""
                        })
                except Exception:
                    continue

            return {
                "success": True,
                "emails": emails,
                "count": len(emails)
            }

        return await asyncio.get_event_loop().run_in_executor(None, _search)

    async def mark_read(self, message_id: str, read: bool = True) -> Dict[str, Any]:
        """Mark email as read (POP3 doesn't support this)."""
        return {
            "success": False,
            "error": "POP3 does not support marking messages as read/unread"
        }

    async def get_folders(self) -> Dict[str, Any]:
        """Get list of folders (POP3 only has INBOX)."""
        return {
            "success": True,
            "folders": ["INBOX"]
        }

    def close(self):
        """Close POP3 connection."""
        if self._pop:
            try:
                self._pop.quit()
            except:
                pass
            self._pop = None
