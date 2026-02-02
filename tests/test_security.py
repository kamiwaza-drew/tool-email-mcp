"""Tests for security validation."""

import pytest
from tool_email_mcp.security import SecurityManager


@pytest.fixture
def security_manager():
    """Create security manager instance."""
    return SecurityManager()


class TestEmailValidation:
    """Tests for email address validation."""

    def test_valid_email(self, security_manager):
        """Validate correct email address."""
        result = security_manager.validate_email_address("user@example.com")
        assert result == "user@example.com"

    def test_email_normalized(self, security_manager):
        """Email addresses are normalized to lowercase."""
        result = security_manager.validate_email_address("User@Example.COM")
        assert result == "user@example.com"

    def test_email_with_display_name(self, security_manager):
        """Parse email from display name format."""
        result = security_manager.validate_email_address("John Doe <john@example.com>")
        assert result == "john@example.com"

    def test_reject_empty_email(self, security_manager):
        """Reject empty email address."""
        with pytest.raises(ValueError, match="cannot be empty"):
            security_manager.validate_email_address("")

    def test_reject_invalid_format(self, security_manager):
        """Reject invalid email format."""
        with pytest.raises(ValueError, match="Invalid email address"):
            security_manager.validate_email_address("not-an-email")

    def test_reject_too_long(self, security_manager):
        """Reject email address that's too long."""
        long_email = "a" * 300 + "@example.com"
        with pytest.raises(ValueError, match="too long"):
            security_manager.validate_email_address(long_email)

    def test_validate_email_list(self, security_manager):
        """Validate list of email addresses."""
        emails = ["user1@example.com", "user2@example.com"]
        result = security_manager.validate_email_list(emails)
        assert len(result) == 2
        assert "user1@example.com" in result

    def test_reject_empty_list(self, security_manager):
        """Reject empty email list."""
        with pytest.raises(ValueError, match="cannot be empty"):
            security_manager.validate_email_list([])

    def test_reject_too_many_recipients(self, security_manager):
        """Reject too many recipients."""
        emails = [f"user{i}@example.com" for i in range(101)]
        with pytest.raises(ValueError, match="Too many recipients"):
            security_manager.validate_email_list(emails)


class TestSubjectValidation:
    """Tests for subject validation."""

    def test_valid_subject(self, security_manager):
        """Validate normal subject."""
        result = security_manager.validate_subject("Meeting Tomorrow")
        assert result == "Meeting Tomorrow"

    def test_reject_empty_subject(self, security_manager):
        """Reject empty subject."""
        with pytest.raises(ValueError, match="cannot be empty"):
            security_manager.validate_subject("")

    def test_reject_newlines(self, security_manager):
        """Reject subject with newlines (header injection)."""
        with pytest.raises(ValueError, match="cannot contain newlines"):
            security_manager.validate_subject("Subject\nBcc: attacker@evil.com")

    def test_reject_too_long(self, security_manager):
        """Reject subject that's too long."""
        long_subject = "a" * 1000
        with pytest.raises(ValueError, match="too long"):
            security_manager.validate_subject(long_subject)


class TestBodyValidation:
    """Tests for body content validation."""

    def test_valid_plain_text(self, security_manager):
        """Validate plain text body."""
        body = "This is a normal email message."
        result = security_manager.validate_body(body)
        assert result == body

    def test_reject_empty_body(self, security_manager):
        """Reject empty body."""
        with pytest.raises(ValueError, match="cannot be empty"):
            security_manager.validate_body("")

    def test_reject_too_long(self, security_manager):
        """Reject body that's too long."""
        long_body = "a" * 11_000_000
        with pytest.raises(ValueError, match="too long"):
            security_manager.validate_body(long_body)

    def test_detect_script_tag(self, security_manager):
        """Detect and reject script tags."""
        body = "Hello <script>alert('xss')</script> world"
        with pytest.raises(ValueError, match="dangerous content"):
            security_manager.validate_body(body)

    def test_detect_javascript_protocol(self, security_manager):
        """Detect javascript: protocol."""
        body = '<a href="javascript:alert(1)">Click</a>'
        with pytest.raises(ValueError, match="dangerous content"):
            security_manager.validate_body(body)

    def test_detect_event_handlers(self, security_manager):
        """Detect event handler attributes."""
        body = '<div onclick="alert(1)">Click me</div>'
        with pytest.raises(ValueError, match="dangerous content"):
            security_manager.validate_body(body)

    def test_detect_iframe(self, security_manager):
        """Detect iframe tags."""
        body = '<iframe src="http://evil.com"></iframe>'
        with pytest.raises(ValueError, match="dangerous content"):
            security_manager.validate_body(body)

    def test_escape_html_when_not_allowed(self, security_manager):
        """Escape HTML when HTML not allowed."""
        body = "<b>Bold text</b>"
        result = security_manager.validate_body(body, allow_html=False)
        assert "&lt;" in result and "&gt;" in result

    def test_allow_safe_html(self, security_manager):
        """Allow safe HTML when enabled."""
        body = "<p>This is <b>bold</b> text.</p>"
        result = security_manager.validate_body(body, allow_html=True)
        assert result == body


