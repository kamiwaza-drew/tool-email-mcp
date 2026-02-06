# Multi-User Setup Guide

## Your Requirements

✅ **a) One-time setup** - Users shouldn't need to re-authenticate constantly
✅ **b) User isolation** - Users should NOT see each other's emails

## How It Works

**Solution: Deploy separate instances per user**

Each user gets their own private container with their own Gmail credentials:

```
┌─────────────────┐
│  User: Alice    │
│  Container 1    │ ──→ Alice's Gmail Account
│  Port: 8001     │
└─────────────────┘

┌─────────────────┐
│  User: Bob      │
│  Container 2    │ ──→ Bob's Gmail Account
│  Port: 8002     │
└─────────────────┘
```

**Result:**
- ✅ Alice and Bob cannot see each other's emails (separate containers)
- ✅ Credentials persist across restarts (environment variables)
- ✅ One-time OAuth setup per user (refresh tokens auto-renew)

---

## Setup: Option 1 - Environment Variables (Recommended)

Each user creates their own deployment with persistent credentials.

### Step 1: Get OAuth Tokens

Each user follows [GMAIL_SETUP.md](GMAIL_SETUP.md) to get their tokens:

```bash
cd /home/kamiwaza/tools/tool-email-mcp
python get_gmail_token.py
```

This outputs:
```json
{
  "credentials": {
    "client_id": "123...apps.googleusercontent.com",
    "client_secret": "GOCSPX-...",
    "refresh_token": "1//0gQ..."
  }
}
```

### Step 2: Create Environment File

Each user creates a `.env` file in their deployment:

**Alice's `.env.alice`:**
```bash
GMAIL_CLIENT_ID=alice_123...apps.googleusercontent.com
GMAIL_CLIENT_SECRET=alice_GOCSPX-...
GMAIL_REFRESH_TOKEN=alice_1//0gQ...
```

**Bob's `.env.bob`:**
```bash
GMAIL_CLIENT_ID=bob_456...apps.googleusercontent.com
GMAIL_CLIENT_SECRET=bob_GOCSPX-...
GMAIL_REFRESH_TOKEN=bob_1//0gQ...
```

### Step 3: Deploy with Environment File

**Alice's deployment:**
```bash
cd /home/kamiwaza/tools/tool-email-mcp
docker-compose --env-file .env.alice -p alice-gmail up -d
```

**Bob's deployment:**
```bash
cd /home/kamiwaza/tools/tool-email-mcp
docker-compose --env-file .env.bob -p bob-gmail up -d
```

### Step 4: Verify

**Alice's endpoint:**
```bash
curl http://localhost:8001/health
# Returns: {"status": "healthy", "provider_configured": true}

curl -X POST http://localhost:8001/mcp -d '{
  "tool": "list_emails",
  "arguments": {"folder": "INBOX", "limit": 5}
}'
# Returns Alice's emails only
```

**Bob's endpoint:**
```bash
curl http://localhost:8002/health
# Returns: {"status": "healthy", "provider_configured": true}

curl -X POST http://localhost:8002/mcp -d '{
  "tool": "list_emails",
  "arguments": {"folder": "INBOX", "limit": 5}
}'
# Returns Bob's emails only
```

---

## Setup: Option 2 - Kamiwaza App Garden (UI)

If Kamiwaza supports per-user tool deployments in the UI:

### Step 1: Each User Deploys

**Alice:**
1. Go to **Tool Shed** in Kamiwaza UI
2. Find **Email MCP Tool**
3. Click **Deploy**
4. Name: `alice-gmail` (or just keep default)
5. Tool gets assigned unique endpoint

**Bob:**
1. Go to **Tool Shed**
2. Find **Email MCP Tool**
3. Click **Deploy**
4. Name: `bob-gmail`
5. Gets different endpoint than Alice

### Step 2: Each User Configures

**Alice configures her instance:**
```bash
# Alice's endpoint (from Kamiwaza)
ALICE_ENDPOINT="http://localhost:8001/mcp"

curl -X POST $ALICE_ENDPOINT -d '{
  "tool": "configure_email_provider",
  "arguments": {
    "provider": "gmail",
    "credentials": {
      "token": "",
      "refresh_token": "alice_1//0gQ...",
      "client_id": "alice_123...apps.googleusercontent.com",
      "client_secret": "alice_GOCSPX-..."
    }
  }
}'
```

**Bob configures his instance:**
```bash
# Bob's endpoint (different from Alice)
BOB_ENDPOINT="http://localhost:8002/mcp"

curl -X POST $BOB_ENDPOINT -d '{
  "tool": "configure_email_provider",
  "arguments": {
    "provider": "gmail",
    "credentials": {
      "token": "",
      "refresh_token": "bob_1//0gQ...",
      "client_id": "bob_456...apps.googleusercontent.com",
      "client_secret": "bob_GOCSPX-..."
    }
  }
}'
```

### Step 3: Use Individual Endpoints

