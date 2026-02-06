# Gmail Setup Guide for Kamiwaza Email MCP Tool

This guide will walk you through setting up Gmail OAuth authentication for the Email MCP tool.

## Quick Overview

1. Create a Google Cloud project and enable Gmail API
2. Set up OAuth credentials
3. Run helper script to get tokens
4. Configure the tool in Kamiwaza

**Time required:** ~10 minutes

---

## Step-by-Step Instructions

### Step 1: Google Cloud Console Setup (5 minutes)

#### 1.1 Create a Project

1. Go to **https://console.cloud.google.com/**
2. Click the project dropdown at the top
3. Click **"New Project"**
4. Enter project name: `Kamiwaza Email Tool`
5. Click **"Create"**
6. Wait for project creation (takes ~30 seconds)

#### 1.2 Enable Gmail API

1. In the left sidebar, go to: **APIs & Services** → **Library**
2. Search for: `Gmail API`
3. Click on **Gmail API**
4. Click **"Enable"**
5. Wait for API to enable (~10 seconds)

#### 1.3 Configure OAuth Consent Screen

1. Go to: **APIs & Services** → **OAuth consent screen**
2. Select **"External"** (unless you have Google Workspace, then choose "Internal")
3. Click **"Create"**

4. **OAuth consent screen page:**
   - App name: `Kamiwaza Email Tool`
   - User support email: Select your email from dropdown
   - Developer contact email: Enter your email
   - Click **"Save and Continue"**

5. **Scopes page:**
   - Click **"Add or Remove Scopes"**
   - In the filter box, search for: `gmail`
   - Select these three scopes:
     - ✅ `.../auth/gmail.readonly` - View your email messages and settings
     - ✅ `.../auth/gmail.send` - Send email on your behalf
     - ✅ `.../auth/gmail.modify` - View and modify but not delete your email
   - Click **"Update"**
   - Click **"Save and Continue"**

6. **Test users page:**
   - Click **"Add Users"**
   - Enter your Gmail address
   - Click **"Add"**
   - Click **"Save and Continue"**

7. **Summary page:**
   - Review and click **"Back to Dashboard"**

#### 1.4 Create OAuth Credentials

1. Go to: **APIs & Services** → **Credentials**
2. Click **"Create Credentials"** at the top
3. Select **"OAuth client ID"**
4. Application type: Select **"Desktop app"**
5. Name: `Kamiwaza Email Desktop`
6. Click **"Create"**
7. You'll see a dialog with Client ID and Client Secret
8. Click **"Download JSON"** (download icon)
9. Save the file as `gmail_credentials.json` in the `tool-email-mcp` directory

---

### Step 2: Get OAuth Tokens (2 minutes)

Now we'll use a helper script to get your access tokens.

#### 2.1 Install Dependencies

```bash
cd /home/kamiwaza/tools/tool-email-mcp

# Install helper script dependencies
pip install -r setup_requirements.txt
```

#### 2.2 Run Token Generator

```bash
# Make sure gmail_credentials.json is in this directory
ls gmail_credentials.json  # Should show the file

# Run the token generator
python get_gmail_token.py
```

**What happens next:**
1. Your browser will open automatically
2. You'll be asked to sign in to your Google account
3. Google will show: "This app isn't verified" - Click **"Advanced"** → **"Go to Kamiwaza Email Tool (unsafe)"**
4. Review the permissions and click **"Allow"**
5. You'll see: "The authentication flow has completed"
6. Go back to your terminal

#### 2.3 Copy Your Credentials

The script will output something like:

```json
{
  "tool": "configure_email_provider",
  "arguments": {
    "provider": "gmail",
    "credentials": {
      "token": "ya29.a0Ae4lvC...",
      "refresh_token": "1//0gQ...",
      "client_id": "123...apps.googleusercontent.com",
      "client_secret": "GOCSPX-..."
    }
  }
}
```

**Save this JSON!** You'll need it to configure the tool.

---

### Step 3: Configure the Tool in Kamiwaza (3 minutes)

#### Option A: Using the Kamiwaza UI

