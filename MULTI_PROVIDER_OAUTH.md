# Multi-Provider OAuth Design

## Supporting Gmail AND Outlook

Users need to connect different email providers:
- **Gmail** - Personal (@gmail.com) or Google Workspace (@company.com)
- **Outlook** - Personal (@outlook.com) or Microsoft 365 (@company.com)
- **Future** - Yahoo, ProtonMail, etc.

---

## User Experience

### Provider Selection

**User Flow:**
```
1. User clicks "Connect Email Account"
2. Sees provider selection:
   ┌─────────────────────────────┐
   │  Choose your email provider │
   │                             │
   │  [ Google / Gmail ]         │
   │  [ Microsoft / Outlook ]    │
   │                             │
   │  (More providers coming)    │
   └─────────────────────────────┘
3. User clicks their provider
4. Redirected to provider's OAuth consent
5. Authorizes
6. Redirected back - ready to use
```

### Multiple Accounts (Optional)

Users can connect multiple accounts:
```
Connected Accounts:
┌────────────────────────────────┐
│ 📧 alice@gmail.com             │
│    ✅ Connected (45 min left)   │
│    [Disconnect]                │
├────────────────────────────────┤
│ 📧 alice@company.com           │
│    ✅ Connected (20 min left)   │
│    [Disconnect]                │
└────────────────────────────────┘

[+ Connect Another Account]
```

---

## Architecture

### OAuth Flow with Provider Selection

```
┌────────────────┐
│  User          │
└───────┬────────┘
        │
        │ 1. "Connect Email"
        ↓
┌────────────────────────────────┐
│  Provider Selection UI         │
│  Choose: Gmail | Outlook       │
└───────┬────────────────────────┘
        │
        │ 2. User selects "Outlook"
        ↓
┌────────────────────────────────┐
│  /oauth/authorize?provider=    │
│  outlook                       │
└───────┬────────────────────────┘
        │
        │ 3. Redirect to provider
        ↓
┌────────────────────────────────┐
│  Microsoft OAuth Consent       │
│  login.microsoftonline.com     │
└───────┬────────────────────────┘
        │
        │ 4. User authorizes
        ↓
┌────────────────────────────────┐
│  /oauth/callback?              │
│  provider=outlook&code=...     │
└───────┬────────────────────────┘
        │
        │ 5. Exchange code for token
        ↓
┌────────────────────────────────┐
│  Session Created               │
│  provider: outlook             │
│  email: alice@company.com      │
└────────────────────────────────┘
```

---

## Implementation

### 1. Provider Configuration

**Environment Variables:**
```bash
# Gmail OAuth App
OAUTH_GMAIL_CLIENT_ID=123...apps.googleusercontent.com
OAUTH_GMAIL_CLIENT_SECRET=GOCSPX-abc123...

# Outlook OAuth App (Azure AD)
OAUTH_OUTLOOK_CLIENT_ID=456...
OAUTH_OUTLOOK_CLIENT_SECRET=def456...
OAUTH_OUTLOOK_TENANT_ID=common  # or specific tenant

# Redirect URIs
OAUTH_REDIRECT_URI=https://kamiwaza.example.com/oauth/callback

# Session config
SESSION_TIMEOUT=3600
```

**Provider Registry:**
```python
# Provider configuration registry
OAUTH_PROVIDERS = {
    "gmail": {
        "name": "Google / Gmail",
        "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "userinfo_url": "https://www.googleapis.com/oauth2/v2/userinfo",
        "scopes": [
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/gmail.send",
            "https://www.googleapis.com/auth/gmail.modify",
            "https://www.googleapis.com/auth/userinfo.email"
        ],
        "client_id_env": "OAUTH_GMAIL_CLIENT_ID",
        "client_secret_env": "OAUTH_GMAIL_CLIENT_SECRET",
        "logo": "/static/google-logo.svg"
    },
    "outlook": {
        "name": "Microsoft / Outlook",
        "auth_url": "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize",
        "token_url": "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token",
        "userinfo_url": "https://graph.microsoft.com/v1.0/me",
        "scopes": [
            "https://graph.microsoft.com/Mail.Read",
            "https://graph.microsoft.com/Mail.ReadWrite",
            "https://graph.microsoft.com/Mail.Send",
            "https://graph.microsoft.com/User.Read"
        ],
        "client_id_env": "OAUTH_OUTLOOK_CLIENT_ID",
        "client_secret_env": "OAUTH_OUTLOOK_CLIENT_SECRET",
        "tenant_id_env": "OAUTH_OUTLOOK_TENANT_ID",
        "logo": "/static/microsoft-logo.svg"
    }
}
```

