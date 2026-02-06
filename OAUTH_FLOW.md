# Secure OAuth Flow Implementation

## Security Requirement

**No persistent credential storage.** Users must authenticate via OAuth each time they want to use the email tool.

## Design Goals

1. ✅ **No stored credentials** - Tokens only in memory during session
2. ✅ **Browser-based auth** - User authorizes via Google OAuth consent screen
3. ✅ **Session-based** - Short-lived sessions (configurable timeout)
4. ✅ **Multi-user support** - Each user has isolated session
5. ✅ **Audit trail** - Log all authentication events

---

## Architecture Overview

```
┌─────────────┐
│   User      │
│  (Browser)  │
└─────┬───────┘
      │
      │ 1. Click "Connect Gmail"
      ↓
┌─────────────────────────────────┐
│  Kamiwaza UI                    │
│  https://kamiwaza.example.com   │
└─────────────┬───────────────────┘
              │
              │ 2. Redirect to OAuth
              ↓
┌─────────────────────────────────┐
│  Google OAuth Consent Screen    │
│  accounts.google.com/o/oauth2   │
└─────────────┬───────────────────┘
              │
              │ 3. User authorizes
              ↓
┌─────────────────────────────────┐
│  Callback Handler               │
│  /oauth/callback                │
└─────────────┬───────────────────┘
              │
              │ 4. Exchange code for token
              ↓
┌─────────────────────────────────┐
│  Email MCP Tool                 │
│  In-Memory Session Store        │
│  (60 min timeout)               │
└─────────────┬───────────────────┘
              │
              │ 5. Make email requests
              ↓
┌─────────────────────────────────┐
│  Gmail API                      │
│  gmail.googleapis.com           │
└─────────────────────────────────┘
```

---

## OAuth Flow Implementation

### Phase 1: Initiate OAuth (Redirect to Google)

**User Action:** Clicks "Connect Gmail" in Kamiwaza UI

**Backend:**
```python
# New endpoint in server.py
@mcp.custom_route("/oauth/authorize", methods=["GET"])
async def oauth_authorize(request: Request) -> RedirectResponse:
    """Initiate OAuth flow - redirect to Google consent screen."""

    # Get OAuth config from environment
    client_id = os.getenv("OAUTH_GMAIL_CLIENT_ID")
    redirect_uri = os.getenv("OAUTH_REDIRECT_URI")

    if not client_id:
        return JSONResponse(
            {"error": "OAuth not configured"},
            status_code=500
        )

    # Generate state token for CSRF protection
    state = secrets.token_urlsafe(32)
    session_id = request.cookies.get("kamiwaza_session")

    # Store state temporarily (in-memory, 5 min expiry)
    oauth_states[state] = {
        "session_id": session_id,
        "created_at": time.time()
    }

    # Build Google OAuth URL
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join([
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/gmail.send",
            "https://www.googleapis.com/auth/gmail.modify"
        ]),
        "state": state,
        "access_type": "online",  # ← No refresh token!
        "prompt": "consent"  # ← Always show consent screen
    }

    oauth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"

    return RedirectResponse(oauth_url)
```

**Key Security Features:**
- `access_type: "online"` - No refresh token issued (short-lived only)
- `prompt: "consent"` - User must re-authorize each time
- State token - CSRF protection
- No credential storage

### Phase 2: Handle OAuth Callback

**User Action:** Authorizes on Google, redirected back

**Backend:**
```python
@mcp.custom_route("/oauth/callback", methods=["GET"])
async def oauth_callback(request: Request) -> Response:
    """Handle OAuth callback from Google."""

    code = request.query_params.get("code")
    state = request.query_params.get("state")
    error = request.query_params.get("error")

    # Check for errors
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

    state_data = oauth_states.pop(state)  # Use once

    # Check state expiry (5 minutes)
    if time.time() - state_data["created_at"] > 300:
        return JSONResponse(
            {"error": "State token expired"},
            status_code=400
        )

    # Exchange authorization code for access token
    client_id = os.getenv("OAUTH_GMAIL_CLIENT_ID")
    client_secret = os.getenv("OAUTH_GMAIL_CLIENT_SECRET")
    redirect_uri = os.getenv("OAUTH_REDIRECT_URI")

    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code"
            }
        ) as resp:
            if resp.status != 200:
                return JSONResponse(
                    {"error": "Token exchange failed"},
                    status_code=500
                )

            token_data = await resp.json()

    # Create session with short-lived token
    session_id = secrets.token_urlsafe(32)
    session_timeout = int(os.getenv("SESSION_TIMEOUT", "3600"))  # 1 hour default

    # Store in-memory (expires automatically)
    user_sessions[session_id] = {
        "access_token": token_data["access_token"],
        "expires_at": time.time() + session_timeout,
        "created_at": time.time(),
        "provider": "gmail"
    }

    # Log authentication event
    print(f"🔐 OAuth authentication successful - Session ID: {session_id[:8]}...")

    # Set session cookie and redirect
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
```

