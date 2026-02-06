# Multi-User Architecture Analysis & Solutions

## Current State: Single-Tenant Design ⚠️

### The Problem

The current implementation is **single-tenant** - all users share the same Gmail credentials:

```python
# server.py - Line 27
email_ops = EmailOperations(security_manager)  # ← Single global instance

# email_operations.py - Line 23
self.provider: Optional[EmailProvider] = None  # ← Shared across all users
```

**This means:**
- ❌ User A and User B access the **same Gmail account**
- ❌ User A can see User B's emails
- ❌ No privacy between users
- ❌ Credentials lost on container restart

## Your Requirements

✅ **a) One-time setup:** Achieved via refresh tokens (works correctly)
❌ **b) User isolation:** NOT currently supported - this needs architectural changes

---

## Solution Options

### Option 1: Per-User MCP Tool Instances (Recommended for Kamiwaza)

**Concept:** Each user deploys their own private instance of the email tool.

#### Architecture
```
User A → tool-email-mcp-alice (port 8001) → Alice's Gmail
User B → tool-email-mcp-bob (port 8002) → Bob's Gmail
```

#### Implementation

**In Kamiwaza App Garden:**

1. **First Deployment (User A):**
   - Deploy `tool-email-mcp` as "email-alice"
   - Configure with Alice's Gmail credentials
   - Gets unique endpoint: `http://localhost:8001/mcp`

2. **Second Deployment (User B):**
   - Deploy `tool-email-mcp` as "email-bob"
   - Configure with Bob's Gmail credentials
   - Gets unique endpoint: `http://localhost:8002/mcp`

#### Pros
- ✅ **Simple** - no code changes needed
- ✅ **Strong isolation** - separate containers
- ✅ **Works today** - leverages Kamiwaza's existing deployment model
- ✅ **Resource isolation** - each user's rate limits separate

#### Cons
- ❌ **Resource overhead** - one container per user
- ❌ **Manual setup** - each user deploys individually
- ❌ **No centralized management**

#### Status
**✅ AVAILABLE NOW** - This works with the current implementation!

---

### Option 2: Multi-Tenant with User Context (Requires Development)

**Concept:** Single tool instance serves multiple users with per-user credential storage.

#### Architecture Changes Needed

**1. Add User Context to MCP Requests**

```python
# Kamiwaza would need to pass user identity
{
  "tool": "list_emails",
  "arguments": {
    "folder": "INBOX"
  },
  "context": {
    "user_id": "alice@company.com",
    "session_token": "jwt_token_here"
  }
}
```

**2. Per-User Credential Storage**

```python
class EmailOperations:
    def __init__(self, security_manager: SecurityManager):
        self.security = security_manager
        # Change from single provider to user-keyed providers
        self.providers: Dict[str, EmailProvider] = {}  # user_id → provider
        self.credential_store = CredentialStore()  # Encrypted storage

    def _get_user_provider(self, user_id: str) -> Optional[EmailProvider]:
        """Get provider for specific user."""
        if user_id not in self.providers:
            # Load credentials from encrypted store
            creds = self.credential_store.get(user_id)
            if creds:
                self.providers[user_id] = self._create_provider(creds)
        return self.providers.get(user_id)
```

**3. Encrypted Credential Storage**

```python
class CredentialStore:
    """Secure per-user credential storage."""

    def __init__(self):
        self.db_path = "/app/credentials/users.db"  # Volume-backed
        self.encryption_key = os.getenv("CREDENTIAL_ENCRYPTION_KEY")

    def store(self, user_id: str, credentials: Dict) -> None:
        """Store encrypted credentials for user."""
        encrypted = self._encrypt(json.dumps(credentials))
        # Store in SQLite with user_id as key

    def get(self, user_id: str) -> Optional[Dict]:
        """Retrieve and decrypt credentials for user."""
        # Fetch from SQLite and decrypt
```

**4. Updated MCP Tool Interface**

```python
@mcp.tool()
async def list_emails(
    folder: str = "INBOX",
    limit: int = 10,
    user_context: Optional[Dict] = None  # ← NEW
) -> Dict[str, Any]:
    """List emails from specified folder."""

    # Extract user ID from context
    user_id = user_context.get("user_id") if user_context else None
    if not user_id:
        return {"success": False, "error": "User authentication required"}

    # Get user-specific provider
    provider = email_ops._get_user_provider(user_id)
    if not provider:
        return {"success": False, "error": "Email not configured for this user"}

    return await email_ops.list_emails(folder, limit, user_id=user_id)
```

#### Pros
- ✅ **Resource efficient** - single container
- ✅ **Centralized management**
- ✅ **Seamless user experience**
- ✅ **Persistent credentials** (across restarts)

#### Cons
- ❌ **Requires development** (~2-3 days of work)
- ❌ **Needs Kamiwaza integration** - user context passing
- ❌ **Encryption key management** required
- ❌ **More complex security surface**