1. Open Kamiwaza at **https://34.56.112.22**
2. Go to **Tool Shed**
3. Find **tool-email-mcp** and click **Deploy**
4. The tool will start running
5. To configure it, you'll need to make an API call (see Option B)

#### Option B: Configure via API/MCP

Once the tool is deployed, you can configure it by calling the MCP endpoint:

```bash
# Get the tool's endpoint from Kamiwaza
# Example: http://localhost:PORT/mcp

curl -X POST http://TOOL_ENDPOINT/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "tool": "configure_email_provider",
    "arguments": {
      "provider": "gmail",
      "credentials": {
        "token": "YOUR_TOKEN_HERE",
        "refresh_token": "YOUR_REFRESH_TOKEN_HERE",
        "client_id": "YOUR_CLIENT_ID_HERE",
        "client_secret": "YOUR_CLIENT_SECRET_HERE"
      }
    }
  }'
```

Replace the credential values with those from Step 2.3.

---

### Step 4: Test the Setup

Try listing your emails:

```bash
curl -X POST http://TOOL_ENDPOINT/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "tool": "list_emails",
    "arguments": {
      "folder": "INBOX",
      "limit": 5
    }
  }'
```

You should see a JSON response with your latest emails!

---

## Troubleshooting

### "gmail_credentials.json not found"

**Solution:** Make sure you downloaded the credentials file from Google Cloud Console and saved it as `gmail_credentials.json` in the `tool-email-mcp` directory.

### "This app isn't verified" warning

**This is normal!** Your app is in development mode. Click:
1. **"Advanced"**
2. **"Go to Kamiwaza Email Tool (unsafe)"**

To remove this warning permanently, you would need to verify your app with Google (requires domain verification), but it's not necessary for personal use.

### "Access blocked: This app's request is invalid"

**Solution:** Check that you added your Gmail address as a test user in Step 1.3.6.

### "invalid_grant" error

**Solutions:**
- Your token has expired - Run `python get_gmail_token.py` again
- Your refresh token was revoked - Delete `gmail_token.json` and run the script again

### Browser doesn't open

**Solution:** The script will print a URL. Copy it and paste into your browser manually.

---

## Security Notes

### ✅ DO:
- Keep your `gmail_credentials.json` secure
- Never commit credentials to git
- Use a dedicated Google account for automation if possible
- Revoke access when no longer needed

### ❌ DON'T:
- Share your client_secret with anyone
- Use your main personal Gmail for production automation
- Leave old tokens active indefinitely

### Revoking Access

If you need to revoke access:

1. Go to: **https://myaccount.google.com/permissions**
2. Find **"Kamiwaza Email Tool"**
3. Click **"Remove Access"**

---

## What These Credentials Do

The OAuth credentials allow the tool to:

- ✅ **Read your emails** - View messages and metadata
- ✅ **Send emails** - Send messages on your behalf
- ✅ **Modify emails** - Mark as read, delete (move to trash), create labels

They **CANNOT**:
- ❌ Change your password
- ❌ Access other Google services (Drive, Calendar, etc.)
- ❌ Delete emails permanently (only move to trash)

---

## Advanced: Environment Variables

For production deployments, you can set credentials as environment variables instead of calling `configure_email_provider`:

```bash
# In docker-compose.yml or deployment config:
environment:
  - GMAIL_CLIENT_ID=123...apps.googleusercontent.com
  - GMAIL_CLIENT_SECRET=GOCSPX-...
  - GMAIL_TOKEN=ya29.a0Ae4lvC...
  - GMAIL_REFRESH_TOKEN=1//0gQ...
```

---

## Next Steps

Once configured, you can use these operations:

- **List emails:** `list_emails`
- **Read email:** `read_email`
- **Send email:** `send_email`
- **Reply:** `reply_email`
- **Forward:** `forward_email`
- **Search:** `search_emails`
- **Delete:** `delete_email`
- **Mark read/unread:** `mark_email_read`
- **Get folders:** `get_folders`

See the [README.md](README.md) for detailed usage examples of each operation.

---

## Support

If you encounter issues:

1. Check the troubleshooting section above
2. Review the [full README](README.md)
3. Check container logs: `docker-compose logs tool-email-mcp`
4. File an issue on GitHub

---

**Happy emailing! 📧**