### 2. OAuth Authorization Endpoint

**Updated to support provider parameter:**

```python
@mcp.custom_route("/oauth/authorize", methods=["GET"])
async def oauth_authorize(request: Request) -> Response:
    """Initiate OAuth flow for specified provider.

    Query params:
        provider: "gmail" or "outlook"
    """

    provider_name = request.query_params.get("provider", "gmail")

    # Validate provider
    if provider_name not in OAUTH_PROVIDERS:
        return JSONResponse(
            {"error": f"Unknown provider: {provider_name}"},
            status_code=400
        )

    provider_config = OAUTH_PROVIDERS[provider_name]

    # Get OAuth credentials from environment
    client_id = os.getenv(provider_config["client_id_env"])
    if not client_id:
        return JSONResponse(
            {"error": f"{provider_name} OAuth not configured"},
            status_code=500
        )

    # Generate state token (CSRF protection)
    state = secrets.token_urlsafe(32)
    session_id = request.cookies.get("kamiwaza_session")

    # Store state with provider info
    oauth_states[state] = {
        "provider": provider_name,
        "session_id": session_id,
        "created_at": time.time()
    }

    # Build provider-specific OAuth URL
    redirect_uri = os.getenv("OAUTH_REDIRECT_URI")

    # Handle tenant ID for Outlook
    auth_url = provider_config["auth_url"]
    if provider_name == "outlook":
        tenant_id = os.getenv(
            provider_config["tenant_id_env"],
            "common"  # Default: any Microsoft account
        )
        auth_url = auth_url.format(tenant=tenant_id)

    # Build authorization URL
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(provider_config["scopes"]),
        "state": state,
        "access_type": "online",  # No refresh token
        "prompt": "consent"  # Always show consent
    }

    oauth_url = f"{auth_url}?{urlencode(params)}"

    return RedirectResponse(oauth_url, status_code=302)
```

### 3. OAuth Callback Handler

**Handles all providers:**