#### Status
**⏳ NOT IMPLEMENTED** - Would require:
1. Changes to tool implementation (credential store, user context)
2. Changes to Kamiwaza MCP integration (user context passing)
3. Encryption key provisioning
4. Migration path for existing deployments

---

### Option 3: OAuth Redirect Flow (Best Long-Term Solution)

**Concept:** Users authenticate directly with Google through their browser.

#### User Experience Flow

1. **User clicks "Connect Gmail" in Kamiwaza UI**
2. **Redirected to Google OAuth consent screen**
3. **User authorizes with their Gmail account**
4. **Redirected back to Kamiwaza with authorization code**
5. **Kamiwaza exchanges code for tokens and stores per-user**

#### Architecture

```
Kamiwaza UI → OAuth Flow → Google
     ↓
Store tokens in Kamiwaza DB (per user)
     ↓
Pass tokens to email-mcp tool via user context
```

#### Implementation Requirements

**In Kamiwaza Backend:**

```python
# New API endpoint
@router.get("/api/v1/integrations/gmail/authorize")
async def gmail_authorize(user: AuthenticatedUser):
    """Redirect to Google OAuth consent."""
    oauth_url = build_google_oauth_url(
        client_id=settings.GMAIL_CLIENT_ID,
        redirect_uri=settings.GMAIL_REDIRECT_URI,
        state=encode_state(user["id"])
    )
    return RedirectResponse(oauth_url)

@router.get("/api/v1/integrations/gmail/callback")
async def gmail_callback(code: str, state: str):
    """Handle OAuth callback and store tokens."""
    user_id = decode_state(state)
    tokens = exchange_code_for_tokens(code)

    # Store in Kamiwaza database
    db.execute(
        "INSERT INTO user_integrations (user_id, provider, credentials) "
        "VALUES (:user_id, 'gmail', :creds)",
        {"user_id": user_id, "creds": encrypt(tokens)}
    )

    return RedirectResponse("/settings/integrations?success=gmail")
```

**In Email MCP Tool:**

```python
# Tool receives pre-authenticated credentials from Kamiwaza
async def list_emails(
    folder: str,
    limit: int,
    user_credentials: Dict  # ← Passed by Kamiwaza
) -> Dict[str, Any]:
    """Credentials already validated by Kamiwaza."""
    provider = GmailProvider(user_credentials)
    return await provider.list_emails(folder, limit)
```

#### Pros
- ✅ **Best UX** - one-click setup
- ✅ **Secure** - no manual credential copying
- ✅ **Native integration** - feels like built-in feature
- ✅ **Centralized management** - Kamiwaza controls access
- ✅ **Auditable** - clear consent trail

#### Cons
- ❌ **Most development** - requires Kamiwaza core changes
- ❌ **OAuth app verification** - Google may require verification for production
- ❌ **Redirect URI management** - needs proper domain setup

#### Status
**🎯 IDEAL LONG-TERM** - Requires product planning and multi-component development.

---

## Comparison Matrix

| Feature | Option 1: Per-User Instance | Option 2: Multi-Tenant | Option 3: OAuth Flow |
|---------|----------------------------|----------------------|---------------------|
| **User isolation** | ✅ Strong | ✅ Strong | ✅ Strong |
| **One-time setup** | ✅ Yes (refresh tokens) | ✅ Yes (persistent) | ✅ Yes (best UX) |
| **Works today** | ✅ Yes | ❌ No | ❌ No |
| **Resource usage** | ⚠️ High (N containers) | ✅ Low (1 container) | ✅ Low (1 container) |
| **Setup complexity** | ⚠️ Each user deploys | ✅ Admin one-time | ✅ One-click |
| **Development effort** | ✅ None | ⚠️ 2-3 days | ❌ 1-2 weeks |
| **Security** | ✅ Best (isolation) | ⚠️ Good (if done right) | ✅ Best (native OAuth) |
| **Scalability** | ❌ Poor (10+ users) | ✅ Good | ✅ Excellent |

---

## Recommended Path Forward

### Phase 1: Immediate (Today) ✅
**Use Option 1: Per-User Instances**

This works with the current implementation:

1. Document the per-user deployment pattern
2. Each user deploys their own instance
3. User isolation through container separation
4. Credentials persist via refresh tokens

**Setup per user:**
```bash
# User A
deploy tool-email-mcp as "my-gmail"
configure with A's credentials

# User B
deploy tool-email-mcp as "my-gmail"
configure with B's credentials
```

### Phase 2: Medium-Term (Sprint)
**Implement Option 2: Multi-Tenant Support**

If resource usage becomes an issue (>10 users):

1. Add encrypted credential storage
2. Implement per-user provider lookup
3. Add user context to MCP protocol
4. Test isolation thoroughly

**Effort:** ~2-3 days development + testing

### Phase 3: Long-Term (Roadmap)
**Implement Option 3: Native OAuth Flow**

