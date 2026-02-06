# Path-Based Routing Cheatsheet for Kamiwaza Apps

> **📦 Template Update Required**
>
> Before implementing these patterns, ensure your extension repo is up-to-date with the latest Kamiwaza extensions template:
> ```bash
> copier update
> ```
> This pulls in critical SDK fixes (e.g., `host_name: z.string().nullish()`) and shared library updates that these patterns depend on.

This guide explains how to adapt your application to support both port-based and path-based routing in Kamiwaza.

## Overview

Kamiwaza deploys apps in two modes:

| Mode | URL Pattern | When Used |
|------|-------------|-----------|
| **Port-based** | `https://host:PORT/` | Direct port access |
| **Path-based** | `https://host/runtime/apps/{id}/` | Through Traefik reverse proxy |

Your app must handle both modes seamlessly.

### Services and Tools

Services and tools also use path-based routing, with different prefixes and proxy behavior:

- Services: `/runtime/services/{id}`
- Tools: `/runtime/tools/{id}`
- Prefix is **stripped** before forwarding. Services/tools should serve at `/` and use `X-Forwarded-Prefix` only when constructing links.
- `KAMIWAZA_APP_PATH` is still set for services (it will contain `/runtime/services/{id}`).

---

## 1. Environment Variables

### Key Variables

```bash
# CRITICAL: Set by Kamiwaza platform to indicate routing mode
# "path" = path-based routing, "port" = port-based routing
KAMIWAZA_ROUTING_MODE="path"  # or "port"

# Set by Kamiwaza platform - the app's path prefix (used when KAMIWAZA_ROUTING_MODE=path)
# Services receive /runtime/services/{uuid}
KAMIWAZA_APP_PATH="/runtime/apps/{uuid}"

# Your app should expose this for client-side code
NEXT_PUBLIC_APP_BASE_PATH="${KAMIWAZA_APP_PATH}"

# For server-side Kamiwaza API calls
KAMIWAZA_API_URL="https://host.docker.internal/api"

# For constructing public model endpoints (goes through Traefik)
KAMIWAZA_PUBLIC_API_URL="https://public-hostname/api"
```

### docker-compose.appgarden.yml

```yaml
services:
  web:
    environment:
      - KAMIWAZA_API_URL=${KAMIWAZA_API_URL:-https://host.docker.internal/api}
      - KAMIWAZA_PUBLIC_API_URL=${KAMIWAZA_PUBLIC_API_URL:-https://localhost/api}
    extra_hosts:
      - "host.docker.internal:host-gateway"
```

---

## 2. Docker Entrypoint (Critical!)

For Next.js apps, `basePath` must be set at **build time**. Use a docker entrypoint to rebuild when path-based routing is detected:

```bash
#!/bin/sh
# docker-entrypoint.sh
set -e

# Handle path-based routing mode
# Check KAMIWAZA_ROUTING_MODE first (set by platform), then fall back to checking env vars
# KAMIWAZA_ROUTING_MODE: "path" = path-based, "port" or unset = port-based
if [ "$KAMIWAZA_ROUTING_MODE" = "path" ] || { [ -z "$KAMIWAZA_ROUTING_MODE" ] && [ -n "$NEXT_PUBLIC_APP_BASE_PATH" ]; }; then
  export NEXT_PUBLIC_APP_BASE_PATH="${NEXT_PUBLIC_APP_BASE_PATH:-$KAMIWAZA_APP_PATH}"
  if [ -n "$NEXT_PUBLIC_APP_BASE_PATH" ]; then
    echo "🔧 Path-based routing detected: ${NEXT_PUBLIC_APP_BASE_PATH}"
    echo "📦 Rebuilding Next.js with base path..."
    pnpm run build
    echo "✅ Rebuild complete!"
  else
    echo "⚠️ Path routing mode but no base path set - using pre-built app"
  fi
else
  echo "📡 Port-based routing mode - using pre-built app"
fi

exec "$@"
```

**Key Logic:**
- `KAMIWAZA_ROUTING_MODE=path` → Rebuild with base path
- `KAMIWAZA_ROUTING_MODE=port` → Use pre-built app (no rebuild)
- `KAMIWAZA_ROUTING_MODE` unset + `NEXT_PUBLIC_APP_BASE_PATH` set → Rebuild (backward compat)

**Dockerfile:**
```dockerfile
COPY docker-entrypoint.sh ./
RUN chmod +x docker-entrypoint.sh
ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["pnpm", "start"]
```

---

## 3. Next.js Configuration

### next.config.ts

```typescript
import type { NextConfig } from 'next';

// Read base path from environment (set at build time)
const basePath = process.env.NEXT_PUBLIC_APP_BASE_PATH || "";

const nextConfig: NextConfig = {
  // Only set basePath/assetPrefix if provided (path-based routing)
  basePath: basePath || undefined,
  assetPrefix: basePath || undefined,
  // ... other config
};

export default nextConfig;
```

