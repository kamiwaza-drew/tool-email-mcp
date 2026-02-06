# Security Decision: No Persistent Credentials

## The Problem with Previous Design

The initial design had credentials persisting in:
- ❌ Environment variables (refresh tokens)
- ❌ Container memory across restarts
- ❌ Long-lived refresh tokens

**Security Risks:**
1. Container compromise → long-lived credential theft
2. Insider access → credential extraction
3. No forced re-authentication
4. Credentials survive container restart

---

## New Secure Design

### ✅ No Credential Persistence

**What this means:**
- Tokens stored **in-memory only** during active session
- Sessions expire after timeout (default: 1 hour)
- Container restart → all sessions cleared
- Users must re-authenticate via OAuth

**User Experience:**
1. User clicks "Connect Gmail"
2. Redirected to Google OAuth consent
3. User authorizes
4. Session valid for 1 hour (configurable)
5. After timeout: Must re-authenticate
6. After container restart: Must re-authenticate

---

## Security Benefits

### Before (Persistent Credentials)
```
User authenticates once
  ↓
Refresh token stored in .env
  ↓
Container restarts with token
  ↓
Token valid for months/years
  ↓
If compromised: Long-term access
```

### After (Session-Based OAuth)
```
User authenticates
  ↓
Access token in memory (1 hour)
  ↓
Session expires
  ↓
User must re-authenticate
  ↓
If compromised: Max 1 hour exposure
```

---

## Attack Surface Comparison

| Scenario | With Persistent Tokens | With Session OAuth |
|----------|----------------------|-------------------|
| **Container compromised** | ❌ Attacker gets refresh token (months) | ✅ Attacker gets session token (max 1 hour) |
| **Insider threat** | ❌ Can extract refresh token from env | ✅ Can only access during session |
| **Container restart** | ❌ Credentials still valid | ✅ All sessions invalidated |
| **Token leaked in logs** | ❌ Long-lived credential exposed | ✅ Short-lived token (expires soon) |
| **Stale containers** | ❌ Forgotten containers with valid tokens | ✅ Sessions expire automatically |

---

## Implementation Status

### ✅ Completed (Secure Foundation)

1. **Removed credential persistence code:**
   - No auto-configuration from env vars
   - No refresh token storage
   - Clean docker-compose.yml

2. **Documentation created:**
   - `OAUTH_FLOW.md` - Complete implementation guide
   - `SECURITY_DECISION.md` - This document
   - Security rationale documented

### ⏳ To Implement (OAuth Flow)

**Phase 1: Core OAuth (1 day)**
- Add `/oauth/authorize` endpoint
- Add `/oauth/callback` endpoint
- State token CSRF protection
- Token exchange with Google
- In-memory session store

**Phase 2: Session Management (1 day)**
- Session extraction from cookies
- Session validation on all tools
- Automatic session expiry
- Background cleanup task

**Phase 3: UI Integration (1 day)**
- "Connect Gmail" button
- Session status display
- Re-authentication prompts
- Disconnect functionality

**Phase 4: Security Hardening (1 day)**
- CSP headers
- Rate limiting
- Audit logging
- Security testing

**Total: ~4 days implementation + 1 day testing**

---

## Configuration (Secure)

### What Gets Stored in Environment

```bash
# OAuth Application Credentials (public, safe to store)
OAUTH_GMAIL_CLIENT_ID=123...apps.googleusercontent.com
OAUTH_GMAIL_CLIENT_SECRET=GOCSPX-abc123...

# OAuth Redirect URI
OAUTH_REDIRECT_URI=https://kamiwaza.example.com/oauth/callback

# Session Configuration (not credentials!)
SESSION_TIMEOUT=3600  # 1 hour
```

**Key Point:** These are OAuth **application** credentials (like API keys), not user credentials. They're safe to store and necessary for the OAuth flow.

### What NEVER Gets Stored

```bash
# ❌ NEVER stored:
GMAIL_REFRESH_TOKEN=...     # User's refresh token
GMAIL_ACCESS_TOKEN=...      # User's access token
USER_PASSWORD=...           # Never touch passwords
```

---

## User Experience Impact

### Current Manual Flow (Insecure)
```
1. User runs get_gmail_token.py
2. Copies credentials into .env
3. Credentials persist forever
4. User never sees Gmail again
```

**Problems:**
- Credentials copied/pasted (can leak)
- Stored in plaintext files
- Persist indefinitely
- No clear revocation

### New OAuth Flow (Secure)
```
1. User clicks "Connect Gmail" in UI
2. Redirected to Google
3. Authorizes
4. Redirected back, ready to use
5. After 1 hour: Re-authenticate
```

**Benefits:**
- No credential copying
- No file storage
- Automatic expiry
- Clear consent screen

### Frequency of Re-Authentication

**Default: Every 1 hour**

Configurable via `SESSION_TIMEOUT`:
```bash
SESSION_TIMEOUT=3600   # 1 hour (default)
SESSION_TIMEOUT=7200   # 2 hours
SESSION_TIMEOUT=1800   # 30 minutes (high security)
```

**Also triggers on:**
- Container restart
- Service restart
- Kamiwaza system upgrade

**Trade-off:**
- More frequent auth = More secure
- Less frequent auth = Better UX

For security-conscious deployments, **1 hour is appropriate**.