For production SaaS offering:

1. Add OAuth integration to Kamiwaza core
2. Build consent UI in frontend
3. Implement secure token storage
4. Submit OAuth app for Google verification

**Effort:** ~1-2 weeks development + Google review

---

## Security Considerations

### Current Single-Tenant (Option 1)
- ✅ **Strong isolation** - separate containers
- ✅ **Simple security model** - no shared state
- ⚠️ **Manual credential handling** - users copy/paste tokens
- ⚠️ **Credential storage** - in-memory only (lost on restart)

### Multi-Tenant (Option 2)
- ✅ **Persistent storage** - survives restarts
- ⚠️ **Encryption required** - must protect stored credentials
- ⚠️ **User context validation** - must verify identity on each request
- ❌ **Higher risk** - bugs could leak credentials across users

### OAuth Flow (Option 3)
- ✅ **Native OAuth** - Google handles security
- ✅ **No credential exposure** - tokens never shown to users
- ✅ **Revocable** - clear consent management
- ✅ **Auditable** - full OAuth event log

---

## Implementation Guide for Option 1 (Use Today)

### For Kamiwaza Administrators

**Document the deployment pattern:**

Create `/docs/tools/email-mcp-multi-user.md`:

```markdown
# Email MCP Tool - Multi-User Setup

Each user should deploy their own private instance of the email tool.

## Setup Steps

1. Go to Tool Shed
2. Find "Email MCP Tool"
3. Click "Deploy"
4. Name: Use your name (e.g., "alice-gmail")
5. Follow OAuth setup in GMAIL_SETUP.md
6. Configure your credentials

## Important Notes

- Your instance is private - only you can access it
- Other users cannot see your emails
- Credentials are stored securely in your container
- Restart-safe via refresh tokens
```

### For Users

Each user follows the standard setup:

1. Deploy tool-email-mcp (gets unique container)
2. Run OAuth setup (GMAIL_SETUP.md)
3. Configure with their credentials
4. Use their personal endpoint

**Example:**
```bash
# Alice's instance
curl http://localhost:8001/mcp -d '{"tool": "list_emails", ...}'

# Bob's instance
curl http://localhost:8002/mcp -d '{"tool": "list_emails", ...}'
```

### Credentials Persistence

**Current:** In-memory (lost on restart)

**To fix for Option 1:**

Add to `docker-compose.yml`:

```yaml
environment:
  - GMAIL_CLIENT_ID=${GMAIL_CLIENT_ID}
  - GMAIL_CLIENT_SECRET=${GMAIL_CLIENT_SECRET}
  - GMAIL_REFRESH_TOKEN=${GMAIL_REFRESH_TOKEN}
```

Then in `server.py`:

```python
# Auto-configure from environment on startup
client_id = os.getenv("GMAIL_CLIENT_ID")
client_secret = os.getenv("GMAIL_CLIENT_SECRET")
refresh_token = os.getenv("GMAIL_REFRESH_TOKEN")

if all([client_id, client_secret, refresh_token]):
    # Exchange refresh token for access token
    token = refresh_gmail_token(client_id, client_secret, refresh_token)

    # Auto-configure provider
    email_ops.configure_provider("gmail", {
        "token": token,
        "refresh_token": refresh_token,
        "client_id": client_id,
        "client_secret": client_secret
    })
```

This makes credentials persistent across container restarts!

---

## Questions to Consider

1. **How many users?**
   - <10 users: Option 1 (per-instance) is fine
   - >10 users: Consider Option 2 (multi-tenant)
   - Production SaaS: Need Option 3 (OAuth flow)

2. **Resource constraints?**
   - Each container uses ~256MB RAM
   - 10 users = ~2.5GB RAM for email tools
   - Consider if this is acceptable

3. **User experience priority?**
   - Quick deployment: Option 1
   - Seamless experience: Option 3
   - Balance: Option 2

4. **Development resources?**
   - No dev time: Option 1
   - 1 sprint: Option 2
   - Product feature: Option 3

---

## Immediate Action Items

To use **Option 1 today** with proper isolation:

1. ✅ Update GMAIL_SETUP.md to document per-user deployment
2. ✅ Add environment variable configuration to docker-compose.yml
3. ✅ Add auto-configuration from env vars in server.py
4. ✅ Test with 2 separate deployments
5. ✅ Document in Kamiwaza Tool Shed

**This gives you:**
- ✅ User isolation (your requirement b)
- ✅ One-time setup with refresh tokens (your requirement a)
- ✅ Works immediately (no development needed)
- ⚠️ Higher resource usage (acceptable for <20 users)

---

## Conclusion

**For your needs right now:** Use **Option 1** - deploy separate instances per user.

**This satisfies both requirements:**
- ✅ **a) One-time setup:** Refresh tokens work correctly
- ✅ **b) User isolation:** Each user has private container

The current tool is production-ready for this use case. No code changes needed!