**Key Security Features:**
- State token verification (CSRF)
- State expiry (5 minutes)
- Session timeout (configurable, default 1 hour)
- HttpOnly cookies (XSS protection)
- Secure cookies (HTTPS only)
- No token refresh

### Phase 3: Use Session for Email Operations

**User Action:** Lists emails, sends email, etc.

**Backend:**
```python
# Modified tool to require session authentication
@mcp.tool()
async def list_emails(
    folder: str = "INBOX",
    limit: int = 10,
    session_token: Optional[str] = None  # ← NEW: passed from cookie
) -> Dict[str, Any]:
    """List emails from specified folder.

    Args:
        folder: Folder name (default: INBOX)
        limit: Maximum emails to return
        session_token: Session token from cookie (auto-extracted)

    Returns:
        Dict with email list or error
    """

    # Validate session
    if not session_token or session_token not in user_sessions:
        return {
            "success": False,
            "error": "Not authenticated. Please authenticate via OAuth.",
            "auth_url": "/oauth/authorize"
        }

    session = user_sessions[session_token]

    # Check session expiry
    if time.time() > session["expires_at"]:
        user_sessions.pop(session_token)  # Clean up
        return {
            "success": False,
            "error": "Session expired. Please re-authenticate.",
            "auth_url": "/oauth/authorize"
        }

    # Configure provider with session token
    await email_ops.configure_provider("gmail", {
        "token": session["access_token"],
        "refresh_token": None,  # No refresh token
        "client_id": os.getenv("OAUTH_GMAIL_CLIENT_ID"),
        "client_secret": os.getenv("OAUTH_GMAIL_CLIENT_SECRET")
    })

    # Execute operation
    return await email_ops.list_emails(folder, limit)
```

**Middleware to Extract Session:**
```python
# Add middleware to extract session from cookie
@mcp.custom_route("/mcp", methods=["POST"])
async def mcp_with_session(request: Request) -> Response:
    """MCP endpoint with session authentication."""

    # Extract session token from cookie
    session_token = request.cookies.get("email_session")

    # Parse MCP request
    body = await request.json()
    tool_name = body.get("tool")
    arguments = body.get("arguments", {})

    # Inject session token into arguments
    arguments["session_token"] = session_token

    # Call the appropriate tool
    # (FastMCP will handle routing to the decorated function)
    # ...
```

---

## Session Management

### In-Memory Session Store

```python
# Global session store (in-memory)
user_sessions: Dict[str, Dict[str, Any]] = {}
oauth_states: Dict[str, Dict[str, Any]] = {}

# Background task to clean expired sessions
async def cleanup_expired_sessions():
    """Remove expired sessions every minute."""
    while True:
        await asyncio.sleep(60)  # Check every minute

        now = time.time()
        expired = [
            sid for sid, session in user_sessions.items()
            if now > session["expires_at"]
        ]

        for sid in expired:
            print(f"🗑️  Cleaning expired session: {sid[:8]}...")
            user_sessions.pop(sid)

        # Clean expired OAuth states (5 min expiry)
        expired_states = [
            state for state, data in oauth_states.items()
            if now - data["created_at"] > 300
        ]

        for state in expired_states:
            oauth_states.pop(state)
```

### Session Properties

```python
{
    "access_token": "ya29.a0...",  # Short-lived (1 hour from Google)
    "expires_at": 1234567890.0,    # Enforced by tool
    "created_at": 1234567000.0,    # For auditing
    "provider": "gmail"             # Or "outlook"
}
```

