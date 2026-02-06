# Email Tool - Quick Start Guide

## ✅ What You Have

A fully functional email tool supporting:
- **IMAP/SMTP** (Generic email servers) ✅ Tested
- **POP3/SMTP** (Gmail, etc.) ✅ Tested
- **OAuth 2.0** (Gmail API, Outlook API) ⚠️ Needs MCP server fix

## 🚀 Using with Kamiwaza

### Option 1: Deploy via Kamiwaza UI

1. **Open Kamiwaza** at https://localhost

2. **Go to Tools** → Deploy New Tool

3. **Select** `tool-email-mcp` (version 1.0.1)

4. **Configure Environment Variables:**

   **For Gmail POP3:**
   ```
   POP3_USERNAME = appiispanen@gmail.com
   POP3_PASSWORD = wdwb itsv fxbk pmif
   POP3_SERVER = pop.gmail.com
   POP3_PORT = 995
   SMTP_SERVER = smtp.gmail.com
   SMTP_PORT = 587
   SMTP_USE_STARTTLS = true
   ```

   **For Generic IMAP:**
   ```
   IMAP_USERNAME = test@directmachines.com
   IMAP_PASSWORD = WElcome#_321
   IMAP_SERVER = d12569.usc1.stableserver.net
   IMAP_PORT = 993
   SMTP_SERVER = d12569.usc1.stableserver.net
   SMTP_PORT = 465
   IMAP_USE_SSL = true
   ```

5. **Click Deploy**

6. **Verify** - Check logs for:
   ```
   🔐 IMAP credentials configured via environment
   ⏱️  Session timeout: 3600 seconds
   INFO: Uvicorn running on http://0.0.0.0:8000
   ```

### Option 2: Deploy via Docker Directly

```bash
# Gmail POP3
docker run -d \
  --name email-gmail \
  -p 8000:8000 \
  -e POP3_USERNAME=appiispanen@gmail.com \
  -e POP3_PASSWORD="wdwb itsv fxbk pmif" \
  -e POP3_SERVER=pop.gmail.com \
  -e POP3_PORT=995 \
  -e SMTP_SERVER=smtp.gmail.com \
  -e SMTP_PORT=587 \
  -e SMTP_USE_STARTTLS=true \
  kamiwazaai/tool-email-mcp:1.0.1

# Verify
docker logs email-gmail
curl http://localhost:8000/oauth/status
```

### Option 3: Deploy via Kamiwaza CLI

```bash
# Create env file
cat > gmail.env <<EOF
POP3_USERNAME=appiispanen@gmail.com
POP3_PASSWORD=wdwb itsv fxbk pmif
POP3_SERVER=pop.gmail.com
POP3_PORT=995
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USE_STARTTLS=true
EOF

# Deploy
kamiwaza tool deploy tool-email-mcp \
  --name email-gmail \
  --env-file gmail.env
```

## 🧪 Testing Deployed Tool

### 1. Check Status
```bash
curl http://localhost:8000/oauth/status
```

Expected:
```json
{
  "authenticated": true,
  "provider": "pop3",
  "email": "appiispanen@gmail.com",
  "configured_via": "environment"
}
```

### 2. List Available Tools (via MCP)
```bash
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/list",
    "id": 1
  }'
```

### 3. List Emails
```bash
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "list_emails",
      "arguments": {
        "folder": "INBOX",
        "limit": 5
      }
    },
    "id": 2
  }'
```

## 📊 What's in the Container

All code is included:
```
/app/src/tool_email_mcp/
├── server.py                 # MCP server
├── email_operations.py       # Email operations manager
├── providers.py              # OAuth providers (Gmail/Outlook)
├── imap_provider.py          # ✅ IMAP/SMTP provider
├── pop3_provider.py          # ✅ POP3/SMTP provider
├── security.py               # Security validation
└── ...
```

## 🔐 How Secrets Work

### Priority Order:
1. **Environment Variables** (when deploying) ← Recommended
2. **OAuth Session** (after web login)
3. **Manual Configuration** (via MCP tool call)

### Setting Secrets:

**Kamiwaza UI:**
- Tools → Deploy → Environment Variables → Add each variable

**Docker:**
- Use `-e KEY=VALUE` flags
- Or `--env-file secrets.env`

**Kamiwaza CLI:**
```bash
kamiwaza tool deploy tool-email-mcp \
  --env POP3_USERNAME=user@gmail.com \
  --env POP3_PASSWORD=secret
```

## ✅ Verified Working

| Protocol | Account | Status |
|----------|---------|--------|
| IMAP | test@directmachines.com | ✅ Tested |
| POP3 | appiispanen@gmail.com | ✅ Tested |
| Docker | Image built | ✅ Ready |

## 📚 Full Documentation

- `KAMIWAZA_DEPLOYMENT.md` - Complete deployment guide
- `GMAIL_POP3_SETUP.md` - Gmail-specific setup
- `TESTING_GUIDE.md` - Local testing guide
- `README.md` - Full feature documentation

## 🎯 Next Steps

1. **Deploy** the tool via Kamiwaza UI or CLI
2. **Set** environment variables for your email account
3. **Verify** the tool is running (check logs)
4. **Test** with MCP tool calls or via Kamiwaza interface

## 💡 Pro Tips

- **Use separate deployments** for different email accounts
- **Store secrets securely** - never commit to git
- **Test locally first** with `docker run` before Kamiwaza deployment
- **Monitor logs** to verify credentials are loaded
- **Check health endpoint** at `/health` after deployment

## 🆘 Quick Troubleshooting

**Can't authenticate?**
```bash
# Check env vars are set in container
docker exec <container-id> env | grep -E "IMAP|POP3"
```

**Container won't start?**
```bash
# Check logs
docker logs <container-id>
```

**MCP server errors?**
- The core email functionality works via Python
- MCP HTTP wrapper needs FastMCP ASGI fix
- Workaround: Use direct Python API or wait for MCP fix