Each user only accesses their own endpoint:

**Alice:**
```bash
curl -X POST http://localhost:8001/mcp -d '{
  "tool": "send_email",
  "arguments": {
    "to": ["colleague@company.com"],
    "subject": "From Alice",
    "body": "This is Alice's email"
  }
}'
```

**Bob:**
```bash
curl -X POST http://localhost:8002/mcp -d '{
  "tool": "send_email",
  "arguments": {
    "to": ["colleague@company.com"],
    "subject": "From Bob",
    "body": "This is Bob's email"
  }
}'
```

---

## Understanding the Isolation

### What Each User Sees

**Alice can:**
- ✅ Read Alice's emails
- ✅ Send from Alice's account
- ✅ Search Alice's inbox
- ❌ **Cannot** see Bob's emails
- ❌ **Cannot** access Bob's container

**Bob can:**
- ✅ Read Bob's emails
- ✅ Send from Bob's account
- ✅ Search Bob's inbox
- ❌ **Cannot** see Alice's emails
- ❌ **Cannot** access Alice's container

### Technical Isolation

```
Process Isolation:    ✅ Separate Docker containers
Network Isolation:    ✅ Different ports
Credential Isolation: ✅ Different OAuth tokens
Storage Isolation:    ✅ No shared state
Memory Isolation:     ✅ Separate process memory
```

---

## Resource Usage

Each email tool instance uses:
- **CPU:** ~0.1-0.5 cores (idle to active)
- **Memory:** ~256MB RAM per container
- **Storage:** ~100MB per image

**Example for 10 users:**
- Total RAM: ~2.5GB
- Total Storage: ~1GB
- CPU: Shared, mostly idle

For most deployments, this is acceptable overhead for strong security isolation.

---

## Credential Persistence

### With Environment Variables (Option 1)
✅ **Survives container restart** - credentials loaded from `.env` file
✅ **Survives system reboot** - Docker Compose restores containers
✅ **Token refresh** - Gmail refresh tokens auto-renew access tokens

### Without Environment Variables (Option 2)
⚠️ **Lost on container restart** - need to reconfigure via API call
✅ **Token refresh** - Still works during container lifetime

**Recommendation:** Use environment variables for production deployments.

---

## Security Best Practices

### Per-User Credentials
1. ✅ **Separate OAuth apps** - Each user creates their own Google Cloud project
2. ✅ **Separate refresh tokens** - No token sharing between users
3. ✅ **Access control** - Container-level isolation

### Credential Storage
1. ✅ **Environment variables** - Standard Docker secret management
2. ✅ **File permissions** - `.env` files should be `chmod 600` (owner-only)
3. ✅ **No git commits** - Add `.env.*` to `.gitignore`

### Container Security
1. ✅ **Non-root user** - Runs as `appuser` inside container
2. ✅ **Resource limits** - CPU and memory constraints
3. ✅ **Network isolation** - Each container on separate port

---

## Troubleshooting

### "Can Alice see Bob's emails?"

**No.** They are in completely separate containers with separate credentials.

To verify:
```bash
# Check running containers
docker ps | grep email-mcp

# Should see:
alice-gmail-tool-email-mcp-1  (port 8001)
bob-gmail-tool-email-mcp-1    (port 8002)
```

### "Do I need to re-authenticate after restart?"

**No** (if using environment variables). The refresh token automatically gets a new access token.

### "What if I restart the container?"

**With env vars:** Credentials auto-configure on startup (✅ persistent)
**Without env vars:** Need to call `configure_email_provider` again (⚠️ manual)

### "Can I switch between my work and personal Gmail?"

**Yes!** Deploy two separate instances:
- `alice-work-gmail` → alice@company.com
- `alice-personal-gmail` → alice@gmail.com

Each instance connects to a different Gmail account.

---

## Comparison: Single vs Multi-Tenant

| Feature | Current (Per-User Instances) | Multi-Tenant (Future) |
|---------|---------------------------|---------------------|
| User isolation | ✅ Strong (containers) | ✅ Strong (if done right) |
| Setup complexity | ⚠️ Each user deploys | ✅ Admin deploys once |
| Resource usage | ⚠️ High (N containers) | ✅ Low (1 container) |
| Security model | ✅ Simple (separate) | ⚠️ Complex (shared) |
| Available today | ✅ Yes | ❌ No (needs development) |

**For now:** Per-user instances is the recommended approach.

**Future:** If you have >20 users, consider requesting multi-tenant support.

---

## Next Steps

1. **Read** [GMAIL_SETUP.md](GMAIL_SETUP.md) for OAuth setup
2. **Choose** Option 1 (env vars) or Option 2 (UI deployment)
3. **Deploy** one instance per user
4. **Configure** each instance with user's credentials
5. **Test** by listing emails from each user's endpoint

**Questions?** See [MULTI_USER_ARCHITECTURE.md](MULTI_USER_ARCHITECTURE.md) for technical details.