**Security Characteristics:**
- ✅ **In-memory only** - Lost on restart (feature, not bug!)
- ✅ **Automatic expiry** - Background task cleans up
- ✅ **No persistence** - Never written to disk
- ✅ **Session timeout** - Configurable (default 1 hour)

---

## User Experience Flow

### First Use (Authentication Required)

1. **User opens Kamiwaza app**
2. **User navigates to email tool**
3. **Tool shows:** "Connect your Gmail account"
4. **User clicks "Connect Gmail"**
5. **Redirected to Google OAuth consent screen**
6. **User reviews permissions:**
   - Read emails
   - Send emails
   - Modify emails (mark read, delete)
7. **User clicks "Allow"**
8. **Redirected back to Kamiwaza**
9. **Tool is now ready** - can list/send emails

### During Session (Authenticated)

1. **User lists emails** - Works normally
2. **User sends email** - Works normally
3. **User searches** - Works normally
4. **Session timeout: 1 hour** (configurable)

### After Session Expires

1. **User tries to list emails**
2. **Tool returns:** "Session expired. Please re-authenticate."
3. **User clicks "Re-authenticate"**
4. **Redirected to Google OAuth again**
5. **User re-authorizes**
6. **New session created**

### After Container Restart

1. **All sessions cleared** (in-memory storage)
2. **User tries to use tool**
3. **Tool returns:** "Not authenticated. Please authenticate."
4. **User authenticates via OAuth**
5. **Fresh session created**

---

## Configuration

### Environment Variables

```bash
# OAuth Application Credentials (safe to store)
OAUTH_GMAIL_CLIENT_ID=123...apps.googleusercontent.com
OAUTH_GMAIL_CLIENT_SECRET=GOCSPX-abc123...

# OAuth Redirect URI
OAUTH_REDIRECT_URI=https://kamiwaza.example.com/oauth/callback

# Session Configuration
SESSION_TIMEOUT=3600  # 1 hour (in seconds)
SESSION_CLEANUP_INTERVAL=60  # Clean every 60 seconds

# Session Security
SESSION_SECRET=random_secret_for_signing_cookies
COOKIE_SECURE=true  # HTTPS only
COOKIE_SAMESITE=lax  # CSRF protection
```

### Google Cloud Console Setup

**Different from manual setup:**

1. **OAuth Client Type:** "Web application" (not Desktop)
2. **Authorized Redirect URIs:** Add your callback URL
   - Example: `https://kamiwaza.example.com/oauth/callback`
   - For dev: `http://localhost:8000/oauth/callback`
3. **OAuth Consent Screen:** Production mode (not testing)

---

## Security Analysis

### What's Protected ✅

1. **No credential persistence** - Tokens never stored on disk
2. **Short-lived sessions** - Expire after timeout
3. **Memory-only storage** - Lost on restart (by design)
4. **CSRF protection** - State tokens verify origin
5. **XSS protection** - HttpOnly cookies
6. **Session isolation** - Each user has separate session
7. **Audit trail** - All auth events logged

### Attack Scenarios

**Scenario 1: Container compromised**
- ✅ Attacker gets current sessions (expire in <1 hour)
- ✅ No long-lived credentials to steal
- ✅ Sessions invalid after container restart

**Scenario 2: Session hijacking**
- ✅ HttpOnly cookies prevent JavaScript access
- ✅ Secure flag prevents HTTP interception
- ✅ SameSite prevents CSRF
- ⚠️ Still vulnerable to XSS on Kamiwaza domain (needs CSP)

**Scenario 3: Insider threat**
- ✅ Can't extract long-lived tokens (don't exist)
- ✅ Can only access emails during active session
- ✅ Audit log shows who authenticated when

**Scenario 4: Container restart**
- ✅ All sessions immediately invalidated
- ✅ Users must re-authenticate
- ✅ No credential recovery possible

---

## Multi-User Support

### Per-User Sessions

Each user gets isolated session:

```python
user_sessions = {
    "abc123...": {  # Alice's session
        "access_token": "ya29.alice...",
        "expires_at": 1234567890.0,
        "user_email": "alice@company.com"  # From Google userinfo
    },
    "def456...": {  # Bob's session
        "access_token": "ya29.bob...",
        "expires_at": 1234567891.0,
        "user_email": "bob@company.com"
    }
}
```