**What Next.js auto-handles with basePath:**
- `<Link>` components
- `router.push()` / `router.replace()`
- `next/image` src URLs
- Static assets

**What you must handle manually:**
- `fetch()` calls
- `window.location` manipulation
- WebSocket URLs
- External redirects

---

## 4. Client-Side API Utilities

Create a utility for client-side fetch calls:

### lib/utils/client-api.ts

```typescript
/**
 * Get the basePath for API calls.
 * Returns empty string for port-based, or /runtime/apps/{id} for path-based.
 */
export function getBasePath(): string {
  return process.env.NEXT_PUBLIC_APP_BASE_PATH || '';
}

/**
 * Prefix a path with the basePath for path-based routing.
 * @param path - API path starting with / (e.g., '/api/models')
 * @returns Full path with basePath prefix
 */
export function getApiPath(path: string): string {
  const basePath = getBasePath();
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  return `${basePath}${normalizedPath}`;
}

/**
 * SWR fetcher with basePath support.
 */
export const apiFetcher = async (url: string) => {
  const fullUrl = getApiPath(url);
  const response = await fetch(fullUrl);
  if (!response.ok) throw new Error(`API error: ${response.status}`);
  return response.json();
};

/**
 * Fetch wrapper with basePath support.
 */
export async function apiFetch(path: string, init?: RequestInit): Promise<Response> {
  const fullUrl = getApiPath(path);
  return fetch(fullUrl, init);
}
```

### Usage in Components

```typescript
// ❌ WRONG - won't work with path-based routing
const response = await fetch('/api/models');

// ✅ CORRECT - handles both modes
import { apiFetch, getApiPath } from '@/lib/utils/client-api';

const response = await apiFetch('/api/models');
// OR
const response = await fetch(getApiPath('/api/models'));

// With SWR
import useSWR from 'swr';
import { apiFetcher } from '@/lib/utils/client-api';

const { data } = useSWR('/api/models', apiFetcher);
```

---

## 5. Server-Side URL Construction

### lib/utils/api-url.ts

```typescript
import { headers } from 'next/headers';

export async function getApiUrl(path: string): Promise<string> {
  const headersList = await headers();
  const host = headersList.get('host');
  const protocol = headersList.get('x-forwarded-proto') || 'http';

  // Get basePath for path-based routing
  const basePath = process.env.NEXT_PUBLIC_APP_BASE_PATH || '';

  if (host) {
    return `${protocol}://${host}${basePath}${path}`;
  }

  // Fallback
  return `${basePath}${path}`;
}
```

---

## 6. Model Endpoint Handling (SDK)

The `@kamiwaza/client` SDK automatically handles path vs port-based model endpoints:

### How It Works

```typescript
// SDK constructs endpoints based on deployment data
if (deployment.access_path) {
  // Path-based routing (preferred)
  endpoint = `${baseOrigin}${deployment.access_path}/v1`;
  // Result: https://host/runtime/models/{uuid}/v1
} else if (deployment.lb_port) {
  // Port-based routing (fallback)
  endpoint = `${protocol}://${hostname}:${lb_port}/v1`;
  // Result: https://host:8080/v1
}
```

### Using the SDK

```typescript
import { KamiwazaClient, ForwardAuthAuthenticator } from '@kamiwaza/client';

// Create client with public URL for endpoint construction
const client = new KamiwazaClient({
  baseUrl: process.env.KAMIWAZA_API_URL,           // Internal API
  publicApiUrl: process.env.KAMIWAZA_PUBLIC_API_URL, // For model endpoints
  authenticator: new ForwardAuthAuthenticator(authHeaders),
});

// Get deployments with proper endpoints
const deployments = await client.serving.listActiveDeployments();
// Each deployment has: { endpoint: "https://host/runtime/models/{id}/v1", ... }

// Use the endpoint directly
const endpoint = deployment.endpoint; // Full URL including /v1
```

### Making LLM Calls

```typescript
import { createOpenAICompatible } from '@ai-sdk/openai-compatible';

// Use endpoint directly as baseURL
const provider = createOpenAICompatible({
  name: 'kamiwaza',
  baseURL: deployment.endpoint, // Already includes /v1
  fetch: customFetch,
});

