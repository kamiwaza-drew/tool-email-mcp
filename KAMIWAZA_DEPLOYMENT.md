# Deploying Email Tool in Kamiwaza

## 📦 What's in the Docker Container

The Docker image includes all three email protocols:
- ✅ **OAuth 2.0** (Gmail API, Outlook API)
- ✅ **IMAP/SMTP** (Generic email servers)
- ✅ **POP3/SMTP** (Gmail POP, etc.)

All code is automatically included when you build the Docker image!

## 🔐 Setting Secrets in Kamiwaza

There are **3 ways** to configure email credentials in Kamiwaza:

### Method 1: Environment Variables (Recommended for Production)

Set environment variables when deploying the tool:

```bash
# Via Kamiwaza CLI
kamiwaza tool deploy tool-email-mcp \
  --env POP3_USERNAME=appiispanen@gmail.com \
  --env POP3_PASSWORD=your_app_password \
  --env POP3_SERVER=pop.gmail.com \
  --env POP3_PORT=995 \
  --env SMTP_SERVER=smtp.gmail.com \
  --env SMTP_PORT=587
```

### Method 2: Kamiwaza UI (Easiest)

1. **Log in to Kamiwaza** at https://localhost
2. **Navigate to Tools** → Deploy New Tool
3. **Select** `tool-email-mcp`
4. **Under "Environment Variables"**, add:
   ```
   POP3_USERNAME = appiispanen@gmail.com
   POP3_PASSWORD = wdwb itsv fxbk pmif
   POP3_SERVER = pop.gmail.com
   POP3_PORT = 995
   SMTP_SERVER = smtp.gmail.com
   SMTP_PORT = 587
   SMTP_USE_STARTTLS = true
   ```
5. **Click Deploy**

### Method 3: Kamiwaza Secrets Manager (Most Secure)

If Kamiwaza has a secrets manager:

```bash
# Store secrets
kamiwaza secret create gmail-password --value "wdwb itsv fxbk pmif"

# Deploy with secret reference
kamiwaza tool deploy tool-email-mcp \
  --env POP3_USERNAME=appiispanen@gmail.com \
  --env-secret POP3_PASSWORD=gmail-password \
  --env POP3_SERVER=pop.gmail.com
```

## 🏗️ Rebuilding Docker Image with New Code

Your new IMAP/POP3 code is already in `src/`, so rebuild:

```bash
cd /home/kamiwaza/tools/tool-email-mcp

# Build new image
docker build -t kamiwazaai/tool-email-mcp:1.0.1 .

# Or build with docker-compose
docker-compose build

# Tag for deployment
docker tag kamiwazaai/tool-email-mcp:1.0.1 kamiwazaai/tool-email-mcp:latest
```

## 📝 Deployment Configuration Examples

### Gmail POP3 Deployment

Create `deploy-gmail.env`:
```bash
POP3_USERNAME=appiispanen@gmail.com
POP3_PASSWORD=wdwb itsv fxbk pmif
POP3_SERVER=pop.gmail.com
POP3_PORT=995
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USE_STARTTLS=true
```

Deploy:
```bash
docker run -d \
  --name email-tool-gmail \
  --env-file deploy-gmail.env \
  -p 8000:8000 \
  kamiwazaai/tool-email-mcp:1.0.1
```

### Generic IMAP Deployment

Create `deploy-imap.env`:
```bash
IMAP_USERNAME=test@directmachines.com
IMAP_PASSWORD=WElcome#_321
IMAP_SERVER=d12569.usc1.stableserver.net
IMAP_PORT=993
SMTP_SERVER=d12569.usc1.stableserver.net
SMTP_PORT=465
IMAP_USE_SSL=true
```

Deploy:
```bash
docker run -d \
  --name email-tool-imap \
  --env-file deploy-imap.env \
  -p 8001:8000 \
  kamiwazaai/tool-email-mcp:1.0.1
```

## 🔍 Verifying Deployment

### Check Container Logs
```bash
# Via Docker
docker logs email-tool-gmail

# Via Kamiwaza
kamiwaza tool logs tool-email-mcp
```