**Session Cookie:**
```
Set-Cookie: email_session=abc123...; HttpOnly; Secure; SameSite=Lax; Max-Age=3600
```

**Key Points:**
- ✅ Each cookie is unique per user
- ✅ Alice's cookie can't access Bob's session
- ✅ Sessions expire independently
- ✅ No cross-user contamination

---

## Implementation Checklist

### Phase 1: OAuth Flow (Core)
- [ ] Add `/oauth/authorize` endpoint (initiate flow)
- [ ] Add `/oauth/callback` endpoint (handle callback)
- [ ] Implement state token generation/verification
- [ ] Implement token exchange with Google
- [ ] Create in-memory session store
- [ ] Add session cleanup background task

### Phase 2: Session Authentication
- [ ] Add session extraction from cookies
- [ ] Modify all MCP tools to require session
- [ ] Add session validation logic
- [ ] Add session expiry checks
- [ ] Return auth URLs when unauthenticated

### Phase 3: UI Integration
- [ ] Add "Connect Gmail" button in Kamiwaza UI
- [ ] Add "Re-authenticate" prompt on expiry
- [ ] Show session status (authenticated/not)
- [ ] Add "Disconnect" button (clear session)

### Phase 4: Security Hardening
- [ ] Add Content-Security-Policy headers
- [ ] Implement rate limiting on OAuth endpoints
- [ ] Add brute-force protection
- [ ] Log all authentication events
- [ ] Add session enumeration prevention

### Phase 5: Testing
- [ ] Test OAuth flow end-to-end
- [ ] Test session expiry
- [ ] Test container restart (sessions cleared)
- [ ] Test concurrent users
- [ ] Security audit

---

## Dependencies to Add

```txt
# requirements.txt additions
aiohttp>=3.9.0           # For OAuth token exchange
itsdangerous>=2.1.0      # For secure session signing
python-jose>=3.3.0       # For JWT if using signed sessions
```

---

## Estimated Implementation Effort

- **Phase 1 (OAuth Flow):** 1 day
- **Phase 2 (Session Auth):** 1 day
- **Phase 3 (UI Integration):** 1 day
- **Phase 4 (Security Hardening):** 1 day
- **Phase 5 (Testing):** 1 day

**Total:** ~1 week for secure OAuth implementation

---

## Alternative: Kamiwaza-Managed Sessions

Instead of tool managing sessions, Kamiwaza could handle it:

### Architecture

```
┌─────────────────────────────────────┐
│  Kamiwaza Backend                   │
│  - Manages OAuth flow               │
│  - Stores encrypted tokens in DB    │
│  - Passes tokens to tools via       │
│    user context in MCP requests     │
└─────────────────────────────────────┘
         │
         │ MCP Request with user context:
         │ {
         │   "tool": "list_emails",
         │   "arguments": {...},
         │   "context": {
         │     "gmail_token": "ya29...",
         │     "user_id": "alice"
         │   }
         │ }
         ↓
┌─────────────────────────────────────┐
│  Email MCP Tool                     │
│  - Receives token from Kamiwaza     │
│  - No session management            │
│  - Stateless operation              │
└─────────────────────────────────────┘
```

**Pros:**
- ✅ Centralized authentication
- ✅ Tool is simpler (stateless)
- ✅ Better integration with Kamiwaza RBAC
- ✅ Single OAuth app for all tools

**Cons:**
- ❌ Requires Kamiwaza core changes
- ❌ Kamiwaza stores tokens (encrypted, but still stored)
- ❌ More complex integration

---

## Recommendation

**For maximum security:** Implement OAuth flow in the tool with in-memory sessions.

**Key Security Benefits:**
1. No persistent storage of any kind
2. Sessions expire automatically
3. Container restart clears all sessions
4. User must re-authorize after timeout
5. Audit trail of all authentications

**Trade-off:**
- Users must re-authenticate after session timeout (default: 1 hour)
- Users must re-authenticate after container restart
- This is a **feature**, not a bug - it's the secure behavior you requested!

Would you like me to proceed with implementing the OAuth flow?
