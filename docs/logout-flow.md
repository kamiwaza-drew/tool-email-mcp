# Logout Flow

This document describes how the logout button in App Garden extensions interacts with the Kamiwaza platform.

## Overview

The logout flow involves four layers:
1. **UI Component** - React button that initiates logout
2. **Session Context** - React hook that manages session state
3. **Extension Backend** - FastAPI endpoint that proxies to Kamiwaza
4. **Kamiwaza Platform** - Central auth service that invalidates sessions

## Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│  Browser                                                            │
│  ┌──────────────┐    ┌──────────────┐    ┌────────────────────┐    │
│  │ Logout Button│ -> │ useSession() │ -> │ POST /api/auth/    │    │
│  │  (click)     │    │   logout()   │    │      logout        │    │
│  └──────────────┘    └──────────────┘    └─────────┬──────────┘    │
└────────────────────────────────────────────────────│────────────────┘
                                                     │
                                                     ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Extension Backend (Python/FastAPI)                                 │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │ POST /auth/logout                                              │ │
│  │   • Collect auth headers (cookie, authorization)              │ │
│  │   • Forward x-forwarded-* headers                             │ │
│  │   • Call Kamiwaza logout                                      │ │
│  └─────────────────────────────────────────┬──────────────────────┘ │
└────────────────────────────────────────────│────────────────────────┘
                                             │
                                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Kamiwaza Platform                                                  │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │ POST /auth/logout                                              │ │
│  │   • Invalidate session                                        │ │
│  │   • Return redirect URLs                                      │ │
│  │   • Optional: front_channel_logout_url for OIDC               │ │
│  └────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

## Detailed Flow

### 1. UI Layer (React Component)

The logout button is typically rendered in a session timer or navigation component:

```tsx
import { useSession } from '@kamiwaza/auth/client';

function LogoutButton() {
  const { logout } = useSession();

  const handleLogout = async () => {
    try {
      const response = await logout();

      // If front-channel logout URL is provided, redirect there first (OIDC)
      if (response.front_channel_logout_url) {
        window.location.assign(response.front_channel_logout_url);
        return;
      }

      // Otherwise redirect to post-logout destination
      const redirectUrl = response.redirect_url || '/logged-out';
      window.location.assign(redirectUrl);
    } catch (err) {
      console.error('Logout failed', err);
      // Still redirect on error
      window.location.assign('/logged-out');
    }
  };

  return <button onClick={handleLogout}>Logout</button>;
}
```

**Key behavior:**
- Calls `logout()` from the `useSession` hook
- Handles both OIDC front-channel logout and direct redirects
- Always redirects even on error (fail-safe)

### 2. Session Context (React Hook)

The `SessionProvider` manages session state and provides the `logout` function:

```tsx
// From @kamiwaza/auth/client
const handleLogout = async (redirectUri?: string): Promise<LogoutResponse> => {
  const response = await logoutImpl(redirectUri, basePath, logoutEndpoint);
  setSession(null);           // Clear local session state
  setSecondsRemaining(undefined);
  return response;
};
```

**Key behavior:**
- Calls the logout fetch utility
- Clears local session state immediately
- Returns the `LogoutResponse` for redirect handling

### 3. Frontend Fetch Utility

The fetch utility makes the actual HTTP request:

```typescript
// POST {basePath}/api/auth/logout
export async function logout(
  redirectUri?: string,
  basePath?: string,
  endpoint: string = '/api/auth/logout'
): Promise<LogoutResponse> {
  const response = await fetch(`${basePath}${endpoint}`, {
    method: 'POST',
    credentials: 'include',  // Important: sends cookies
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      post_logout_redirect_uri: redirectUri,
    }),
  });

  return response.json();
}
```

**Key behavior:**
- Uses `credentials: 'include'` to send auth cookies
- Accepts optional `post_logout_redirect_uri` for custom redirect destination

### 4. Backend Python Endpoint

The backend endpoint proxies the logout request to Kamiwaza:

```python
@router.post("/auth/logout", response_model=LogoutResponse)
async def logout(request: Request, body: LogoutRequest | None = None):
    # Get Kamiwaza API base URL
    api_base = os.getenv("KAMIWAZA_API_URL") or "http://host.docker.internal:8080"
    logout_url = f"{api_base}/auth/logout"

    # Forward auth headers to Kamiwaza
    headers = {}
    if "cookie" in request.headers:
        headers["cookie"] = request.headers["cookie"]
    if "authorization" in request.headers:
        headers["authorization"] = request.headers["authorization"]

    # Forward x-forwarded headers
    for header in ["x-forwarded-host", "x-forwarded-proto", "x-forwarded-for"]:
        if header in request.headers:
            headers[header] = request.headers[header]

    # Call Kamiwaza logout
    async with httpx.AsyncClient() as client:
        response = await client.post(
            logout_url,
            headers=headers,
            json={"post_logout_redirect_uri": post_logout_redirect},
        )

    # Return response with redirect URLs
    return LogoutResponse(
        success=True,
        message="Logged out successfully",
        redirect_url=response.json().get("post_logout_redirect_uri"),
        front_channel_logout_url=response.json().get("front_channel_logout_url"),
    )
```

**Key behavior:**
- Forwards authentication headers (cookies, authorization token)
- Forwards `x-forwarded-*` headers for proper URL reconstruction
- Calls Kamiwaza's `/auth/logout` endpoint
- Returns redirect URLs for the frontend to handle
- Gracefully handles Kamiwaza failures (still returns redirect URL)

### 5. Kamiwaza Platform

The Kamiwaza platform's `/auth/logout` endpoint:
- Invalidates the user's session
- Clears session cookies
- Returns redirect URLs:
  - `post_logout_redirect_uri`: Where to send the user after logout
  - `front_channel_logout_url`: For OIDC front-channel logout (if configured)

## Response Types

### LogoutResponse

```typescript
interface LogoutResponse {
  success: boolean;
  message: string;
  redirect_url?: string;           // Post-logout destination
  front_channel_logout_url?: string; // OIDC front-channel logout URL
}
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `KAMIWAZA_API_URL` | Internal Kamiwaza API URL | `http://host.docker.internal:8080` |
| `KAMIWAZA_PUBLIC_API_URL` | Public Kamiwaza API URL | `https://localhost/api` |
| `KAMIWAZA_TLS_REJECT_UNAUTHORIZED` | TLS verification | `true` |

## Error Handling

The logout flow is designed to be resilient:

1. **Backend Kamiwaza call fails**: Returns `success: false` but still provides `redirect_url`
2. **Frontend fetch fails**: Catches error and redirects to `/logged-out` anyway
3. **Session already expired**: Logout still works, redirects appropriately

This ensures users can always log out, even if there are network issues.

## OIDC Front-Channel Logout

When Kamiwaza is configured with an OIDC provider, the logout flow may include front-channel logout:

1. User clicks logout
2. Backend calls Kamiwaza, which returns `front_channel_logout_url`
3. Frontend redirects to OIDC provider's logout endpoint
4. OIDC provider clears its session and redirects back to the app

## Usage with Shared Libraries

### Using kamiwaza-auth (Python)

```python
from fastapi import FastAPI
from kamiwaza_auth.endpoints import create_session_router

app = FastAPI()
app.include_router(create_session_router())  # Adds /session, /auth/login-url, /auth/logout
```

### Using @kamiwaza/auth (TypeScript)

```tsx
import { SessionProvider, useSession } from '@kamiwaza/auth/client';

// Wrap your app
function App() {
  return (
    <SessionProvider>
      <YourApp />
    </SessionProvider>
  );
}

// Use in components
function Header() {
  const { session, logout } = useSession();
  return <button onClick={() => logout()}>Logout</button>;
}
```

## Related Documentation

- [Auth Integration Guide](./auth-integration-guide.md) - Complete authentication setup
- [Path-Based Routing Cheatsheet](./path-based-routing-cheatsheet.md) - URL routing in App Garden