---

## Compliance Considerations

### NIST Cybersecurity Framework

✅ **PR.AC-1:** Identities and credentials are issued, managed, verified, revoked, and audited
- OAuth provides identity verification
- Sessions are revoked on expiry
- All authentications logged

✅ **PR.AC-7:** Users, devices, and other assets are authenticated
- OAuth ensures user authentication
- No stored credentials to steal

✅ **PR.DS-1:** Data-at-rest is protected
- No credentials at rest (in-memory only)
- Sessions cleared on restart

✅ **DE.CM-3:** Personnel activity is monitored
- OAuth events logged
- Session access audited

### FedRAMP Moderate

✅ **AC-2:** Account Management
- Sessions managed with expiry

✅ **AC-7:** Unsuccessful Login Attempts
- Can implement rate limiting on OAuth

✅ **IA-5:** Authenticator Management
- OAuth tokens managed by Google
- Short-lived sessions

✅ **SC-12:** Cryptographic Key Establishment
- OAuth flow uses industry-standard crypto
- No key storage in tool

---

## Risk Analysis

### Risk: User Friction (Re-authentication)

**Likelihood:** High
**Impact:** Low (annoyance, not harm)
**Mitigation:**
- Clear messaging: "Re-authentication required for security"
- Session timeout configurable per deployment
- UI makes re-auth one-click

### Risk: Session Timeout During Long Operation

**Likelihood:** Low
**Impact:** Medium (user must retry)
**Mitigation:**
- Extend timeout for specific operations
- Return clear error: "Session expired, please re-authenticate"
- Auto-redirect to OAuth flow

### Risk: Container Restart Clears Sessions

**Likelihood:** Medium (during updates/maintenance)
**Impact:** Low (users re-authenticate)
**Mitigation:**
- Announce maintenance windows
- Users re-authenticate after restart (by design)

### Risk: OAuth Flow Failure

**Likelihood:** Low
**Impact:** High (can't access email)
**Mitigation:**
- Comprehensive error messages
- Fallback to manual configuration (if needed)
- Health check shows OAuth status

---

## Migration Plan

### Current Users (Manual Setup)

**If you've already used the tool with manual credentials:**

1. **Stop using environment variable credentials**
   ```bash
   # Remove from .env:
   # GMAIL_REFRESH_TOKEN=...
   # GMAIL_CLIENT_ID=...
   # GMAIL_CLIENT_SECRET=...
   ```

2. **Wait for OAuth implementation**
   - Target: ~1 week development

3. **Use new OAuth flow**
   - Click "Connect Gmail" in UI
   - Authorize via browser
   - Start using tool

### New Users

**Wait for OAuth implementation before first use.**

Do NOT use the manual setup guide - it will be deprecated.

---

## Future Enhancements

### Optional: Kamiwaza-Managed Tokens

If Kamiwaza core supports it, tokens could be managed centrally:

**Benefits:**
- Seamless multi-tool authentication
- Centralized revocation
- Better integration with RBAC

**Implementation:**
- Kamiwaza handles OAuth flow
- Stores encrypted tokens in database
- Passes tokens to tools via MCP context

**Timeline:** Requires Kamiwaza core development

---

## Decision Summary

✅ **Approved:** No persistent credential storage
✅ **Approved:** Session-based OAuth authentication
✅ **Approved:** In-memory session store only
✅ **Approved:** Mandatory re-authentication on timeout
✅ **Approved:** Sessions cleared on container restart

❌ **Rejected:** Environment variable credential storage
❌ **Rejected:** Refresh token persistence
❌ **Rejected:** Automatic credential loading
❌ **Rejected:** Long-lived access without re-auth

---

## Next Steps

### Immediate (No Code)
1. ✅ Document security decision (this file)
2. ✅ Update docker-compose.yml (removed credential env vars)
3. ✅ Update server.py (removed auto-configuration)

### Phase 1: Implementation (1 week)
1. Implement OAuth flow (OAUTH_FLOW.md)
2. Add session management
3. Integrate with UI
4. Security hardening
5. Testing

### Phase 2: Deployment
1. Update Kamiwaza Tool Shed listing
2. Add OAuth setup instructions
3. Announce to users
4. Deprecate manual setup guide

### Phase 3: Monitoring
1. Track authentication events
2. Monitor session lifetimes
3. Analyze user friction
4. Adjust timeout if needed

---

## Questions?

**Q: Why not just use refresh tokens securely?**
A: Refresh tokens are long-lived (months/years). Even if encrypted, they're a persistent credential. If the encryption key is compromised, so are all tokens.

**Q: What if users complain about re-authenticating?**
A: Security > convenience. We can adjust `SESSION_TIMEOUT` if needed, but we should not sacrifice security for convenience.

**Q: Can we make this optional?**
A: No. Security must be mandatory. We should not provide insecure fallbacks.

**Q: What about service accounts / automation?**
A: Service accounts can use longer session timeouts (e.g., 8 hours) or Kamiwaza can provide service account tokens via a different mechanism.

---

## Conclusion

The decision to **not persist credentials** is the correct security choice. It significantly reduces the attack surface and aligns with security best practices.

The OAuth flow implementation is well-documented and achievable in ~1 week.

**Status:** Ready to implement. Awaiting approval to proceed with OAuth flow development.