```python
@mcp.custom_route("/oauth/callback", methods=["GET"])
async def oauth_callback(request: Request) -> Response:
    """Handle OAuth callback from any provider."""

    code = request.query_params.get("code")
    state = request.query_params.get("state")
    error = request.query_params.get("error")

    # Handle errors
    if error:
        return RedirectResponse(
            f"/oauth/error?error={error}",
            status_code=302
        )

    # Verify state (CSRF protection)
    if state not in oauth_states:
        return JSONResponse(
            {"error": "Invalid state token"},
            status_code=400
        )

    state_data = oauth_states.pop(state)
    provider_name = state_data["provider"]

    # Check state expiry (5 minutes)
    if time.time() - state_data["created_at"] > 300:
        return JSONResponse(
            {"error": "State token expired"},
            status_code=400
        )

    # Get provider config
    provider_config = OAUTH_PROVIDERS[provider_name]

    # Get OAuth credentials
    client_id = os.getenv(provider_config["client_id_env"])
    client_secret = os.getenv(provider_config["client_secret_env"])
    redirect_uri = os.getenv("OAUTH_REDIRECT_URI")

    # Build token URL
    token_url = provider_config["token_url"]
    if provider_name == "outlook":
        tenant_id = os.getenv(
            provider_config["tenant_id_env"],
            "common"
        )
        token_url = token_url.format(tenant=tenant_id)

    # Exchange code for token
    async with aiohttp.ClientSession() as session:
        async with session.post(
            token_url,
            data={
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code"
            }
        ) as resp:
            if resp.status != 200:
                error_data = await resp.json()
                return JSONResponse(
                    {"error": "Token exchange failed", "details": error_data},
                    status_code=500
                )

            token_data = await resp.json()

    # Get user info (email address)
    access_token = token_data["access_token"]
    user_email = await get_user_email(provider_name, access_token)

    # Create session
    session_id = secrets.token_urlsafe(32)
    session_timeout = int(os.getenv("SESSION_TIMEOUT", "3600"))

    user_sessions[session_id] = {
        "provider": provider_name,
        "access_token": access_token,
        "user_email": user_email,
        "expires_at": time.time() + session_timeout,
        "created_at": time.time()
    }

    # Log authentication
    print(f"🔐 {provider_name} OAuth successful - {user_email}")

    # Set session cookie
    response = RedirectResponse("/", status_code=302)
    response.set_cookie(
        "email_session",
        session_id,
        max_age=session_timeout,
        httponly=True,
        secure=True,
        samesite="lax"
    )

    return response


async def get_user_email(provider: str, access_token: str) -> str:
    """Get user's email from provider API."""

    provider_config = OAUTH_PROVIDERS[provider]
    userinfo_url = provider_config["userinfo_url"]

    async with aiohttp.ClientSession() as session:
        async with session.get(
            userinfo_url,
            headers={"Authorization": f"Bearer {access_token}"}
        ) as resp:
            if resp.status != 200:
                return "unknown@example.com"

            data = await resp.json()

            # Provider-specific email extraction
            if provider == "gmail":
                return data.get("email", "unknown@example.com")
            elif provider == "outlook":
                return data.get("mail") or data.get("userPrincipalName", "unknown@example.com")

            return "unknown@example.com"
```

### 4. Session Validation with Provider Support

**Updated tool to handle any provider:**

```python
@mcp.tool()
async def list_emails(
    folder: str = "INBOX",
    limit: int = 10,
    session_token: Optional[str] = None
) -> Dict[str, Any]:
    """List emails - works with any connected provider."""

    # Validate session
    if not session_token or session_token not in user_sessions:
        return {
            "success": False,
            "error": "Not authenticated. Please connect your email account.",
            "auth_urls": {
                "gmail": "/oauth/authorize?provider=gmail",
                "outlook": "/oauth/authorize?provider=outlook"
            }
        }

    session = user_sessions[session_token]

    # Check expiry
    if time.time() > session["expires_at"]:
        user_sessions.pop(session_token)
        return {
            "success": False,
            "error": "Session expired. Please re-authenticate.",
            "auth_urls": {
                "gmail": "/oauth/authorize?provider=gmail",
                "outlook": "/oauth/authorize?provider=outlook"
            }
        }

    # Configure provider based on session
    provider_type = session["provider"]

    await email_ops.configure_provider(provider_type, {
        "token": session["access_token"],
        "refresh_token": None,
        "client_id": os.getenv(
            OAUTH_PROVIDERS[provider_type]["client_id_env"]
        ),
        "client_secret": os.getenv(
            OAUTH_PROVIDERS[provider_type]["client_secret_env"]
        )
    })

    # Execute operation (provider-agnostic)
    return await email_ops.list_emails(folder, limit)
```

---

## Session Storage with Multiple Accounts

### Session Structure

```python
user_sessions = {
    "session_abc123": {
        "provider": "gmail",
        "access_token": "ya29.gmail...",
        "user_email": "alice@gmail.com",
        "expires_at": 1234567890.0,
        "created_at": 1234567000.0
    },
    "session_def456": {
        "provider": "outlook",
        "access_token": "eyJ0...outlook...",
        "user_email": "alice@company.com",
        "expires_at": 1234567891.0,
        "created_at": 1234567001.0
    }
}
```

