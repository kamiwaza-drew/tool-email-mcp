

# Email MCP Assistant Tool

A production-ready, security-hardened Email MCP tool for Kamiwaza that provides secure email operations through FastMCP/HTTP transport. Supports Gmail and Outlook with OAuth 2.0 authentication and federal-standard security controls.

## Features

### Email Providers
- **Gmail** - Google Workspace and personal Gmail accounts
- **Outlook** - Microsoft 365 and Outlook.com accounts

### Email Operations (10 tools)

**Configuration:**
- **configure_email_provider** - Set up OAuth credentials for Gmail or Outlook

**Reading:**
- **list_emails** - List emails in folders with pagination
- **read_email** - Read full email content by ID
- **search_emails** - Search emails with provider-specific query syntax
- **get_folders** - List available folders/labels

**Writing:**
- **send_email** - Send new emails with HTML support
- **reply_email** - Reply to emails (single or all)
- **forward_email** - Forward emails with optional comments

**Management:**
- **delete_email** - Move emails to trash
- **mark_email_read** - Mark emails as read/unread

## Federal-Standard Security Features

### Authentication
- ✅ **OAuth 2.0 Only** - No password storage
- ✅ **Encrypted Credentials** - Never logged or persisted
- ✅ **Token Refresh** - Automatic token renewal (Gmail)
- ✅ **Scope Minimization** - Request only necessary permissions

### Input Validation
- ✅ **Email Address Validation** - RFC 5322 compliant
- ✅ **Subject Header Injection Prevention** - Blocks newline attacks
- ✅ **XSS Protection** - Scans for script injection in body
- ✅ **Query Injection Prevention** - Validates search queries
- ✅ **Size Limits** - Enforces maximum lengths (DoS prevention)

### Anti-Abuse Controls
- ✅ **Recipient Limits** - Max 100 recipients (prevents mass mailing)
- ✅ **Rate Limiting** - Provider-enforced API limits
- ✅ **Content Scanning** - Blocks dangerous patterns
- ✅ **Pagination Enforcement** - Limits page sizes

### Data Protection
- ✅ **No Data Persistence** - Stateless operation
- ✅ **Sanitized Errors** - No sensitive data in error messages
- ✅ **HTML Sanitization** - Removes dangerous HTML elements
- ✅ **Audit Logging** - All operations logged

### Container Security
- ✅ **Non-Root User** - Runs as `appuser`
- ✅ **Resource Limits** - 1 CPU, 1G memory
- ✅ **Health Checks** - Automated monitoring
- ✅ **Minimal Base Image** - Python 3.11 slim

## Installation

### Prerequisites
- Docker and Docker Compose
- OAuth 2.0 credentials (see Setup sections below)
- Python 3.11+ (for local development)

### Build and Run

```bash
# Build the Docker image
cd tools/tool-email-mcp
docker-compose build

# Start the service
docker-compose up -d

# Check health
curl http://localhost:8000/health
```

## OAuth 2.0 Setup

### Gmail Setup

1. **Create Google Cloud Project**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select existing

2. **Enable Gmail API**
   - Navigate to "APIs & Services" > "Library"
   - Search for "Gmail API" and enable it

3. **Create OAuth Credentials**
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth client ID"
   - Application type: "Desktop app" or "Web application"
   - Add authorized redirect URIs (e.g., `http://localhost:8080/callback`)

4. **Download Credentials**
   - Download the JSON file with client_id and client_secret

5. **Get Access Token**
   ```bash
   # Use OAuth playground or implement OAuth flow
   # https://developers.google.com/oauthplayground/

   # Required scopes:
   # - https://www.googleapis.com/auth/gmail.readonly
   # - https://www.googleapis.com/auth/gmail.send
   # - https://www.googleapis.com/auth/gmail.modify
   ```

6. **Configure Provider**
   ```json
   {
     "tool": "configure_email_provider",
     "arguments": {
       "provider": "gmail",
       "credentials": {
         "token": "ya29.a0...",
         "refresh_token": "1//...",
         "client_id": "123...apps.googleusercontent.com",
         "client_secret": "GOCSPX-..."
       }
     }
   }
   ```

### Outlook Setup