// The SDK appends /chat/completions automatically
// Final URL: https://host/runtime/models/{id}/v1/chat/completions
```

---

## 7. Quick Reference: What Goes Where

| Item | Where | Example |
|------|-------|---------|
| basePath config | `next.config.ts` | `basePath: process.env.NEXT_PUBLIC_APP_BASE_PATH` |
| Runtime rebuild | `docker-entrypoint.sh` | `if [ -n "$KAMIWAZA_APP_PATH" ]; then pnpm build` |
| Client fetch | Use `getApiPath()` | `fetch(getApiPath('/api/data'))` |
| Server URL | Use `getApiUrl()` | `await getApiUrl('/api/internal')` |
| SWR fetcher | Use `apiFetcher` | `useSWR('/api/models', apiFetcher)` |
| Model endpoints | Use SDK | `client.serving.listActiveDeployments()` |

---

## 8. Common Pitfalls

### ❌ Hardcoded URLs
```typescript
// BAD
fetch('http://localhost:3000/api/data');
fetch('/api/data'); // Missing basePath
```

### ❌ Forgetting entrypoint rebuild
```dockerfile
# BAD - basePath set at image build time, won't adapt
ENV NEXT_PUBLIC_APP_BASE_PATH=/fixed/path
RUN pnpm build
```

### ❌ Using wrong protocol for model calls
```typescript
// BAD - port 8080 is HTTP, not HTTPS
const url = `https://host:8080/v1/chat/completions`;
```

### ✅ Correct Patterns
```typescript
// GOOD - use SDK endpoint directly
const endpoint = deployment.endpoint; // Already has correct protocol and path

// GOOD - use utilities
import { getApiPath } from '@/lib/utils/client-api';
fetch(getApiPath('/api/models'));
```

---

## 9. Testing Both Modes

### Local Port-Based Testing
```bash
# No path set - port-based mode
docker-compose up
# Access at http://localhost:3000/
```

### Local Path-Based Testing
```bash
# Set path - triggers rebuild in entrypoint
KAMIWAZA_APP_PATH=/runtime/apps/test-123 docker-compose up
# Access at http://localhost:3000/runtime/apps/test-123/
```

---

## 10. Login Gate & Security Banners

Kamiwaza provides centralized authentication and security banners (consent gates, classification banners) via an embed script and auth middleware.

### Environment Variables

```bash
# Enable Kamiwaza authentication (SSO via Keycloak)
KAMIWAZA_USE_AUTH=true

# Public API URL for browser redirects and embed script
KAMIWAZA_PUBLIC_API_URL="https://public-hostname/api"
```

### docker-compose.appgarden.yml

```yaml
services:
  web:
    environment:
      - KAMIWAZA_USE_AUTH=${KAMIWAZA_USE_AUTH:-false}
      - KAMIWAZA_PUBLIC_API_URL=${KAMIWAZA_PUBLIC_API_URL:-https://localhost/api}
```

---

### Security Embed Script (Banners)

The security embed script provides:
- **Consent gate**: User must accept terms before using the app
- **Classification banners**: Top/bottom banners showing data classification level

Add to your root layout (`app/layout.tsx`):

```typescript
import Script from 'next/script';

// Construct embed URL from public API URL
const KAMIWAZA_SECURITY_EMBED_URL = process.env.KAMIWAZA_PUBLIC_API_URL
  ? `${process.env.KAMIWAZA_PUBLIC_API_URL}/security/embed.js`
  : null;

export default function RootLayout({ children }) {
  return (
    <html>
      <body>
        {/* Kamiwaza security: consent gate and classification banners */}
        {KAMIWAZA_SECURITY_EMBED_URL && (
          <Script
            src={KAMIWAZA_SECURITY_EMBED_URL}
            strategy="beforeInteractive"
          />
        )}
        {children}
      </body>
    </html>
  );
}
```

**Key points:**
- Use `strategy="beforeInteractive"` to load before app hydrates
- Script is conditionally loaded only when `KAMIWAZA_PUBLIC_API_URL` is set
- Banners automatically appear based on platform security configuration

---

### Authentication Middleware

Install the `@kamiwaza/auth` package and create middleware:

```typescript
// middleware.ts
import { NextResponse, type NextRequest } from 'next/server';
import { createAuthMiddleware } from '@kamiwaza/auth/middleware';

// Create base middleware for App Garden deployments
const basePathMiddleware = createAuthMiddleware({
  cookieOptions: {
    secure: process.env.NODE_ENV === 'production',
  },
});

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Allow auth-related API routes to pass through
  if (pathname.startsWith('/api/auth') || pathname.startsWith('/api/session')) {
    return NextResponse.next();
  }

  // Run base path middleware
  const basePathResponse = basePathMiddleware(request);

  // Check if auth is enabled
  const useAuth = process.env.KAMIWAZA_USE_AUTH === 'true';
  const requiresAuth = pathname === '/' || pathname.startsWith('/chat/');

  if (requiresAuth && !useAuth) {
    // Auth disabled - redirect to guest auth if no token
    const token = request.cookies.get('access_token');
    if (!token) {
      const redirectUrl = encodeURIComponent(pathname);
      return NextResponse.redirect(
        new URL(`/api/auth/guest?redirectUrl=${redirectUrl}`, request.url)
      );
    }
  }

  return basePathResponse;
}

