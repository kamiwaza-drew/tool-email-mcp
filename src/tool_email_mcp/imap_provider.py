"""IMAP/SMTP provider for generic email accounts.

Simple username/password authentication for standard email servers.
"""

import imaplib
import smtplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import parseaddr, formataddr
from typing import Dict, List, Optional, Any
from datetime import datetime
import asyncio
from functools import partial

from .providers import EmailProvider


class IMAPProvider(EmailProvider):
    """Generic IMAP/SMTP provider for standard email accounts."""

    def __init__(
        self,
        username: str,
        password: str,
        imap_server: str,
        imap_port: int = 993,
        smtp_server: str = None,
        smtp_port: int = 465,
        use_ssl: bool = True
    ):
        """Initialize IMAP/SMTP provider.

        Args:
            username: Email address
            password: Email password
            imap_server: IMAP server hostname
            imap_port: IMAP port (default 993 for SSL)
            smtp_server: SMTP server hostname (defaults to imap_server)
            smtp_port: SMTP port (default 465 for SSL)
            use_ssl: Use SSL/TLS connection
        """
        self.username = username
        self.password = password
        self.imap_server = imap_server
        self.imap_port = imap_port
        self.smtp_server = smtp_server or imap_server
        self.smtp_port = smtp_port
        self.use_ssl = use_ssl
        self._imap = None

    def _get_imap_connection(self) -> imaplib.IMAP4_SSL:
        """Get or create IMAP connection."""
        # Only reconnect if connection doesn't exist or is in an invalid state
        if self._imap is None:
            if self.use_ssl:
                self._imap = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
            else:
                self._imap = imaplib.IMAP4(self.imap_server, self.imap_port)
            self._imap.login(self.username, self.password)
        elif self._imap.state not in ('AUTH', 'SELECTED'):
            # Connection is in bad state, reconnect
            try:
                self._imap.logout()
            except:
                pass
            if self.use_ssl:
                self._imap = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
            else:
                self._imap = imaplib.IMAP4(self.imap_server, self.imap_port)
            self._imap.login(self.username, self.password)
        return self._imap

    async def list_emails(
        self,
        folder: str = "INBOX",
        limit: int = 50,
        page_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """List emails in folder."""
        def _list():
            imap = self._get_imap_connection()
            imap.select(folder, readonly=True)

            # Search for all messages
            status, messages = imap.search(None, 'ALL')
            if status != 'OK':
                return {"success": False, "error": "Failed to search messages"}

            msg_ids = messages[0].split()
            msg_ids.reverse()  # Most recent first

            # Apply pagination
            start_idx = int(page_token) if page_token else 0
            end_idx = min(start_idx + limit, len(msg_ids))
            selected_ids = msg_ids[start_idx:end_idx]

            emails = []
            for msg_id in selected_ids:
                status, data = imap.fetch(msg_id, '(BODY.PEEK[HEADER])')
                if status != 'OK':
                    continue

                msg = email.message_from_bytes(data[0][1])
                emails.append({
                    "id": msg_id.decode(),
                    "from": msg.get("From", ""),
                    "to": msg.get("To", ""),
                    "subject": msg.get("Subject", ""),
                    "date": msg.get("Date", ""),
                    "snippet": ""  # Would need to fetch body for snippet
                })

            next_token = str(end_idx) if end_idx < len(msg_ids) else None

            return {
                "success": True,
                "emails": emails,
                "count": len(emails),
                "next_page_token": next_token
            }

        return await asyncio.get_event_loop().run_in_executor(None, _list)

    async def read_email(self, message_id: str) -> Dict[str, Any]:
        """Read email by ID."""
        def _read():
            imap = self._get_imap_connection()
            imap.select("INBOX", readonly=True)

            status, data = imap.fetch(message_id, '(RFC822)')
            if status != 'OK':
                return {"success": False, "error": "Failed to fetch message"}

            msg = email.message_from_bytes(data[0][1])

            # Extract body
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                        break
            else:
                body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')

            return {
                "success": True,
                "id": message_id,
                "from": msg.get("From", ""),
                "to": msg.get("To", ""),
                "cc": msg.get("Cc", ""),
                "subject": msg.get("Subject", ""),
                "date": msg.get("Date", ""),
                "body": body,
                "labels": []  # IMAP doesn't have labels like Gmail
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
        """Send email."""
        def _send():
            msg = MIMEMultipart() if html else MIMEText(body, 'plain')
            msg['From'] = self.username
            msg['To'] = ', '.join(to)
            msg['Subject'] = subject

            if cc:
                msg['Cc'] = ', '.join(cc)

            if html:
                msg.attach(MIMEText(body, 'html'))

            # Combine all recipients
            all_recipients = to + (cc or []) + (bcc or [])

            # Connect to SMTP server
            if self.use_ssl:
                smtp = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port)
            else:
                smtp = smtplib.SMTP(self.smtp_server, self.smtp_port)
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
        # First, read the original message to get headers
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
        """Delete email (move to Trash)."""
        def _delete():
            imap = self._get_imap_connection()
            imap.select("INBOX")
            imap.store(message_id, '+FLAGS', '\\Deleted')
            imap.expunge()
            return {"success": True}

        return await asyncio.get_event_loop().run_in_executor(None, _delete)

    async def search_emails(
        self,
        query: str,
        limit: int = 50
    ) -> Dict[str, Any]:
        """Search emails using IMAP SEARCH."""
        def _search():
            imap = self._get_imap_connection()
            imap.select("INBOX", readonly=True)

            # Simple search - could be enhanced with query parsing
            status, messages = imap.search(None, f'TEXT "{query}"')
            if status != 'OK':
                return {"success": False, "error": "Search failed"}

            msg_ids = messages[0].split()
            msg_ids.reverse()[:limit]  # Most recent first, limited

            emails = []
            for msg_id in msg_ids:
                status, data = imap.fetch(msg_id, '(BODY.PEEK[HEADER])')
                if status != 'OK':
                    continue

                msg = email.message_from_bytes(data[0][1])
                emails.append({
                    "id": msg_id.decode(),
                    "from": msg.get("From", ""),
                    "to": msg.get("To", ""),
                    "subject": msg.get("Subject", ""),
                    "date": msg.get("Date", ""),
                    "snippet": ""
                })

            return {
                "success": True,
                "emails": emails,
                "count": len(emails)
            }

        return await asyncio.get_event_loop().run_in_executor(None, _search)

    async def mark_read(self, message_id: str, read: bool = True) -> Dict[str, Any]:
        """Mark email as read/unread."""
        def _mark():
            imap = self._get_imap_connection()
            imap.select("INBOX")

            flag = '\\Seen' if read else '\\Seen'
            operation = '+FLAGS' if read else '-FLAGS'
            imap.store(message_id, operation, flag)

            return {"success": True}

        return await asyncio.get_event_loop().run_in_executor(None, _mark)

    async def get_folders(self) -> Dict[str, Any]:
        """Get list of available folders."""
        def _folders():
            imap = self._get_imap_connection()
            status, folders = imap.list()
            if status != 'OK':
                return {"success": False, "error": "Failed to list folders"}

            folder_list = []
            for folder in folders:
                # Parse folder name from IMAP response
                folder_str = folder.decode()
                parts = folder_str.split('"')
                if len(parts) >= 4:
                    folder_list.append(parts[3])

            return {
                "success": True,
                "folders": folder_list
            }

        return await asyncio.get_event_loop().run_in_executor(None, _folders)

    def close(self):
        """Close IMAP connection."""
        if self._imap:
            try:
                self._imap.logout()
            except:
                pass
            self._imap = None
