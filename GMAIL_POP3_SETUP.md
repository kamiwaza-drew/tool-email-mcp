# Gmail POP3 Setup Guide

## ✅ POP3 Support Added!

I've added full POP3 support for Gmail (and any other POP3 email service).

## 🔐 Gmail App Password Setup

**IMPORTANT:** Gmail requires an "App Password" if you have 2-Factor Authentication enabled.

### Step 1: Enable 2-Factor Authentication
1. Go to [Google Account Security](https://myaccount.google.com/security)
2. Under "Signing in to Google", click "2-Step Verification"
3. Follow the steps to enable 2FA

### Step 2: Generate App Password
1. Go to [App Passwords](https://myaccount.google.com/apppasswords)
2. Select app: **Mail**
3. Select device: **Other (Custom name)** → Enter "Email MCP Tool"
4. Click **Generate**
5. Copy the 16-character password (e.g., `abcd efgh ijkl mnop`)
6. **Save this password** - you'll need it!

### Step 3: Enable POP in Gmail
1. Go to Gmail → Settings (gear icon) → See all settings
2. Click "Forwarding and POP/IMAP" tab
3. Under "POP Download", select:
   - **Enable POP for all mail**
   - **Keep Gmail's copy in the Inbox** (recommended)
4. Click "Save Changes"

## ⚙️ Configuration

Edit `.env.gmail` and add your credentials:

```bash
# Your Gmail address
POP3_USERNAME=appiispanen@gmail.com

# Your App Password (16 characters from Step 2)
POP3_PASSWORD=abcd efgh ijkl mnop

# Gmail POP3 settings (already configured)
POP3_SERVER=pop.gmail.com
POP3_PORT=995
POP3_USE_SSL=true

# Gmail SMTP settings (already configured)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USE_STARTTLS=true
```

## 🧪 Test Your Setup

```bash
cd /home/kamiwaza/tools/tool-email-mcp

# Edit .env.gmail with your App Password first!
nano .env.gmail

# Run the test
python3 test_gmail_pop3.py
```

Expected output:
```
✅ Loaded credentials from .env.gmail
============================================================
Testing Gmail POP3 Connection
============================================================
Username: appiispanen@gmail.com
POP3 Server: pop.gmail.com:995 (SSL)
SMTP Server: smtp.gmail.com:587 (STARTTLS)

1. Testing: List Emails from INBOX
------------------------------------------------------------
✅ Success! Found 5 emails:

   ID: 123
   From: Sender <sender@example.com>
   Subject: Your Email Subject
   Date: Thu, 05 Feb 2026 12:00:00 +0000

...
```

## 📝 Using POP3 in Python

```python
import asyncio
import sys
sys.path.insert(0, 'src')

from tool_email_mcp.pop3_provider import POP3Provider

async def test():
    provider = POP3Provider(
        username="appiispanen@gmail.com",
        password="your_app_password_here",
        pop_server="pop.gmail.com",
        pop_port=995,
        smtp_server="smtp.gmail.com",
        smtp_port=587,
        use_ssl=True,
        use_starttls=True
    )

    # List emails
    emails = await provider.list_emails(limit=10)
    print(f"Found {emails['count']} emails")

    # Read first email
    if emails['emails']:
        email = await provider.read_email(emails['emails'][0]['id'])
        print(f"Subject: {email['subject']}")
        print(f"Body: {email['body'][:200]}")

    # Send an email
    await provider.send_email(
        to=["recipient@example.com"],
        subject="Test from POP3 Tool",
        body="This is a test email!"
    )

    provider.close()

asyncio.run(test())
```

## 🆚 POP3 vs IMAP

| Feature | POP3 | IMAP |
|---------|------|------|
| **Folders** | INBOX only | All folders |
| **Mark Read** | ❌ No | ✅ Yes |
| **Search** | Client-side only | Server-side |
| **Complexity** | Simple | Full-featured |
| **Use Case** | Basic email | Power users |

**Recommendation:**
- Use **POP3** for simple, single-inbox access
- Use **IMAP** if you need folders, labels, or mark-as-read

## ✅ Available Operations with POP3

- ✅ `list_emails()` - List emails from INBOX
- ✅ `read_email()` - Read full email content
- ✅ `send_email()` - Send new email via SMTP
- ✅ `reply_email()` - Reply to emails
- ✅ `forward_email()` - Forward emails
- ✅ `delete_email()` - Delete from server
- ✅ `search_emails()` - Client-side search
- ✅ `get_folders()` - Returns ["INBOX"]
- ❌ `mark_read()` - Not supported by POP3

## 🔧 Troubleshooting

### Authentication Failed
```
❌ Exception: -ERR [AUTH] Username and password not accepted
```
**Solutions:**
1. Verify App Password is correct (16 characters)
2. Make sure 2FA is enabled on your Google account
3. Check that you copied the password correctly (no spaces)

### POP Not Enabled
```
❌ Exception: -ERR [SYS/PERM] Your account is not enabled for POP access
```
**Solution:**
- Go to Gmail Settings → Forwarding and POP/IMAP
- Enable POP for all mail

### SSL/TLS Errors
```
❌ Exception: SSL: CERTIFICATE_VERIFY_FAILED
```
**Solution:**
- Update Python's SSL certificates: `pip install --upgrade certifi`

### Connection Timeout
```
❌ Exception: TimeoutError
```
**Solutions:**
1. Check your internet connection
2. Verify firewall isn't blocking port 995 (POP3) or 587 (SMTP)
3. Try from a different network

## 🎯 Quick Start Checklist

- [ ] Enable 2FA on Google Account
- [ ] Generate App Password
- [ ] Enable POP in Gmail Settings
- [ ] Update `.env.gmail` with username and app password
- [ ] Run `python3 test_gmail_pop3.py`
- [ ] Confirm ✅ Success messages

## 📚 Additional Resources

- [Gmail POP Settings](https://support.google.com/mail/answer/7126229)
- [App Passwords Help](https://support.google.com/accounts/answer/185833)
- [Gmail SMTP Settings](https://support.google.com/mail/answer/7126229)

## 🔒 Security Notes

- **Never commit** `.env.gmail` to git
- App Passwords are as sensitive as your regular password
- Revoke unused App Passwords from [App Passwords](https://myaccount.google.com/apppasswords)
- Consider using a dedicated email account for automation
