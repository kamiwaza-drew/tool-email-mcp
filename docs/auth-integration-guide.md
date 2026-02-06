# Auth Integration Guide

This guide is the canonical playbook for integrating Kamiwaza authentication into your extensions. Whether you're retrofitting auth into an existing app/tool or building a new one, this guide covers everything you need.

## Table of Contents

1. [How Auth Works](#how-auth-works)
2. [Prerequisites](#prerequisites)
3. [Building the Shared Libraries](#building-the-shared-libraries)
4. [Integrating Auth into Apps](#integrating-auth-into-apps)
5. [Integrating Auth into Tools](#integrating-auth-into-tools)
6. [Session Management](#session-management)
7. [Login and Logout Flows](#login-and-logout-flows)
8. [Common Patterns](#common-patterns)
9. [Troubleshooting](#troubleshooting)
10. [Migration Checklist](#migration-checklist)

---

## How Auth Works

### Architecture Overview

Kamiwaza uses Traefik forward auth to authenticate requests to App Garden applications:

```
┌─────────┐     ┌─────────┐     ┌──────────────┐     ┌─────────┐
│ Browser │────>│ Traefik │────>│   Frontend   │────>│ Backend │
└─────────┘     └─────────┘     │   (Next.js)  │     │(FastAPI)│
                    │           └──────────────┘     └─────────┘
                    │                                     │
                    │ /api/auth/validate                  │
                    ▼                                     ▼
              ┌───────────┐                        ┌────────────┐
              │ Kamiwaza  │                        │  Kamiwaza  │
              │   Auth    │                        │    API     │
              │  Service  │                        └────────────┘
              └───────────┘
```

### Authentication Flow

1. **User accesses app** → Traefik intercepts the request
2. **Traefik validates** → Calls `/api/auth/validate` with the user's cookies/token
3. **If authenticated** → Traefik adds identity headers (`x-user-id`, `x-user-email`, etc.)
4. **Request continues** → Your app receives the request with identity headers
5. **If not authenticated** → User is redirected to Kamiwaza login

### Identity Headers

When authentication succeeds, Traefik adds these headers:

| Header | Description | Example |
|--------|-------------|---------|
| `x-user-id` | Unique user identifier | `550e8400-e29b-41d4-a716-446655440000` |
| `x-user-email` | User's email | `user@example.com` |
| `x-user-name` | Display name | `John Doe` |
| `x-user-roles` | Comma-separated roles | `admin,user` |
| `x-request-id` | Request correlation ID | `req-12345` |

### JWT Token Flow

The auth system uses JWT tokens stored in cookies:

- **Access Token**: Short-lived (5 minutes), used for API calls
- **Refresh Token**: Longer-lived, used to obtain new access tokens
- **Session Cookie**: HTTP-only cookie containing the tokens

---

## Prerequisites

Before integrating auth, ensure you have:

1. **Kamiwaza platform running** with auth enabled
2. **Extension repo** with the shared libraries (`shared/python/`, `shared/typescript/`)
3. **Docker environment** configured with `host.docker.internal` access

---

## Building the Shared Libraries

The auth libraries must be built before use:

```bash
# Build all packages
make package-libs

# Or build individually
make package-libs PYTHON_ONLY=1    # Python wheel only
make package-libs TS_ONLY=1        # TypeScript package only
make package-libs CLEAN=1          # Clean rebuild
```

### Package Locations

After building:

| Package | Location |
|---------|----------|
| Python wheel | `shared/python/dist/kamiwaza_auth-{version}-py3-none-any.whl` |
| TypeScript tgz | `shared/typescript/kamiwaza-auth/kamiwaza-auth-{version}.tgz` |

---

## Integrating Auth into Apps

Apps typically have a Next.js frontend and FastAPI backend. Both need auth integration.

### Step 1: Install the Libraries

**Backend (Python):**

```bash
# Copy wheel to backend
cp shared/python/dist/kamiwaza_auth-*.whl apps/my-app/backend/

# Add to requirements.txt (at the top)
echo "./kamiwaza_auth-0.1.0-py3-none-any.whl" >> apps/my-app/backend/requirements.txt
```

**Frontend (TypeScript):**

```bash
# Copy package to frontend
cp shared/typescript/kamiwaza-auth/kamiwaza-auth-*.tgz apps/my-app/frontend/

# Add to package.json
cd apps/my-app/frontend
npm pkg set dependencies.@kamiwaza/auth="file:./kamiwaza-auth-0.1.0.tgz"
npm install
```

### Step 2: Configure the Backend

**Add session router to FastAPI app:**

```python
# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from kamiwaza_auth.endpoints import create_session_router

app = FastAPI()

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add session endpoints: /session, /auth/login-url, /auth/logout
app.include_router(create_session_router(prefix="/api"))

# Your other routes...
```

**Protect endpoints with auth:**

```python
from fastapi import Depends
from kamiwaza_auth import Identity, require_auth, get_identity

# Requires authentication - returns 401 if not authenticated
@app.get("/api/protected")
async def protected_endpoint(identity: Identity = Depends(require_auth)):
    return {"user": identity.email, "roles": identity.roles}

# Optional authentication - works for both authenticated and anonymous
@app.get("/api/public")
async def public_endpoint(request: Request):
    identity = await get_identity(request)
    if identity.is_authenticated:
        return {"message": f"Hello, {identity.name}!"}
    return {"message": "Hello, guest!"}
```

### Step 3: Configure the Frontend

**Create middleware for base path handling (`middleware.ts`):**

```typescript
import { createAuthMiddleware } from '@kamiwaza/auth/middleware';

export const middleware = createAuthMiddleware();

export const config = {
  // Must be inline - Next.js cannot import from modules
  matcher: ['/((?!_next/static|_next/image|favicon.ico|.*\\..*).*)'],
};
```

**Set up session provider and auth guard (`app/layout.tsx`):**

```tsx
import { SessionProvider, AuthGuard } from '@kamiwaza/auth/client';

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html>
      <body>
        <SessionProvider>
          <AuthGuard publicRoutes={['/logged-out', '/public']}>
            {children}
          </AuthGuard>
        </SessionProvider>
      </body>
    </html>
  );
}
```

**Create API proxy route (`app/api/[...path]/route.ts`):**

```typescript
import { createProxyHandlers } from '@kamiwaza/auth/server';

const BACKEND_URL = process.env.BACKEND_URL || 'http://backend:8000';

const { GET, POST, PUT, PATCH, DELETE, OPTIONS } = createProxyHandlers({
  backendUrl: BACKEND_URL,
});

export { GET, POST, PUT, PATCH, DELETE, OPTIONS };
```

**Use session hook in components:**

```tsx
'use client';

import { useSession } from '@kamiwaza/auth/client';

export function UserStatus() {
  const { session, isLoading, secondsRemaining, logout } = useSession();

  if (isLoading) return <div>Loading...</div>;
  if (!session) return <div>Not logged in</div>;

  return (
    <div>
      <p>Welcome, {session.name}</p>
      <p>Session expires in {secondsRemaining}s</p>
      <button onClick={logout}>Logout</button>
    </div>
  );
}
```

### Step 4: Configure Docker Compose

```yaml
services:
  frontend:
    build: ./frontend
    environment:
      - BACKEND_URL=http://backend:8000
      - KAMIWAZA_PUBLIC_API_URL=${KAMIWAZA_PUBLIC_API_URL:-https://localhost/api}
    depends_on:
      - backend

  backend:
    build: ./backend
    environment:
      - KAMIWAZA_API_URL=${KAMIWAZA_API_URL:-https://localhost/api}
      - KAMIWAZA_PUBLIC_API_URL=${KAMIWAZA_PUBLIC_API_URL:-https://localhost/api}
      - KAMIWAZA_ENDPOINT=${KAMIWAZA_ENDPOINT:-http://host.docker.internal:8080}
      - OPENAI_BASE_URL=${KAMIWAZA_ENDPOINT:-http://host.docker.internal:8080}
      - OPENAI_API_KEY=${OPENAI_API_KEY:-not-needed-kamiwaza}
    extra_hosts:
      - "host.docker.internal:host-gateway"
```

---

## Integrating Auth into Tools

MCP tools are simpler - they only have a Python backend.

### Step 1: Install the Library

```bash
cp shared/python/dist/kamiwaza_auth-*.whl tools/my-tool/
# Add to requirements.txt
```

### Step 2: Add Auth to MCP Server

```python
from mcp import FastMCP
from kamiwaza_auth import get_identity, require_auth
from kamiwaza_auth.endpoints import create_session_router
from fastapi import Depends, Request

mcp = FastMCP("my-tool")
app = mcp.create_fastapi_app()

# Add session endpoints
app.include_router(create_session_router())

# Protected tool function
@mcp.tool()
async def protected_tool(request: Request, param: str) -> dict:
    """A protected tool that requires authentication."""
    identity = await get_identity(request)
    if not identity.is_authenticated:
        return {"error": "Authentication required"}

    return {"result": f"Hello {identity.name}, you said: {param}"}

# Health check (unprotected)
@app.get("/health")
async def health():
    return {"status": "healthy"}
```

---

## Session Management

### How Sessions Work

1. **Session creation**: When user logs in via Keycloak, Kamiwaza creates a session
2. **Session storage**: JWT tokens stored in HTTP-only cookies
3. **Session validation**: Each request validates the token via forward auth
4. **Session expiry**: Access tokens expire in 5 minutes, auto-refreshed via refresh token
5. **Session termination**: Logout clears cookies and invalidates the session

### Session Endpoints

The `create_session_router()` adds these endpoints:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/session` | GET | Returns current session info (user, expiry time) |
| `/auth/login-url` | GET | Builds a login URL with redirect |
| `/auth/logout` | POST | Logs out and returns redirect URLs |

### Session Response Format

```json
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "name": "John Doe",
  "roles": ["user"],
  "expires_at": "2024-01-15T12:30:00Z",
  "seconds_remaining": 285,
  "auth_enabled": true
}
```

---

## Login and Logout Flows

### Login Flow

1. User accesses protected route
2. `AuthGuard` detects no session → redirects to login
3. Frontend calls `/api/auth/login-url?redirect_uri=<current_url>`
4. Backend returns Kamiwaza login URL
5. User redirected to Kamiwaza → Keycloak
6. After login, user redirected back to `redirect_uri`

### Logout Flow

1. User clicks logout
2. Frontend calls `logout()` from `useSession` hook
3. Hook calls `/api/auth/logout` POST
4. Backend:
   - Clears session cookies
   - Calls Kamiwaza to invalidate session
   - Returns redirect URLs (Keycloak logout + final destination)
5. Frontend navigates to Keycloak logout URL
6. Keycloak redirects to final destination (Kamiwaza login page)

### Implementing Logout Button

```tsx
'use client';

import { useSession } from '@kamiwaza/auth/client';

export function LogoutButton() {
  const { logout } = useSession();

  const handleLogout = async () => {
    await logout();
    // logout() handles the redirect automatically
  };

  return <button onClick={handleLogout}>Logout</button>;
}
```

---

## Common Patterns

### Calling Kamiwaza APIs with Auth

Always forward auth headers when calling Kamiwaza APIs:

```python
from kamiwaza_auth import KamiwazaClient, forward_auth_headers

# Using KamiwazaClient
client = KamiwazaClient.from_env()
models = await client.get_models(request.headers)

# Manual forwarding with httpx
import httpx

async def call_kamiwaza_api(request: Request, endpoint: str):
    async with httpx.AsyncClient(verify=False) as client:
        resp = await client.get(
            f"https://localhost/api{endpoint}",
            headers=forward_auth_headers(request.headers),
        )
        return resp.json()
```

### Role-Based Access Control

```python
from kamiwaza_auth import require_auth, Identity
from fastapi import Depends, HTTPException

def require_admin(identity: Identity = Depends(require_auth)) -> Identity:
    if not identity.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return identity

@app.get("/api/admin/users")
async def admin_only(identity: Identity = Depends(require_admin)):
    return {"admin": identity.email}
```

### Handling Session Expiry in Frontend

```tsx
'use client';

import { useSession } from '@kamiwaza/auth/client';
import { useEffect } from 'react';

export function SessionTimer() {
  const { secondsRemaining, logout } = useSession();

  useEffect(() => {
    if (secondsRemaining !== null && secondsRemaining <= 0) {
      // Session expired - logout
      logout();
    }
  }, [secondsRemaining, logout]);

  if (secondsRemaining === null) return null;

  // Warn when session is expiring soon
  if (secondsRemaining < 60) {
    return <div className="warning">Session expiring in {secondsRemaining}s</div>;
  }

  return null;
}
```

### Base Path Handling for App Garden

App Garden deploys apps at dynamic paths (e.g., `/runtime/apps/{deployment-id}/`). The middleware handles this automatically:

```typescript
// The middleware sets a cookie with the base path
// All API calls automatically include the base path

import { apiFetch } from '@kamiwaza/auth';

// This automatically becomes /runtime/apps/{id}/api/users
const users = await apiFetch('/api/users').then(r => r.json());
```

---

## Troubleshooting

### 401 Unauthorized Errors

**Symptoms**: API calls return 401, user appears logged in

**Causes and fixes**:

1. **Token expired**: Access tokens have 5-minute TTL
   - Ensure frontend refreshes session periodically
   - Check `secondsRemaining` in session hook

2. **Headers not forwarded**: API proxy not forwarding auth cookies
   - Check proxy route includes `credentials: 'include'`
   - Verify `cookie` header is forwarded

3. **Missing trailing slash**: Some Kamiwaza endpoints require trailing slashes
   - Add trailing slashes to API URLs (e.g., `/api/models/`)

### Redirect Loops

**Symptoms**: Browser stuck in redirect loop between app and login

**Causes and fixes**:

1. **Session endpoint returns 401**: Frontend thinks user is logged out
   - Check backend session endpoint is working
   - Verify cookies are being sent

2. **AuthGuard misconfigured**: Wrong public routes
   - Add `/logged-out` to `publicRoutes`
   - Temporarily disable AuthGuard to debug

### CORS Errors

**Symptoms**: Browser console shows CORS errors

**Causes and fixes**:

1. **Backend missing CORS middleware**:
   ```python
   app.add_middleware(
       CORSMiddleware,
       allow_origins=["*"],
       allow_credentials=True,
       allow_methods=["*"],
       allow_headers=["*"],
   )
   ```

2. **Cookies not sent cross-origin**:
   - Ensure `credentials: 'include'` in fetch calls
   - Check cookie `SameSite` attribute

### Docker Networking Issues

**Symptoms**: Backend can't reach Kamiwaza API

**Causes and fixes**:

1. **Missing extra_hosts**:
   ```yaml
   extra_hosts:
     - "host.docker.internal:host-gateway"
   ```

2. **Wrong URL**: Using `localhost` instead of `host.docker.internal`
   - Backend should use `http://host.docker.internal:8080` for Kamiwaza

3. **SSL verification**: Internal HTTPS calls fail
   - Use `verify=False` for internal calls in development

### Session Not Persisting

**Symptoms**: User logged out after page refresh

**Causes and fixes**:

1. **Cookies not being set**: Check browser dev tools → Application → Cookies
2. **Cookie path mismatch**: Ensure cookie path matches app base path
3. **HTTP-only cookies**: Cookies won't appear in JavaScript, but should be sent with requests

---

## Migration Checklist

Use this checklist when retrofitting auth into an existing app:

### Backend

- [ ] Copy `kamiwaza_auth-*.whl` to backend directory
- [ ] Add wheel to `requirements.txt` (at the top)
- [ ] Add CORS middleware if not present
- [ ] Add session router: `app.include_router(create_session_router(prefix="/api"))`
- [ ] Add `require_auth` dependency to protected endpoints
- [ ] Update Docker Compose with environment variables
- [ ] Add `extra_hosts` for `host.docker.internal`

### Frontend

- [ ] Copy `kamiwaza-auth-*.tgz` to frontend directory
- [ ] Add package to `package.json` and run `npm install`
- [ ] Create `middleware.ts` with auth middleware
- [ ] Add `SessionProvider` to root layout
- [ ] Add `AuthGuard` to root layout
- [ ] Create API proxy route at `app/api/[...path]/route.ts`
- [ ] Replace direct backend calls with `apiFetch`
- [ ] Add logout UI using `useSession` hook

### Docker Compose

- [ ] Set `BACKEND_URL` for frontend service
- [ ] Set `KAMIWAZA_PUBLIC_API_URL` for both services
- [ ] Set `KAMIWAZA_ENDPOINT` for backend (LLM access)
- [ ] Add `extra_hosts` to backend service

### Testing

- [ ] Test login flow: unauthenticated → redirect → login → redirect back
- [ ] Test logout flow: click logout → redirect to Kamiwaza login
- [ ] Test session expiry: wait for token expiry → auto-refresh or logout
- [ ] Test protected endpoints: returns 401 without auth
- [ ] Test API proxy: frontend can call backend APIs

---

## See Also

- [Extension Developer Guide](./extension-developer-guide.md) - Full development guide
- [Shared Libraries](../shared/README.md) - Library documentation