Expected output:
```
🔐 IMAP credentials configured via environment
⏱️  Session timeout: 3600 seconds (60 minutes)
INFO: Started server process
INFO: Uvicorn running on http://0.0.0.0:8000
```

### Test the Deployed Tool

```bash
# Health check
curl http://localhost:8000/health

# Check authentication status
curl http://localhost:8000/oauth/status

# List available MCP tools
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/list","id":1}'
```

## 🎯 Configuration Priority

The tool checks for credentials in this order:

1. **Environment Variables** (highest priority)
   - `IMAP_USERNAME`, `IMAP_PASSWORD`, etc.
   - `POP3_USERNAME`, `POP3_PASSWORD`, etc.

2. **OAuth Session** (if authenticated via web UI)
   - OAuth tokens stored in session

3. **Manual Configuration** (via MCP tool)
   - `configure_email_provider` tool call

**Best Practice:** Set credentials via environment variables for automated/production use.

## 🔒 Security Best Practices

### ✅ DO:
- Use environment variables for secrets
- Use Kamiwaza secrets manager if available
- Use `.env` files for local development (gitignored)
- Rotate passwords regularly
- Use Gmail App Passwords (not real password)
- Limit access to deployed tools

### ❌ DON'T:
- Commit secrets to git
- Hardcode passwords in code
- Use your real Gmail password (use App Password)
- Share App Passwords across tools
- Log passwords or tokens

## 🚀 Deployment Checklist

- [ ] Build Docker image with latest code
- [ ] Test locally with `docker run`
- [ ] Prepare environment variables
- [ ] Deploy via Kamiwaza UI or CLI
- [ ] Verify container is running
- [ ] Check logs for "IMAP/POP3 configured"
- [ ] Test with health check endpoint
- [ ] Test email operations via MCP tools

## 📊 Monitoring

### Health Checks
```bash
# Docker health check (automatic)
docker ps  # Check STATUS column for (healthy)

# Manual health check
curl http://localhost:8000/health
```

### Logs
```bash
# View container logs
docker logs -f email-tool-gmail

# View Kamiwaza logs
kamiwaza tool logs tool-email-mcp --follow
```

### Metrics
- Container should be "healthy" within 30 seconds
- Memory usage: ~150-200MB
- CPU usage: <5% idle, <50% under load

## 🛠️ Troubleshooting

### Container Won't Start
```bash
# Check logs
docker logs email-tool-gmail

# Common issues:
# - Missing environment variables
# - Port already in use
# - Invalid credentials
```

### Authentication Fails
```bash
# Verify env vars are set
docker exec email-tool-gmail env | grep -E "IMAP|POP3|SMTP"

# Test credentials outside container
python3 test_gmail_pop3.py
```

### Can't Connect to Email Server
```bash
# Check network connectivity from container
docker exec email-tool-gmail curl -v telnet://pop.gmail.com:995

# Check firewall rules
# Ensure ports 995 (POP3), 993 (IMAP), 587 (SMTP) are allowed
```

## 📚 Related Documentation

- `TESTING_GUIDE.md` - Local testing without Kamiwaza
- `GMAIL_POP3_SETUP.md` - Gmail-specific setup
- `README.md` - General tool documentation
- `kamiwaza.json` - Tool metadata and configuration

## 💡 Pro Tips

1. **Use different instances for different accounts:**
   ```bash
   # Deploy Gmail instance
   kamiwaza tool deploy tool-email-mcp --name email-gmail --env-file gmail.env

   # Deploy IMAP instance
   kamiwaza tool deploy tool-email-mcp --name email-imap --env-file imap.env
   ```

2. **Environment-specific configs:**
   - `.env.dev` - Development
   - `.env.staging` - Staging
   - `.env.prod` - Production

3. **Backup your environment configs:**
   ```bash
   cp deploy-gmail.env deploy-gmail.env.backup
   ```

4. **Use Docker secrets for production:**
   ```bash
   echo "wdwb itsv fxbk pmif" | docker secret create gmail_password -
   docker service create \
     --name email-tool \
     --secret gmail_password \
     --env POP3_PASSWORD_FILE=/run/secrets/gmail_password \
     kamiwazaai/tool-email-mcp:1.0.1
   ```
