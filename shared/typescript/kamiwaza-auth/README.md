# @kamiwaza/auth - TypeScript

Forward auth utilities for Next.js frontends in Kamiwaza App Garden.

## Installation

```bash
# Install from local path
npm install ../../shared/typescript/kamiwaza-auth
# or
pnpm add ../../shared/typescript/kamiwaza-auth

# Or copy to your project
cp -r src/* /path/to/your/frontend/lib/
```

## Quick Start

### Middleware (Base Path Handling)

Create `middleware.ts`:

```typescript
import { createAuthMiddleware } from '@kamiwaza/auth/middleware';

export const middleware = createAuthMiddleware();

export const config = {
  // Matcher must be inline - Next.js cannot import it from modules
  matcher: ['/((?!_next/static|_next/image|favicon.ico|sitemap.xml|robots.txt).*)'],
};
```

### Session Provider & Auth Guard

In your root layout:

```typescript
import { SessionProvider, AuthGuard } from '@kamiwaza/auth/client';

export default function RootLayout({ children }) {
  return (
    <SessionProvider>
      <AuthGuard publicRoutes={['/logged-out']}>
        {children}
      </AuthGuard>
    </SessionProvider>
  );
}
```

### API Proxy Route

Create `app/api/[...path]/route.ts`:

```typescript
import { createProxyHandlers } from '@kamiwaza/auth/server';

const { GET, POST, PUT, PATCH, DELETE } = createProxyHandlers({
  backendUrl: process.env.BACKEND_URL,
});

export { GET, POST, PUT, PATCH, DELETE };
```

### Client-Side Session Hook

```typescript
import { useSession } from '@kamiwaza/auth/client';

function UserInfo() {
  const { authEnabled, secondsRemaining, logout, loading } = useSession();

  if (!authEnabled) return null;
  return <span>Session: {secondsRemaining}s remaining</span>;
}
```

### Client-Side Fetch

```typescript
import { apiFetch } from '@kamiwaza/auth';

// GET request
const users = await apiFetch('/api/users').then(r => r.json());

// POST request
const newUser = await apiFetch('/api/users', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ name: 'John' }),
}).then(r => r.json());
```

## Subpath Exports

The library uses subpath exports to separate server/client code for Next.js compatibility:

| Import Path | Description | Use In |
|-------------|-------------|--------|
| `@kamiwaza/auth` | Core utilities (apiFetch, withBase) | Any |
| `@kamiwaza/auth/client` | React components (SessionProvider, AuthGuard, useSession) | Client components |
| `@kamiwaza/auth/server` | Server utilities (createProxyHandlers) | Server components, API routes |
| `@kamiwaza/auth/middleware` | Next.js middleware (createAuthMiddleware) | middleware.ts |

## Components

### Middleware (`@kamiwaza/auth/middleware`)

- `createAuthMiddleware(config?)` - Create Next.js middleware for base path handling
- `DEFAULT_MIDDLEWARE_MATCHER` - Default matcher pattern (cannot be imported into middleware.ts)

### Session (`@kamiwaza/auth/client`)

- `SessionProvider` - React context provider for session state
- `useSession()` - Hook returning `{ authEnabled, secondsRemaining, logout, loading }`
- `AuthGuard` - Component that protects routes and redirects to login
- `fetchSession()` - Fetch session from `/api/session`
- `logout()` - Logout and redirect

### Proxy (`@kamiwaza/auth/server`)

- `createProxyHandlers(config)` - Create all HTTP method handlers
- `forwardHeaders(request)` - Extract headers to forward
- `buildTargetUrl(request, path)` - Build backend URL

### Fetch (`@kamiwaza/auth`)

- `apiFetch(path, init)` - Fetch with auto base path and credentials
- `createApiFetch(config)` - Create configured fetch function

### Base Path (`@kamiwaza/auth` or `@kamiwaza/auth/client`)

- `getBasePathClient()` - Get base path from cookie (client-side)
- `getBasePathServer()` - Get base path from request (server-side, async)
- `withBase(path, basePath)` - Prepend base path to URL
- `parseCookie(header, name)` - Parse cookie value
- `BASE_PATH_COOKIE` - Cookie name constant

## Configuration

### MiddlewareConfig

```typescript
interface MiddlewareConfig {
  cookieName?: string;    // Default: 'app-base-path'
  basePath?: string;      // Default: from environment
}
```

### AuthGuardConfig

```typescript
interface AuthGuardConfig {
  publicRoutes?: string[];    // Routes that don't require auth
  loadingComponent?: React.ReactNode;
  redirectComponent?: React.ReactNode;
}
```

### ProxyConfig

```typescript
interface ProxyConfig {
  backendUrl?: string;    // Default: http://backend:8000
  apiPrefix?: string;     // Default: /api
  excludeHeaders?: string[];
}
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `BACKEND_URL` | Backend URL | `http://backend:8000` |
| `NEXT_PUBLIC_APP_BASE_PATH` | App base path | `` |

## Documentation

See [Auth Integration Guide](../../docs/auth-integration-guide.md) for complete documentation.