export const config = {
  matcher: ['/', '/chat/:id', '/api/:path*', '/((?!_next/static|_next/image|favicon.ico).*)'],
};
```

---

### AuthGuard Component (Client-Side)

Wrap protected pages with `AuthGuard` for client-side redirect handling:

```typescript
// components/auth-guard-wrapper.tsx
'use client';

import { AuthGuard } from '@kamiwaza/auth/client';

export function AuthGuardWrapper({ children }: { children: React.ReactNode }) {
  return (
    <AuthGuard
      publicRoutes={['/login', '/register', '/logged-out', '/api/auth']}
      loginUrlEndpoint="/api/auth/login-url"
    >
      {children}
    </AuthGuard>
  );
}
```

Use in your layout:

```typescript
// app/(protected)/layout.tsx
import { AuthGuardWrapper } from '@/components/auth-guard-wrapper';

export default function ProtectedLayout({ children }) {
  return (
    <AuthGuardWrapper>
      {children}
    </AuthGuardWrapper>
  );
}
```

---

### Login URL API Route

Create an endpoint that returns the Kamiwaza login URL:

```typescript
// app/api/auth/login-url/route.ts
import { NextRequest, NextResponse } from 'next/server';

export async function GET(request: NextRequest) {
  const redirectUri = request.nextUrl.searchParams.get('redirect_uri') || '/';

  const kamiwazaPublicApiUrl =
    process.env.KAMIWAZA_PUBLIC_API_URL || 'https://localhost/api';

  const loginUrl = `${kamiwazaPublicApiUrl}/auth/login?redirect_uri=${encodeURIComponent(redirectUri)}`;

  return NextResponse.json({ login_url: loginUrl });
}
```

---

### Session Handling

Extract user identity from Kamiwaza ForwardAuth headers:

```typescript
// lib/session.ts
import { headers } from 'next/headers';
import { extractIdentity } from '@kamiwaza/auth/server';

export async function auth() {
  const useAuth = process.env.KAMIWAZA_USE_AUTH === 'true';

  // Try Kamiwaza ForwardAuth headers first
  const headersList = await headers();
  const identity = extractIdentity(headersList);

  if (identity) {
    // User authenticated via Kamiwaza SSO
    return {
      user: {
        id: identity.resolvedUuid,
        name: identity.name,
        email: identity.email
      }
    };
  }

  if (useAuth) {
    // Auth enabled but no headers - anonymous user (AuthGuard will redirect)
    return { user: { id: 'anonymous', name: 'Guest' } };
  }

  // Auth disabled - fall back to guest mode
  return { user: { id: 'guest', name: 'Guest' } };
}
```

---

### Auth Flow Summary

```
┌─────────────────────────────────────────────────────────────────┐
│                      User Request                                │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│  Security Embed Script (layout.tsx)                             │
│  - Shows consent gate if required                               │
│  - Displays classification banners                              │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│  Middleware (middleware.ts)                                      │
│  - KAMIWAZA_USE_AUTH=true → Let through, AuthGuard handles      │
│  - KAMIWAZA_USE_AUTH=false → Guest auth via JWT cookie          │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│  AuthGuard Component (client-side)                              │
│  - Checks /api/session for auth status                          │
│  - If 401 → Redirect to /api/auth/login-url                     │
│  - If OK → Render children                                       │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│  Session Extraction (server-side)                               │
│  - extractIdentity() reads ForwardAuth headers                  │
│  - Headers set by Traefik after Keycloak authentication         │
└─────────────────────────────────────────────────────────────────┘
```

---

### Quick Reference: Auth & Banners

| Feature | Component | Required Env Var |
|---------|-----------|------------------|
| Security banners | `<Script>` in layout | `KAMIWAZA_PUBLIC_API_URL` |
| SSO authentication | Middleware + AuthGuard | `KAMIWAZA_USE_AUTH=true` |
| Login redirect | `/api/auth/login-url` route | `KAMIWAZA_PUBLIC_API_URL` |
| User identity | `extractIdentity()` | ForwardAuth headers from Traefik |
| Guest mode | JWT cookie | `KAMIWAZA_USE_AUTH=false` |

---

## Summary

1. **Set up entrypoint** to rebuild when `KAMIWAZA_APP_PATH` is set
2. **Configure next.config.ts** to read `NEXT_PUBLIC_APP_BASE_PATH`
3. **Create client utilities** (`getApiPath`, `apiFetcher`) for fetch calls
4. **Use SDK** for model endpoints - it handles path/port automatically
5. **Add security embed script** in root layout for banners
6. **Implement auth middleware** and AuthGuard for login gate
7. **Test both modes** before deploying
