# Email MCP Tool - Implementation Summary

## What We're Building

A secure, multi-provider email tool that supports:
- ✅ **Gmail** (personal @gmail.com + Google Workspace @company.com)
- ✅ **Outlook** (personal @outlook.com + Microsoft 365 @company.com)
- ✅ **Multiple accounts** (users can connect both)
- ✅ **OAuth authentication** (no stored credentials)
- ✅ **Session-based** (1-hour timeout, in-memory only)

---

## User Experience

### Initial Connection

```
1. User opens Kamiwaza email tool
2. Sees: "Connect Your Email Account"
3. Choices:
   ┌────────────────────────────┐
   │  [ Google / Gmail ]        │
   │  [ Microsoft / Outlook ]   │
   └────────────────────────────┘
4. User clicks their provider
5. Redirected to provider's consent screen
6. User authorizes
7. Redirected back - ready to use!
```

### Using the Tool

```
Connected as: alice@company.com (Outlook)
Session expires in: 45 minutes

Actions:
• List emails
• Read email
• Send email
• Search emails
• Reply / Forward
• Delete email
```

### After Session Expires

```
⚠️ Session expired. Please re-authenticate.

[Re-connect Outlook] [Connect Different Account]
```

### Multiple Accounts

```
Your Connected Accounts:
┌──────────────────────────────────┐
│ 📧 alice@gmail.com               │
│    ✅ Active (45 min remaining)   │
│    [Use] [Disconnect]            │
├──────────────────────────────────┤
│ 📧 alice@company.com             │
│    ✅ Active (20 min remaining)   │
│    [Use] [Disconnect]            │
└──────────────────────────────────┘

[+ Connect Another Account]
```

---

## Security Model

### ✅ What's Secure

```
Credentials:           In-memory only (never disk)
Session Lifetime:      1 hour (configurable)
Container Restart:     All sessions cleared
Token Type:            Access token only (no refresh)
Re-authentication:     Required after timeout
CSRF Protection:       State tokens
XSS Protection:        HttpOnly cookies
```

### ❌ What We DON'T Do

```
❌ Store credentials in .env files
❌ Store refresh tokens
❌ Persist credentials across restarts
❌ Allow unlimited session lifetimes
❌ Share credentials between users
```

### Attack Surface

| Threat | Mitigation |
|--------|-----------|
| Container compromised | Max 1 hour exposure (then expires) |
| Credential theft | Nothing to steal (in-memory only) |
| Session hijacking | HttpOnly + Secure cookies + SameSite |
| Insider threat | Can't extract credentials (don't exist on disk) |
| Container restart | All sessions immediately invalidated |

---

## Architecture

### Components

```
┌─────────────────────────────────────┐
│  Kamiwaza Frontend                  │
│  • Provider selection UI            │
│  • Connected accounts dashboard     │
│  • Account switcher                 │
└─────────────┬───────────────────────┘
              │
              ↓
┌─────────────────────────────────────┐
│  Email MCP Tool                     │
│  • OAuth flow handler               │
│  • In-memory session store          │
│  • Provider-agnostic API            │
└─────────────┬───────────────────────┘
              │
       ┌──────┴──────┐
       ↓             ↓
┌────────────┐ ┌──────────────┐
│ Gmail API  │ │ Graph API    │
│ (Google)   │ │ (Microsoft)  │
└────────────┘ └──────────────┘
```

### Session Storage

```python
# In-memory only (cleared on restart)
user_sessions = {
    "session_abc123": {
        "provider": "gmail",
        "user_email": "alice@gmail.com",
        "access_token": "ya29...",
        "expires_at": timestamp,
        "created_at": timestamp
    },
    "session_def456": {
        "provider": "outlook",
        "user_email": "bob@company.com",
        "access_token": "eyJ0...",
        "expires_at": timestamp,
        "created_at": timestamp
    }
}
```

---

## Configuration

### Environment Variables

```bash
# ===== Gmail OAuth App =====
OAUTH_GMAIL_CLIENT_ID=123...apps.googleusercontent.com
OAUTH_GMAIL_CLIENT_SECRET=GOCSPX-abc123...

# ===== Outlook OAuth App =====
OAUTH_OUTLOOK_CLIENT_ID=456...
OAUTH_OUTLOOK_CLIENT_SECRET=def456...
OAUTH_OUTLOOK_TENANT_ID=common  # For all Microsoft accounts

# ===== OAuth Settings =====
OAUTH_REDIRECT_URI=https://kamiwaza.example.com/oauth/callback

# ===== Session Settings =====
SESSION_TIMEOUT=3600  # 1 hour
SESSION_SECRET=<random-secret-for-cookie-signing>

# ===== Security =====
COOKIE_SECURE=true  # HTTPS only
COOKIE_SAMESITE=lax  # CSRF protection
```