### Multiple Sessions Per User

**If user connects both Gmail AND Outlook:**

```python
# Store sessions by user + provider
user_sessions = {
    "user_alice_gmail": {
        "provider": "gmail",
        "user_email": "alice@gmail.com",
        "access_token": "...",
        "expires_at": 1234567890.0
    },
    "user_alice_outlook": {
        "provider": "outlook",
        "user_email": "alice@company.com",
        "access_token": "...",
        "expires_at": 1234567891.0
    }
}
```

**UI shows both accounts:**
```
Select Email Account:
┌────────────────────────────────┐
│ 📧 alice@gmail.com (Gmail)     │
│    ✅ Active (45 min)           │
├────────────────────────────────┤
│ 📧 alice@company.com (Outlook) │
│    ✅ Active (20 min)           │
└────────────────────────────────┘
```

**User selects which account to use for each operation.**

---

## Provider Selection UI

### Frontend Component

```javascript
// ProviderSelection.jsx
function EmailProviderSelection() {
    const providers = [
        {
            id: 'gmail',
            name: 'Google / Gmail',
            description: 'Personal Gmail or Google Workspace',
            logo: '/static/google-logo.svg',
            color: '#4285F4'
        },
        {
            id: 'outlook',
            name: 'Microsoft / Outlook',
            description: 'Outlook.com or Microsoft 365',
            logo: '/static/microsoft-logo.svg',
            color: '#0078D4'
        }
    ];

    const handleConnect = (providerId) => {
        window.location.href = `/oauth/authorize?provider=${providerId}`;
    };

    return (
        <div className="provider-selection">
            <h2>Connect Your Email Account</h2>
            <div className="provider-grid">
                {providers.map(provider => (
                    <div
                        key={provider.id}
                        className="provider-card"
                        onClick={() => handleConnect(provider.id)}
                    >
                        <img src={provider.logo} alt={provider.name} />
                        <h3>{provider.name}</h3>
                        <p>{provider.description}</p>
                        <button>Connect</button>
                    </div>
                ))}
            </div>
        </div>
    );
}
```

### Connected Accounts Dashboard

```javascript
// ConnectedAccounts.jsx
function ConnectedAccounts() {
    const [accounts, setAccounts] = useState([]);

    useEffect(() => {
        // Fetch connected accounts from /api/accounts
        fetch('/api/accounts')
            .then(r => r.json())
            .then(setAccounts);
    }, []);

    const handleDisconnect = async (sessionId) => {
        await fetch(`/api/accounts/${sessionId}`, { method: 'DELETE' });
        // Refresh list
    };

    const handleReauth = (provider) => {
        window.location.href = `/oauth/authorize?provider=${provider}`;
    };

    return (
        <div className="connected-accounts">
            <h2>Connected Email Accounts</h2>
            {accounts.map(account => (
                <div key={account.session_id} className="account-card">
                    <div className="account-info">
                        <img src={`/static/${account.provider}-logo.svg`} />
                        <div>
                            <strong>{account.email}</strong>
                            <span>{account.provider}</span>
                        </div>
                    </div>
                    <div className="account-status">
                        {account.expired ? (
                            <>
                                <span className="status-expired">⚠️ Expired</span>
                                <button onClick={() => handleReauth(account.provider)}>
                                    Re-authenticate
                                </button>
                            </>
                        ) : (
                            <>
                                <span className="status-active">✅ Active</span>
                                <span className="time-left">
                                    {Math.floor(account.minutes_remaining)} min
                                </span>
                                <button onClick={() => handleDisconnect(account.session_id)}>
                                    Disconnect
                                </button>
                            </>
                        )}
                    </div>
                </div>
            ))}
            <button className="add-account" onClick={() => window.location.href = '/oauth/providers'}>
                + Connect Another Account
            </button>
        </div>
    );
}
```

---

## Azure AD / Microsoft 365 Setup

### For Corporate Outlook (Microsoft 365)