1. **Register Azure AD Application**
   - Go to [Azure Portal](https://portal.azure.com/)
   - Navigate to "Azure Active Directory" > "App registrations"
   - Click "New registration"
   - Name: "Email MCP Tool"
   - Supported account types: Choose based on your needs
   - Redirect URI: `http://localhost:8080/callback` (Web)

2. **Configure API Permissions**
   - Go to "API permissions"
   - Add permissions:
     - Microsoft Graph > Delegated permissions
     - Mail.Read
     - Mail.ReadWrite
     - Mail.Send
   - Grant admin consent

3. **Create Client Secret**
   - Go to "Certificates & secrets"
   - Click "New client secret"
   - Save the secret value (shown once)

4. **Get Access Token**
   ```python
   import msal

   client_id = "your_client_id"
   client_secret = "your_client_secret"
   tenant_id = "your_tenant_id"

   authority = f"https://login.microsoftonline.com/{tenant_id}"
   scopes = ["https://graph.microsoft.com/Mail.Read",
             "https://graph.microsoft.com/Mail.ReadWrite",
             "https://graph.microsoft.com/Mail.Send"]

   app = msal.ConfidentialClientApplication(
       client_id,
       authority=authority,
       client_credential=client_secret
   )

   # Interactive flow for delegated permissions
   result = app.acquire_token_interactive(scopes=scopes)
   access_token = result['access_token']
   ```

5. **Configure Provider**
   ```json
   {
     "tool": "configure_email_provider",
     "arguments": {
       "provider": "outlook",
       "credentials": {
         "access_token": "eyJ0eXAi..."
       }
     }
   }
   ```

## Usage Examples

### List Inbox Emails

```json
{
  "tool": "list_emails",
  "arguments": {
    "folder": "INBOX",
    "limit": 10
  }
}
```

Response:
```json
{
  "success": true,
  "emails": [
    {
      "id": "18c4f...",
      "from": "sender@example.com",
      "to": "me@example.com",
      "subject": "Meeting Tomorrow",
      "date": "2024-01-15T10:30:00Z",
      "snippet": "Hi, just confirming our meeting..."
    }
  ],
  "count": 10,
  "next_page_token": "CAES..."
}
```

### Read Email

```json
{
  "tool": "read_email",
  "arguments": {
    "message_id": "18c4f..."
  }
}
```

Response:
```json
{
  "success": true,
  "id": "18c4f...",
  "from": "sender@example.com",
  "to": "me@example.com",
  "cc": "",
  "subject": "Meeting Tomorrow",
  "date": "2024-01-15T10:30:00Z",
  "body": "Hi,\n\nJust confirming our meeting tomorrow at 2pm...",
  "labels": ["INBOX", "UNREAD"]
}
```

### Send Email

```json
{
  "tool": "send_email",
  "arguments": {
    "to": ["recipient@example.com"],
    "subject": "Project Update",
    "body": "Hi team,\n\nHere's the latest update on the project...",
    "cc": ["manager@example.com"],
    "html": false
  }
}
```

Response:
```json
{
  "success": true,
  "message_id": "18c5a...",
  "thread_id": "18c5a..."
}
```

### Search Emails

**Gmail syntax:**
```json
{
  "tool": "search_emails",
  "arguments": {
    "query": "from:boss@example.com subject:urgent after:2024/01/01",
    "limit": 20
  }
}
```

**Outlook syntax:**
```json
{
  "tool": "search_emails",
  "arguments": {
    "query": "from:boss@example.com AND subject:urgent",
    "limit": 20
  }
}
```

### Reply to Email

```json
{
  "tool": "reply_email",
  "arguments": {
    "message_id": "18c4f...",
    "body": "Thanks for the update. I'll review and get back to you.",
    "reply_all": false,
    "html": false
  }
}
```

### Forward Email

```json
{
  "tool": "forward_email",
  "arguments": {
    "message_id": "18c4f...",
    "to": ["colleague@example.com"],
    "comment": "FYI - This might be relevant to your project."
  }
}
```

### Delete Email

```json
{
  "tool": "delete_email",
  "arguments": {
    "message_id": "18c4f..."
  }
}
```

### Mark as Read

```json
{
  "tool": "mark_email_read",
  "arguments": {
    "message_id": "18c4f...",
    "read": true
  }
}
```

## Security Best Practices

### Credential Management
1. **Never commit credentials** to version control
2. **Use environment variables** for OAuth secrets
3. **Rotate tokens regularly** (recommended: every 90 days)
4. **Revoke unused tokens** in provider admin console
5. **Use dedicated service accounts** for automation

### Operational Security
1. **Monitor API usage** for anomalies
2. **Enable audit logging** in provider console
3. **Set up alerts** for suspicious activity
4. **Review permissions** periodically
5. **Limit tool access** to authorized users only

### Compliance Considerations
- **HIPAA**: Ensure Business Associate Agreement (BAA) with provider
- **GDPR**: Document data processing, implement data retention policies
- **FISMA**: Use FedRAMP authorized cloud services (Google Workspace Gov, Microsoft 365 GCC)
- **ITAR**: Consider on-premises deployment for controlled data

## Architecture

```
tool-email-mcp/
├── src/tool_email_mcp/
│   ├── __init__.py              # Package initialization
│   ├── server.py                # FastMCP server with 10 tools
│   ├── security.py              # SecurityManager with federal controls
│   ├── email_operations.py      # EmailOperations manager
│   └── providers.py             # Gmail & Outlook providers
├── tests/
│   ├── test_security.py         # Security validation tests
│   ├── test_providers.py        # Provider tests
│   └── test_server.py           # Server and tool tests
├── Dockerfile                   # Container definition
├── docker-compose.yml           # Local development
├── requirements.txt             # Python dependencies
├── kamiwaza.json               # Tool metadata
└── README.md                   # This file
```

## Security Guarantees

1. ✅ **No Password Storage** - OAuth 2.0 only
2. ✅ **Input Validation** - All user input sanitized
3. ✅ **XSS Prevention** - HTML content sanitized
4. ✅ **Injection Prevention** - Query and header validation
5. ✅ **Rate Limiting** - Provider-enforced limits
6. ✅ **Audit Logging** - All operations logged
7. ✅ **Non-Root Container** - Runs as `appuser`
8. ✅ **Minimal Permissions** - OAuth scopes minimized

## Limitations

1. **OAuth Setup Required** - Manual credential configuration needed
2. **No IMAP/SMTP** - API-only access (more secure)
3. **Provider Limits** - Subject to Gmail/Outlook API quotas
4. **No Attachments** - File operations not supported in v1.0
5. **No Drafts** - Draft management not implemented
6. **Stateless** - No session persistence between restarts

## Troubleshooting

### Authentication Errors

**Gmail "invalid_grant":**
- Token expired - re-authenticate to get new token
- Refresh token revoked - generate new OAuth credentials

**Outlook "invalid_client":**
- Client secret expired - create new secret in Azure Portal
- App permissions changed - re-consent to permissions

### API Errors

**Gmail "403 rateLimitExceeded":**
- Hitting Gmail API quota - wait or request quota increase

**Outlook "429 Too Many Requests":**
- Throttled by Microsoft Graph - implement exponential backoff

### Container Issues

```bash
# Check container logs
docker-compose logs tool-email-mcp

# Verify health
curl http://localhost:8000/health

# Restart service
docker-compose restart tool-email-mcp
```

## Testing

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src/tool_email_mcp --cov-report=html
```

## Contributing

Contributions welcome! Please ensure:
1. All security validations are preserved
2. Tests added for new features
3. Documentation updated
4. No credentials committed

## License

MIT License - See LICENSE file for details

## Support

For issues and questions:
- GitHub Issues: [kamiwaza-extensions](https://github.com/kamiwazaai/kamiwaza-extensions)
- Documentation: [Kamiwaza Docs](https://docs.kamiwaza.ai)
- Security Issues: security@kamiwaza.ai (private disclosure)

## References

- [Gmail API Documentation](https://developers.google.com/gmail/api)
- [Microsoft Graph Mail API](https://learn.microsoft.com/en-us/graph/api/resources/mail-api-overview)
- [OAuth 2.0 Security Best Practices](https://tools.ietf.org/html/rfc8252)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)
