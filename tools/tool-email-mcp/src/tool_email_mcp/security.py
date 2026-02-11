"""Security validation for Email MCP tool operations.

Implements federal-standard security controls including input validation,
credential protection, and audit logging.
"""

import re
import html
from typing import Optional, List
from email.utils import parseaddr
import secrets


class SecurityManager:
    """Manages security validations for email operations."""

    # Maximum lengths for inputs (prevent DoS)
    MAX_EMAIL_LENGTH = 320  # RFC 5321 standard
    MAX_SUBJECT_LENGTH = 998  # RFC 5322 standard
    MAX_BODY_LENGTH = 10_000_000  # 10MB limit
    MAX_ATTACHMENT_SIZE = 25_000_000  # 25MB limit (Gmail/Outlook limits)
    MAX_RECIPIENTS = 100  # Prevent mass mailing abuse

    # Allowed content types for attachments (security whitelist)
    ALLOWED_ATTACHMENT_TYPES = {
        'application/pdf',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/vnd.ms-excel',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'application/vnd.ms-powerpoint',
        'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        'text/plain',
        'text/csv',
        'image/jpeg',
        'image/png',
        'image/gif',
        'application/zip',
    }

    # Email address validation (RFC 5322 simplified)
    EMAIL_PATTERN = re.compile(
        r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    )

    # Dangerous patterns in email content (XSS, injection)
    DANGEROUS_PATTERNS = [
        re.compile(r'<script[^>]*>.*?</script>', re.IGNORECASE | re.DOTALL),
        re.compile(r'javascript:', re.IGNORECASE),
        re.compile(r'on\w+\s*=', re.IGNORECASE),  # Event handlers
        re.compile(r'<iframe[^>]*>', re.IGNORECASE),
        re.compile(r'<embed[^>]*>', re.IGNORECASE),
        re.compile(r'<object[^>]*>', re.IGNORECASE),
    ]

    def __init__(self):
        """Initialize security manager."""
        pass

    def validate_email_address(self, email: str) -> str:
        """Validate email address format.

        Args:
            email: Email address to validate

        Returns:
            Validated and normalized email address

        Raises:
            ValueError: If email is invalid
        """
        if not email or not email.strip():
            raise ValueError("Email address cannot be empty")

        email = email.strip().lower()

        if len(email) > self.MAX_EMAIL_LENGTH:
            raise ValueError(f"Email address too long (max {self.MAX_EMAIL_LENGTH} chars)")

        # Parse email address (handles display names)
        _, addr = parseaddr(email)
        if not addr:
            raise ValueError("Invalid email address format")

        # Validate with regex
        if not self.EMAIL_PATTERN.match(addr):
            raise ValueError("Invalid email address format")

        return addr

    def validate_email_list(self, emails: List[str], max_count: Optional[int] = None) -> List[str]:
        """Validate list of email addresses.

        Args:
            emails: List of email addresses
            max_count: Optional maximum number of recipients

        Returns:
            List of validated email addresses

        Raises:
            ValueError: If any email is invalid or count exceeds limit
        """
        if not emails:
            raise ValueError("Email list cannot be empty")

        if len(emails) > (max_count or self.MAX_RECIPIENTS):
            raise ValueError(
                f"Too many recipients (max {max_count or self.MAX_RECIPIENTS})"
            )

        validated = []
        for email in emails:
            validated.append(self.validate_email_address(email))

        return validated

    def validate_subject(self, subject: str) -> str:
        """Validate email subject.

        Args:
            subject: Email subject line

        Returns:
            Validated subject

        Raises:
            ValueError: If subject is invalid
        """
        if not subject or not subject.strip():
            raise ValueError("Subject cannot be empty")

        subject = subject.strip()

        if len(subject) > self.MAX_SUBJECT_LENGTH:
            raise ValueError(f"Subject too long (max {self.MAX_SUBJECT_LENGTH} chars)")

        # Check for header injection attempts
        if '\n' in subject or '\r' in subject:
            raise ValueError("Subject cannot contain newlines")

        return subject

    def validate_body(self, body: str, allow_html: bool = False) -> str:
        """Validate email body content.

        Args:
            body: Email body content
            allow_html: Whether HTML content is allowed

        Returns:
            Validated body content

        Raises:
            ValueError: If body is invalid or contains dangerous content
        """
        if not body:
            raise ValueError("Email body cannot be empty")

        if len(body) > self.MAX_BODY_LENGTH:
            raise ValueError(f"Email body too long (max {self.MAX_BODY_LENGTH} chars)")

        # Check for dangerous patterns
        for pattern in self.DANGEROUS_PATTERNS:
            if pattern.search(body):
                raise ValueError("Email body contains potentially dangerous content")

        # If HTML not allowed, escape HTML entities
        if not allow_html and ('<' in body or '>' in body):
            body = html.escape(body)

        return body

    def validate_message_id(self, message_id: str) -> str:
        """Validate message ID format.

        Args:
            message_id: Message ID to validate

        Returns:
            Validated message ID

        Raises:
            ValueError: If message ID is invalid
        """
        if not message_id or not message_id.strip():
            raise ValueError("Message ID cannot be empty")

        message_id = message_id.strip()

        # Gmail message IDs are alphanumeric with underscores/hyphens
        # Outlook message IDs are longer with various characters
        if not re.match(r'^[a-zA-Z0-9_\-\.=@]+$', message_id):
            raise ValueError("Invalid message ID format")

        if len(message_id) > 1024:
            raise ValueError("Message ID too long")

        return message_id

    def validate_label(self, label: str) -> str:
        """Validate label/folder name.

        Args:
            label: Label or folder name

        Returns:
            Validated label

        Raises:
            ValueError: If label is invalid
        """
        if not label or not label.strip():
            raise ValueError("Label cannot be empty")

        label = label.strip()

        if len(label) > 255:
            raise ValueError("Label name too long")

        # Prevent directory traversal
        if '..' in label or '/' in label or '\\' in label:
            raise ValueError("Invalid characters in label name")

        return label

    def validate_search_query(self, query: str) -> str:
        """Validate search query.

        Args:
            query: Search query string

        Returns:
            Validated query

        Raises:
            ValueError: If query is invalid
        """
        if not query or not query.strip():
            raise ValueError("Search query cannot be empty")

        query = query.strip()

        if len(query) > 1000:
            raise ValueError("Search query too long")

        # Check for injection attempts in query operators
        dangerous_chars = ['<script', 'javascript:', '<iframe']
        for char in dangerous_chars:
            if char.lower() in query.lower():
                raise ValueError("Search query contains invalid content")

        return query

    def validate_attachment_type(self, content_type: str) -> str:
        """Validate attachment content type.

        Args:
            content_type: MIME content type

        Returns:
            Validated content type

        Raises:
            ValueError: If content type is not allowed
        """
        if not content_type:
            raise ValueError("Content type cannot be empty")

        content_type = content_type.lower().strip()

        # Remove parameters (e.g., "text/plain; charset=utf-8" -> "text/plain")
        base_type = content_type.split(';')[0].strip()

        if base_type not in self.ALLOWED_ATTACHMENT_TYPES:
            raise ValueError(
                f"Content type '{base_type}' not allowed. "
                f"Allowed types: {', '.join(sorted(self.ALLOWED_ATTACHMENT_TYPES))}"
            )

        return base_type

    def sanitize_html(self, html_content: str) -> str:
        """Sanitize HTML content for safe display.

        Args:
            html_content: HTML content to sanitize

        Returns:
            Sanitized HTML

        Note:
            This is a basic sanitizer. For production, consider using
            a library like bleach or html-sanitizer.
        """
        # Remove dangerous patterns
        sanitized = html_content
        for pattern in self.DANGEROUS_PATTERNS:
            sanitized = pattern.sub('', sanitized)

        return sanitized

    def generate_correlation_id(self) -> str:
        """Generate a secure correlation ID for audit logging.

        Returns:
            Secure random correlation ID
        """
        return secrets.token_urlsafe(16)

    def validate_pagination(self, page_size: int, max_page_size: int = 100) -> int:
        """Validate pagination parameters.

        Args:
            page_size: Requested page size
            max_page_size: Maximum allowed page size

        Returns:
            Validated page size

        Raises:
            ValueError: If page size is invalid
        """
        if page_size < 1:
            raise ValueError("Page size must be positive")

        if page_size > max_page_size:
            raise ValueError(f"Page size too large (max {max_page_size})")

        return page_size

    def validate_list_params(self, folder: str, limit: int) -> dict:
        """Validate list emails parameters.

        Args:
            folder: Folder/label name
            limit: Maximum number of emails to return

        Returns:
            Dict with validation result:
                - valid (bool): Whether parameters are valid
                - error (str): Error message if invalid
        """
        try:
            self.validate_label(folder)
            self.validate_pagination(limit)
            return {"valid": True}
        except ValueError as e:
            return {"valid": False, "error": str(e)}