**1. Register App in Azure Portal**
- Go to: https://portal.azure.com/
- Azure Active Directory → App registrations
- Click "New registration"

**2. Configure App**
- Name: "Kamiwaza Email Tool"
- Supported account types:
  - **Personal Microsoft accounts only** → `consumers`
  - **Organization accounts only** → `organizations`
  - **Both** → `common` (recommended)
- Redirect URI: `https://kamiwaza.example.com/oauth/callback` (Web)

**3. API Permissions**
- Microsoft Graph → Delegated permissions:
  - `Mail.Read`
  - `Mail.ReadWrite`
  - `Mail.Send`
  - `User.Read`
- Click "Grant admin consent" (if organization)

**4. Client Secret**
- Certificates & secrets → New client secret
- Save the **Value** (shown once!)

**5. Configuration**
```bash
OAUTH_OUTLOOK_CLIENT_ID=<Application (client) ID>
OAUTH_OUTLOOK_CLIENT_SECRET=<Client secret value>
OAUTH_OUTLOOK_TENANT_ID=common  # Or specific tenant ID
```

### Tenant Types

```bash
# Personal Microsoft accounts only
OAUTH_OUTLOOK_TENANT_ID=consumers

# Organization accounts only (your company)
OAUTH_OUTLOOK_TENANT_ID=<your-tenant-id>

# Both personal and organizational (recommended)
OAUTH_OUTLOOK_TENANT_ID=common
```

---

## Google Workspace Setup

### For Corporate Gmail (Google Workspace)

**Same as personal Gmail setup**, but:

1. **Google Workspace Admin** creates OAuth app
2. **Admin console** → Security → API controls
3. **Manage domain-wide delegation** (if service account)
4. Users can authorize with their `@company.com` email

**Configuration** (same as personal Gmail):
```bash
OAUTH_GMAIL_CLIENT_ID=<Client ID>
OAUTH_GMAIL_CLIENT_SECRET=<Client secret>
```

OAuth flow works identically for both `@gmail.com` and `@company.com`.

---

## Provider-Specific Differences

### Gmail vs Outlook

| Feature | Gmail | Outlook |
|---------|-------|---------|
| **OAuth Endpoint** | accounts.google.com | login.microsoftonline.com |
| **Tenant Support** | N/A | Yes (common/consumers/org) |
| **Token Format** | JWT | JWT |
| **Token Lifetime** | 1 hour | 1 hour |
| **Refresh Tokens** | Optional (we don't use) | Optional (we don't use) |
| **Scopes** | gmail.* | Mail.* |
| **User Info API** | oauth2/v2/userinfo | graph.microsoft.com/me |

### Code Differences (Already Abstracted)

**Our providers.py already handles this!**

```python
# Gmail uses Gmail API
class GmailProvider(EmailProvider):
    async def list_emails(self, folder, limit):
        # Uses Gmail API
        service = build('gmail', 'v1', credentials=self.creds)
        results = service.users().messages().list(...)

# Outlook uses Microsoft Graph
class OutlookProvider(EmailProvider):
    async def list_emails(self, folder, limit):
        # Uses Graph API
        url = f"https://graph.microsoft.com/v1.0/me/mailFolders/{folder}/messages"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as resp:
                ...
```

**No changes needed!** The tool already supports both providers.

---

## Configuration Summary

### Complete Environment Setup

```bash
# ===== Gmail OAuth =====
OAUTH_GMAIL_CLIENT_ID=123...apps.googleusercontent.com
OAUTH_GMAIL_CLIENT_SECRET=GOCSPX-abc123...

# ===== Outlook OAuth =====
OAUTH_OUTLOOK_CLIENT_ID=456...
OAUTH_OUTLOOK_CLIENT_SECRET=def456...
OAUTH_OUTLOOK_TENANT_ID=common  # common/consumers/organizations/<tenant-id>

# ===== OAuth Config =====
OAUTH_REDIRECT_URI=https://kamiwaza.example.com/oauth/callback

# ===== Session Config =====
SESSION_TIMEOUT=3600  # 1 hour
SESSION_SECRET=<random-secret>

# ===== Security =====
COOKIE_SECURE=true
COOKIE_SAMESITE=lax
```

