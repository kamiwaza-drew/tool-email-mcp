# Email MCP Tool

A secure email tool for Kamiwaza that lets you read, send, and manage emails through Gmail, Outlook, or any IMAP server.

## Quick Start

### 1. Install & Run

```bash
cd /home/kamiwaza/tools/tool-email-mcp
docker-compose up -d
curl http://localhost:8000/health  # Should return {"status": "healthy"}
```

### 2. Choose Your Email Provider

Pick one:

**Option A: IMAP (Simplest - Works with any email)**
```bash
# Set environment variables in docker-compose.yml or .env.imap
IMAP_USERNAME=your-email@gmail.com
IMAP_PASSWORD=your-app-password
IMAP_SERVER=imap.gmail.com
IMAP_PORT=993
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=465
```

**Option B: Gmail OAuth (More secure)**
- Get credentials from [Google Cloud Console](https://console.cloud.google.com/)
- Enable Gmail API
- Use `configure_email_provider` tool (see below)

**Option C: Outlook OAuth**
- Register app in [Azure Portal](https://portal.azure.com/)
- Set up Mail permissions
- Use `configure_email_provider` tool (see below)

### 3. Start Using

The tool is ready! See [Common Tasks](#common-tasks) below.

---

## Common Tasks

### Read Your Inbox

```json
{
  "tool": "list_emails",
  "arguments": {
    "folder": "INBOX",
    "limit": 10
  }
}
```

**Returns:** List of recent emails with subject, sender, date

---

### Read a Specific Email

```json
{
  "tool": "read_email",
  "arguments": {
    "message_id": "18c4f..."
  }
}
```

**Returns:** Full email content including body

---

### Send an Email

```json
{
  "tool": "send_email",
  "arguments": {
    "to": ["recipient@example.com"],
    "subject": "Hello",
    "body": "This is my message"
  }
}
```

**Optional:** Add `"cc": [...]`, `"bcc": [...]`, `"html": true`

---

### Reply to an Email

```json
{
  "tool": "reply_email",
  "arguments": {
    "message_id": "18c4f...",
    "body": "Thanks for your email!",
    "reply_all": false
  }
}
```

---

### Search Emails

**Gmail:**
```json
{
  "tool": "search_emails",
  "arguments": {
    "query": "from:boss@company.com subject:urgent",
    "limit": 20
  }
}
```

**IMAP (simple text search):**
```json
{
  "tool": "search_emails",
  "arguments": {
    "query": "urgent",
    "limit": 20
  }
}
```

---

## All Available Tools

| Tool | What it does |
|------|-------------|
| `list_emails` | List emails in a folder (INBOX, Sent, etc.) |
| `read_email` | Read full email content |
| `send_email` | Send a new email |
| `reply_email` | Reply to an email |
| `forward_email` | Forward an email to others |
| `search_emails` | Search for specific emails |
| `delete_email` | Move email to trash |
| `mark_email_read` | Mark email as read/unread |
| `get_folders` | List all folders/labels |
| `configure_email_provider` | Set up OAuth credentials |

---

## Setup Guides

### Gmail with App Password (Easiest)

1. **Enable 2-Step Verification** in your Google Account
2. **Create App Password:**
   - Go to [Google Account Security](https://myaccount.google.com/security)
   - Click "2-Step Verification" → "App passwords"
   - Generate password for "Mail"
3. **Configure:**
   ```bash
   IMAP_USERNAME=your-email@gmail.com
   IMAP_PASSWORD=<16-character-app-password>
   IMAP_SERVER=imap.gmail.com
   SMTP_SERVER=smtp.gmail.com
   ```

### Gmail with OAuth (More Secure)

1. **Create Google Cloud Project:**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create new project

2. **Enable Gmail API:**
   - APIs & Services → Library → Search "Gmail API" → Enable

3. **Create OAuth Client:**
   - APIs & Services → Credentials → Create OAuth client ID
   - Type: Web application or Desktop app
   - Download JSON with `client_id` and `client_secret`

4. **Get Access Token:**
   - Use [OAuth Playground](https://developers.google.com/oauthplayground/)
   - Scopes needed:
     - `https://www.googleapis.com/auth/gmail.readonly`
     - `https://www.googleapis.com/auth/gmail.send`
     - `https://www.googleapis.com/auth/gmail.modify`

5. **Configure via MCP:**
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

### Outlook OAuth

1. **Register Azure App:**
   - [Azure Portal](https://portal.azure.com/) → Azure Active Directory → App registrations
   - New registration → Name: "Email MCP Tool"
   - Redirect URI: `http://localhost:8000/oauth/callback`

2. **Add Permissions:**
   - API permissions → Add Microsoft Graph:
     - Mail.Read
     - Mail.ReadWrite
     - Mail.Send
   - Grant admin consent

3. **Create Secret:**
   - Certificates & secrets → New client secret → Copy value

4. **Get Token & Configure:**
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

### Other IMAP Servers

Works with any email provider that supports IMAP:

```bash
# Yahoo Mail
IMAP_SERVER=imap.mail.yahoo.com
SMTP_SERVER=smtp.mail.yahoo.com

# Outlook/Office365
IMAP_SERVER=outlook.office365.com
SMTP_SERVER=smtp.office365.com

# Custom domain
IMAP_SERVER=mail.yourdomain.com
SMTP_SERVER=mail.yourdomain.com
```

---

## Security Features

- ✅ **No password storage** in code (OAuth preferred)
- ✅ **Input validation** prevents injection attacks
- ✅ **Rate limiting** prevents abuse
- ✅ **SSL/TLS encryption** for all connections
- ✅ **Non-root container** for isolation
- ✅ **Audit logging** tracks all operations

---

## Troubleshooting

### "Authentication failed"

**IMAP:**
- Check username/password are correct
- For Gmail: Use app password, not account password
- Verify IMAP is enabled in email settings

**OAuth:**
- Token may be expired → Get new token
- Check client_id and client_secret are correct

### "Connection refused"

```bash
# Check if container is running
docker ps | grep email-mcp

# Check logs
docker-compose logs tool-email-mcp

# Restart
docker-compose restart
```

### Gmail "Less secure app" error

Gmail no longer allows less secure apps. Use either:
1. App passwords (with 2FA enabled)
2. OAuth 2.0

### Rate limit errors

You're making too many requests. Wait a few minutes and try again.

---

## Development

### Run Tests

```bash
pip install -r requirements.txt
pytest tests/ -v
```

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run server locally
python -m tool_email_mcp.server
```

---

## File Structure

```
tool-email-mcp/
├── src/tool_email_mcp/
│   ├── server.py              # FastMCP server with 10 tools
│   ├── security.py            # Input validation & security
│   ├── email_operations.py    # Email operation logic
│   ├── imap_provider.py       # IMAP/SMTP implementation
│   ├── gmail_provider.py      # Gmail OAuth implementation
│   └── outlook_provider.py    # Outlook OAuth implementation
├── docker-compose.yml         # Docker setup
├── Dockerfile                 # Container definition
├── requirements.txt           # Python dependencies
└── kamiwaza.json             # Tool metadata
```

---

## Support

- **Issues:** [GitHub Issues](https://github.com/kamiwaza-drew/tool-email-mcp/issues)
- **Security:** Report privately to security@kamiwaza.ai

---

## License

MIT License
