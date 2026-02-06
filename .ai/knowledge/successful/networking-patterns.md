# Networking Patterns - Kamiwaza Extensions

## Frontend-Backend Proxy Pattern

### Next.js API Route Proxy (micro-ats)
```typescript
// frontend/src/app/api/[...path]/route.ts
const BACKEND_URL = process.env.BACKEND_URL || 'http://backend:8000';

const EXCLUDED_HEADERS = new Set([
  'host', 'connection', 'content-length',
  'transfer-encoding', 'upgrade'
]);

function buildTargetUrl(request: NextRequest): string {
  const url = new URL(request.url);
  return `${BACKEND_URL}${url.pathname}${url.search}`;
}

function getForwardHeaders(request: NextRequest): HeadersInit {
  const headers: Record<string, string> = {};
  request.headers.forEach((value, key) => {
    if (!EXCLUDED_HEADERS.has(key.toLowerCase())) {
      headers[key] = value;
    }
  });
  headers['host'] = new URL(BACKEND_URL).host;
  return headers;
}

async function handler(request: NextRequest, method: string) {
  const targetUrl = buildTargetUrl(request);
  const fetchOptions: RequestInit = {
    method,
    headers: getForwardHeaders(request),
    cache: 'no-store',
  };

  if (['POST', 'PUT', 'PATCH'].includes(method) && request.body) {
    const contentType = request.headers.get('content-type') || '';
    if (contentType.includes('application/json')) {
      const json = await request.json();
      fetchOptions.body = JSON.stringify(json);
    } else {
      fetchOptions.body = request.body;
    }
    // @ts-expect-error - duplex required by Next.js
    fetchOptions.duplex = 'half';
  }

  const response = await fetch(targetUrl, fetchOptions);
  const responseHeaders = new Headers();
  response.headers.forEach((value, key) => {
    if (!EXCLUDED_HEADERS.has(key.toLowerCase())) {
      responseHeaders.set(key, value);
    }
  });

  const contentType = response.headers.get('content-type') || '';
  if (contentType.includes('application/json')) {
    const data = await response.json();
    return NextResponse.json(data, {
      status: response.status,
      headers: responseHeaders,
    });
  }

  const data = await response.arrayBuffer();
  return new NextResponse(data, {
    status: response.status,
    headers: responseHeaders,
  });
}

export async function GET(request: NextRequest) {
  return handler(request, 'GET');
}

export async function POST(request: NextRequest) {
  return handler(request, 'POST');
}

export async function OPTIONS() {
  return new NextResponse(null, {
    status: 200,
    headers: {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, PATCH, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type, Authorization',
      'Access-Control-Max-Age': '86400',
    },
  });
}
```

### Frontend API Client Pattern
```typescript
// frontend/src/utils/apiClient.ts
const BASE_URL = ""; // Empty - relies on proxy

function normalizeUrl(baseUrl: string, endpoint: string): string {
  if (!baseUrl) {
    return endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
  }
  const base = baseUrl.replace(/\/+$/, '');
  const path = endpoint.replace(/^\/+/, '');
  return `${base}/${path}`;
}

export async function apiGet<T>(endpoint: string, params = {}): Promise<T> {
  let url = normalizeUrl(BASE_URL, endpoint);
  const queryParams = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value != null) {
      if (Array.isArray(value)) {
        value.forEach(v => queryParams.append(key, String(v)));
      } else {
        queryParams.append(key, String(value));
      }
    }
  });
  const queryString = queryParams.toString();
  if (queryString) url += `?${queryString}`;

  const res = await fetch(url);
  if (!res.ok) {
    const errorBody = await res.text();
    throw new Error(`GET ${endpoint} failed: ${res.status} - ${errorBody}`);
  }
  return res.json();
}

export async function apiPost<T>(endpoint: string, data: any, isFormData = false): Promise<T> {
  const url = normalizeUrl(BASE_URL, endpoint);
  const res = await fetch(url, {
    method: "POST",
    headers: isFormData ? undefined : { "Content-Type": "application/json" },
    body: isFormData ? data : JSON.stringify(data),
  });
  if (!res.ok) {
    const errorBody = await res.text();
    throw new Error(`POST ${endpoint} failed: ${res.status} - ${errorBody}`);
  }
  return res.json();
}
```

## Backend CORS Configuration

### FastAPI CORS (micro-ats)
```python
# backend/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Micro-ATS", debug=True)

# Allow all origins since API accessed through frontend proxy
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Error Handling

### Backend Service Unavailable
```typescript
catch (error) {
  if (error instanceof TypeError && error.message.includes('fetch failed')) {
    return NextResponse.json(
      {
        error: 'Backend service unavailable',
        details: 'Could not connect to the backend service.',
      },
      { status: 503 }
    );
  }

  return NextResponse.json(
    {
      error: 'Proxy error',
      details: error instanceof Error ? error.message : 'Unknown error',
    },
    { status: 500 }
  );
}
```

## Docker Service Communication

### docker-compose.yml
```yaml
services:
  frontend:
    environment:
      - BACKEND_URL=http://backend:8000
    depends_on:
      - backend

  backend:
    ports:
      - "8000"
    extra_hosts:
      - "host.docker.internal:host-gateway"
```

## Key Principles

### 1. Use Docker Service Names
- Frontend → Backend: `http://backend:8000`
- Never hardcode `localhost` in Docker environments

### 2. Header Filtering
- Exclude hop-by-hop headers: `connection`, `upgrade`, `transfer-encoding`
- Exclude routing headers: `host`, `content-length`
- Forward application headers: `content-type`, `authorization`

### 3. CORS Strategy
- Backend: Allow all origins (secured by proxy)
- Frontend proxy: Handle OPTIONS preflight
- Return proper CORS headers in responses

### 4. Error Handling
- 503: Backend unavailable (connection errors)
- 500: Proxy errors (unexpected issues)
- Preserve backend error codes when possible

### 5. Content Type Handling
- JSON: Parse and re-serialize for proper forwarding
- Binary: Forward as ArrayBuffer
- Form data: Preserve multipart encoding

### 6. Cache Control
```typescript
cache: 'no-store'  // Disable Next.js caching for proxy
```

## Anti-Patterns

### ❌ Hardcoded Backend URLs in Frontend
```typescript
// Wrong
const API_URL = 'http://localhost:8000';
```

### ✅ Use Proxy Pattern
```typescript
// Correct
const BASE_URL = ""; // Proxy handles routing
```

### ❌ Missing duplex for Streaming
```typescript
// Wrong - will fail with body
fetchOptions.body = request.body;
```

### ✅ Include duplex for Next.js
```typescript
// Correct
fetchOptions.body = request.body;
fetchOptions.duplex = 'half';
```

### ❌ Forwarding All Headers
```typescript
// Wrong - causes proxy errors
request.headers.forEach((value, key) => {
  headers[key] = value;
});
```

### ✅ Filter Headers
```typescript
// Correct
if (!EXCLUDED_HEADERS.has(key.toLowerCase())) {
  headers[key] = value;
}
```