---

## Enterprise Deployment Scenarios

### Scenario 1: Gmail-Only Company

```bash
# Only configure Gmail
OAUTH_GMAIL_CLIENT_ID=...
OAUTH_GMAIL_CLIENT_SECRET=...

# Outlook disabled (UI won't show it)
```

### Scenario 2: Microsoft 365 Company

```bash
# Only configure Outlook
OAUTH_OUTLOOK_CLIENT_ID=...
OAUTH_OUTLOOK_CLIENT_SECRET=...
OAUTH_OUTLOOK_TENANT_ID=<company-tenant-id>

# Gmail disabled
```

### Scenario 3: Mixed Environment

```bash
# Configure both
OAUTH_GMAIL_CLIENT_ID=...
OAUTH_GMAIL_CLIENT_SECRET=...
OAUTH_OUTLOOK_CLIENT_ID=...
OAUTH_OUTLOOK_CLIENT_SECRET=...
OAUTH_OUTLOOK_TENANT_ID=common

# Users can connect either or both
```

---

## Testing Plan

### Test Cases

**1. Gmail Personal**
- User: `alice@gmail.com`
- Flow: Gmail OAuth → List emails → Send email
- Expected: ✅ Works

**2. Google Workspace**
- User: `alice@company.com`
- Flow: Gmail OAuth → List emails → Send email
- Expected: ✅ Works (same as personal)

**3. Outlook Personal**
- User: `bob@outlook.com`
- Flow: Outlook OAuth → List emails → Send email
- Expected: ✅ Works

**4. Microsoft 365**
- User: `bob@company.com`
- Flow: Outlook OAuth (org tenant) → List emails → Send email
- Expected: ✅ Works

**5. Multiple Accounts**
- User connects Gmail + Outlook
- Switch between accounts
- Send from each account
- Expected: ✅ Both work independently

**6. Session Expiry**
- Wait for timeout
- Try to list emails
- Expected: ✅ Error with re-auth prompt

**7. Mixed Providers After Restart**
- Connect Gmail and Outlook
- Restart container
- Try to use both
- Expected: ✅ Both require re-auth

---

## Migration from Manual Setup

### Old Way (Manual)
```bash
# User runs get_gmail_token.py
# Copies credentials
# Only Gmail supported
```

### New Way (OAuth)
```bash
# User clicks "Connect Gmail" OR "Connect Outlook"
# Authorizes via browser
# Both providers supported
# Can connect multiple accounts
```

---

## Future Extensions

### Additional Providers

**Yahoo Mail:**
```python
"yahoo": {
    "name": "Yahoo Mail",
    "auth_url": "https://api.login.yahoo.com/oauth2/request_auth",
    "token_url": "https://api.login.yahoo.com/oauth2/get_token",
    # ...
}
```

**ProtonMail:**
- Requires ProtonMail Bridge (IMAP/SMTP)
- Different authentication model

**Custom IMAP:**
- Username/password (less secure)
- App-specific passwords
- OAuth if supported

---

## Recommendation

**✅ Implement multi-provider OAuth**

**Phase 1: Core (3 days)**
- Provider registry system
- Gmail OAuth flow
- Outlook OAuth flow
- Session management with provider info

**Phase 2: UI (2 days)**
- Provider selection screen
- Connected accounts dashboard
- Account switching
- Re-authentication prompts

**Phase 3: Testing (2 days)**
- Test all provider combinations
- Test enterprise tenants
- Security testing

**Total: ~1 week for full multi-provider support**

**Benefits:**
- ✅ Works for Gmail companies
- ✅ Works for Microsoft 365 companies
- ✅ Works for mixed environments
- ✅ Users can connect multiple accounts
- ✅ Clean, secure architecture

Would you like me to proceed with implementing this?