class TestMessageIdValidation:
    """Tests for message ID validation."""

    def test_valid_message_id(self, security_manager):
        """Validate normal message ID."""
        msg_id = "18c4f12a3b5d6e7f"
        result = security_manager.validate_message_id(msg_id)
        assert result == msg_id

    def test_reject_empty_message_id(self, security_manager):
        """Reject empty message ID."""
        with pytest.raises(ValueError, match="cannot be empty"):
            security_manager.validate_message_id("")

    def test_reject_invalid_characters(self, security_manager):
        """Reject message ID with invalid characters."""
        with pytest.raises(ValueError, match="Invalid message ID"):
            security_manager.validate_message_id("abc/../../../etc/passwd")

    def test_reject_too_long(self, security_manager):
        """Reject message ID that's too long."""
        long_id = "a" * 1025
        with pytest.raises(ValueError, match="too long"):
            security_manager.validate_message_id(long_id)


class TestSearchQueryValidation:
    """Tests for search query validation."""

    def test_valid_query(self, security_manager):
        """Validate normal search query."""
        query = "from:user@example.com subject:meeting"
        result = security_manager.validate_search_query(query)
        assert result == query

    def test_reject_empty_query(self, security_manager):
        """Reject empty query."""
        with pytest.raises(ValueError, match="cannot be empty"):
            security_manager.validate_search_query("")

    def test_reject_too_long(self, security_manager):
        """Reject query that's too long."""
        long_query = "a" * 1001
        with pytest.raises(ValueError, match="too long"):
            security_manager.validate_search_query(long_query)

    def test_reject_script_injection(self, security_manager):
        """Reject query with script injection."""
        with pytest.raises(ValueError, match="invalid content"):
            security_manager.validate_search_query("<script>alert(1)</script>")


class TestPaginationValidation:
    """Tests for pagination validation."""

    def test_valid_page_size(self, security_manager):
        """Validate normal page size."""
        result = security_manager.validate_pagination(50)
        assert result == 50

    def test_reject_negative(self, security_manager):
        """Reject negative page size."""
        with pytest.raises(ValueError, match="must be positive"):
            security_manager.validate_pagination(-1)

    def test_reject_too_large(self, security_manager):
        """Reject page size that's too large."""
        with pytest.raises(ValueError, match="too large"):
            security_manager.validate_pagination(200, max_page_size=100)


class TestAttachmentValidation:
    """Tests for attachment type validation."""

    def test_valid_pdf(self, security_manager):
        """Allow PDF attachments."""
        result = security_manager.validate_attachment_type("application/pdf")
        assert result == "application/pdf"

    def test_valid_with_charset(self, security_manager):
        """Handle content type with charset parameter."""
        result = security_manager.validate_attachment_type("text/plain; charset=utf-8")
        assert result == "text/plain"

    def test_reject_executable(self, security_manager):
        """Reject executable file types."""
        with pytest.raises(ValueError, match="not allowed"):
            security_manager.validate_attachment_type("application/x-msdownload")

    def test_reject_empty_type(self, security_manager):
        """Reject empty content type."""
        with pytest.raises(ValueError, match="cannot be empty"):
            security_manager.validate_attachment_type("")