### Deployment Scenarios

**Gmail-Only Company:**
```bash
# Only configure Gmail
OAUTH_GMAIL_CLIENT_ID=...
OAUTH_GMAIL_CLIENT_SECRET=...
# Outlook UI hidden
```

**Microsoft 365 Company:**
```bash
# Only configure Outlook
OAUTH_OUTLOOK_CLIENT_ID=...
OAUTH_OUTLOOK_CLIENT_SECRET=...
OAUTH_OUTLOOK_TENANT_ID=<company-tenant>
# Gmail UI hidden
```

**Mixed Environment:**
```bash
# Configure both
OAUTH_GMAIL_CLIENT_ID=...
OAUTH_GMAIL_CLIENT_SECRET=...
OAUTH_OUTLOOK_CLIENT_ID=...
OAUTH_OUTLOOK_CLIENT_SECRET=...
OAUTH_OUTLOOK_TENANT_ID=common
# Users see both options
```

---

## Implementation Plan

### Phase 1: OAuth Core (2-3 days)

**Endpoints:**
- `GET /oauth/authorize?provider=gmail|outlook`
- `GET /oauth/callback?code=...&state=...`
- `GET /api/accounts` (list connected accounts)
- `DELETE /api/accounts/:session_id` (disconnect)

**Features:**
- Provider registry system
- State token generation/validation
- Token exchange with Google/Microsoft
- In-memory session store
- Session cleanup background task
- CSRF protection

**Files:**
- `src/tool_email_mcp/oauth.py` (new)
- `src/tool_email_mcp/session.py` (new)
- `src/tool_email_mcp/server.py` (updated)

### Phase 2: Session Authentication (1-2 days)

**Middleware:**
- Extract session from cookie
- Validate session expiry
- Inject provider context into tools

**Tool Updates:**
- All tools require valid session
- Return auth URLs when unauthenticated
- Support provider switching

**Files:**
- `src/tool_email_mcp/middleware.py` (new)
- `src/tool_email_mcp/server.py` (tool decorators updated)

### Phase 3: UI Integration (2-3 days)

**Frontend Components:**
- Provider selection page
- Connected accounts dashboard
- Account switcher dropdown
- Re-authentication prompts
- Session expiry warnings

**API Integration:**
- Fetch connected accounts
- Trigger OAuth flow
- Switch active account
- Disconnect accounts

**Files:**
- `frontend/ProviderSelection.jsx` (new)
- `frontend/ConnectedAccounts.jsx` (new)
- `frontend/AccountSwitcher.jsx` (new)

### Phase 4: Testing (2 days)

**Test Cases:**
1. Gmail personal authentication
2. Google Workspace authentication
3. Outlook personal authentication
4. Microsoft 365 authentication
5. Multiple accounts (Gmail + Outlook)
6. Session expiry
7. Container restart (sessions cleared)
8. Account switching
9. Concurrent users
10. Security testing (CSRF, XSS, session hijacking)

**Files:**
- `tests/test_oauth.py` (new)
- `tests/test_sessions.py` (new)
- `tests/test_multi_provider.py` (new)

### Phase 5: Documentation (1 day)

**User Guides:**
- OAuth setup for Gmail
- OAuth setup for Outlook
- Multi-account usage
- Troubleshooting

**Admin Guides:**
- Azure AD app registration
- Google Cloud Console setup
- Environment configuration
- Security considerations

---

## Timeline

```
Week 1:
├─ Days 1-3: OAuth core + session auth
├─ Days 4-5: UI integration
└─ Day 5: Initial testing

Week 2:
├─ Days 1-2: Comprehensive testing
├─ Day 3: Documentation
├─ Days 4-5: Bug fixes + polish
└─ End of week: Ready for production
```

**Total: ~2 weeks for production-ready multi-provider OAuth**

---

## Dependencies

### Python (Backend)

```txt
# OAuth and HTTP
aiohttp>=3.9.0
python-jose>=3.3.0
itsdangerous>=2.1.0

# Google API (already have)
google-auth>=2.25.0
google-auth-httplib2>=0.2.0
google-api-python-client>=2.110.0

# Microsoft Graph (already have)
msal>=1.26.0
```

### JavaScript (Frontend)

```json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-router-dom": "^6.20.0",
    "axios": "^1.6.0"
  }
}
```

---

## Success Criteria

### Functional Requirements

- ✅ Users can authenticate with Gmail
- ✅ Users can authenticate with Outlook
- ✅ Users can connect multiple accounts
- ✅ Sessions expire after 1 hour
- ✅ Sessions cleared on container restart
- ✅ All email operations work with both providers
- ✅ Users can switch between accounts
- ✅ Clear error messages and re-auth prompts

### Security Requirements

- ✅ No credentials stored on disk
- ✅ In-memory sessions only
- ✅ CSRF protection (state tokens)
- ✅ XSS protection (HttpOnly cookies)
- ✅ Session hijacking mitigation (Secure + SameSite)
- ✅ Audit logging (all auth events)
- ✅ Automatic cleanup (expired sessions)

### User Experience

- ✅ One-click provider selection
- ✅ Clear session status display
- ✅ Intuitive account switching
- ✅ Graceful error handling
- ✅ Mobile-responsive UI

---

## Rollout Plan

### Phase 1: Internal Testing
- Deploy to staging environment
- Test with Kamiwaza team Gmail + Outlook accounts
- Validate all flows
- Fix any issues

### Phase 2: Beta Users
- Invite 5-10 beta users
- Mix of Gmail and Outlook users
- Gather feedback
- Iterate on UX

### Phase 3: Production
- Deploy to production
- Update documentation
- Announce to users
- Monitor authentication metrics

### Phase 4: Monitoring
- Track authentication success rate
- Monitor session lifetimes
- Analyze provider usage (Gmail vs Outlook)
- Identify friction points

---

## Migration from Manual Setup

### Deprecation Plan

**Old manual setup:**
```bash
# DEPRECATED - Will be removed
python get_gmail_token.py
# Copy credentials to .env
```

**New OAuth setup:**
```bash
# Just click "Connect Gmail" or "Connect Outlook"
# No manual credential copying
```

**Timeline:**
- Week 1: OAuth available (manual still works)
- Week 2-4: Both methods supported
- Week 5+: Manual method deprecated, warnings shown
- Week 8+: Manual method removed

---

## Cost Analysis

### Development Cost

- OAuth implementation: ~80 hours
- UI development: ~40 hours
- Testing: ~20 hours
- Documentation: ~10 hours
- **Total: ~150 hours (~3-4 weeks)**

### Operational Cost

**OAuth Apps:**
- Google Cloud Console: Free (under quota)
- Azure AD app registration: Free
- OAuth API calls: Free (within limits)

**Compute:**
- No additional resources needed
- Same container as current design

### Security Value

**Risk Reduction:**
- Credential theft: High → Low
- Session hijacking: High → Medium
- Insider threat: High → Low
- Compliance: Partial → Full

**Estimated risk reduction value: $100K+/year**
(Based on average cost of credential breach)

---

## Open Questions

1. **Session Timeout:**
   - Default 1 hour OK?
   - Different timeouts for Gmail vs Outlook?
   - Different timeouts for personal vs corporate?

2. **Multi-Account:**
   - Allow unlimited accounts?
   - Limit to N accounts per user?
   - Automatic cleanup of unused accounts?

3. **Remember Me:**
   - Add "Remember me" option for longer sessions?
   - Security implications?

4. **Service Accounts:**
   - Different flow for automation/bots?
   - API key authentication for services?

5. **Integration:**
   - OAuth managed by tool or Kamiwaza core?
   - Token storage in Kamiwaza DB?
   - User context passed from Kamiwaza?

---

## Recommendation

**✅ Proceed with multi-provider OAuth implementation**

**Rationale:**
1. **Security:** Eliminates credential storage risk
2. **Flexibility:** Supports Gmail AND Outlook
3. **User Experience:** One-click authentication
4. **Compliance:** Meets enterprise security standards
5. **Scalability:** Works for any size deployment

**Next Steps:**
1. Get approval on approach
2. Finalize configuration (session timeout, etc.)
3. Start Phase 1 implementation (OAuth core)
4. Iterate based on testing feedback
5. Launch to production

**Timeline: ~2 weeks to production-ready**

---

## Questions for You

1. **Which approach do you prefer?**
   - Option A: Tool manages OAuth (faster, independent)
   - Option B: Kamiwaza manages OAuth (cleaner, more integrated)

2. **Session timeout preference?**
   - 30 minutes (high security)
   - 1 hour (balanced) ← Recommended
   - 2 hours (convenience)
   - Configurable per deployment

3. **Multi-account priority?**
   - Phase 1 (must-have)
   - Phase 2 (nice-to-have)
   - Future enhancement

4. **Provider priority?**
   - Gmail + Outlook (Phase 1) ← Recommended
   - Gmail only first, Outlook later
   - Add Yahoo/others?

Ready to start implementing?
