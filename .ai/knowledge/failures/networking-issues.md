# Networking Issues - Kamiwaza Extensions

## Proxy Issues

### PROBLEM: Hardcoded localhost in Frontend
```typescript
// ❌ Wrong
const API_URL = 'http://localhost:8000';
fetch(`${API_URL}/api/users`);
```

**Symptoms:**
- Works in development, fails in Docker
- CORS errors in production
- 404 errors when deployed

**SOLUTION:**
```typescript
// ✅ Correct - Use proxy pattern
const BASE_URL = ""; // Empty - relies on Next.js API route
fetch('/api/users'); // Proxied to backend
```

### PROBLEM: Missing duplex for Request Body
```typescript
// ❌ Wrong
const response = await fetch(url, {
  method: 'POST',
  body: request.body,
});
```

**Symptoms:**
- Error: "RequestInit: duplex option is required"
- POST/PUT requests fail
- Only occurs in Next.js environment

**SOLUTION:**
```typescript
// ✅ Correct
const response = await fetch(url, {
  method: 'POST',
  body: request.body,
  // @ts-expect-error - duplex required by Next.js
  duplex: 'half',
});
```

### PROBLEM: Forwarding Hop-by-Hop Headers
```typescript
// ❌ Wrong
request.headers.forEach((value, key) => {
  proxyHeaders[key] = value;
});
```

**Symptoms:**
- 502 Bad Gateway errors
- Connection reset errors
- Transfer encoding errors

**SOLUTION:**
```typescript
// ✅ Correct
const EXCLUDED_HEADERS = new Set([
  'host', 'connection', 'content-length',
  'transfer-encoding', 'upgrade', 'http2-settings',
  'te', 'trailer',
]);

request.headers.forEach((value, key) => {
  if (!EXCLUDED_HEADERS.has(key.toLowerCase())) {
    proxyHeaders[key] = value;
  }
});
```

### PROBLEM: Missing CORS Preflight Handler
```typescript
// ❌ Wrong - No OPTIONS handler
export async function POST(request: NextRequest) {
  // Handle POST only
}
```

**Symptoms:**
- CORS errors on first request
- Preflight requests fail with 405
- Works on second try (cached)

**SOLUTION:**
```typescript
// ✅ Correct
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

## Docker Service Communication

### PROBLEM: Using localhost in Docker
```yaml
# ❌ Wrong
services:
  frontend:
    environment:
      - BACKEND_URL=http://localhost:8000
```

**Symptoms:**
- Connection refused errors
- Frontend can't reach backend
- Works outside Docker, fails inside

**SOLUTION:**
```yaml
# ✅ Correct - Use Docker service names
services:
  frontend:
    environment:
      - BACKEND_URL=http://backend:8000
    depends_on:
      - backend

  backend:
    ports:
      - "8000"
```

### PROBLEM: Exposing Host Ports
```yaml
# ❌ Wrong - Exposes on host
services:
  backend:
    ports:
      - "8000:8000"
```

**Symptoms:**
- Port conflicts in App Garden
- Cannot run multiple instances
- Violates App Garden rules

**SOLUTION:**
```yaml
# ✅ Correct - Internal port only
services:
  backend:
    ports:
      - "8000"
```

### PROBLEM: Missing host.docker.internal
```python
# ❌ Wrong
KAMIWAZA_ENDPOINT = "http://localhost:8080"
```

**Symptoms:**
- Can't access Kamiwaza LLM from Docker
- Connection refused to host services
- Works on host, fails in container

**SOLUTION:**
```yaml
# docker-compose.yml
services:
  backend:
    extra_hosts:
      - "host.docker.internal:host-gateway"
    environment:
      - KAMIWAZA_ENDPOINT=http://host.docker.internal:8080
```

## Streaming Issues

### PROBLEM: Missing Stream Cleanup
```typescript
// ❌ Wrong - Memory leak
useEffect(() => {
  const processStream = () => {
    dataStream.forEach(delta => {
      updateState(delta);
    });
  };
  processStream();
}); // Missing dependency array and cleanup
```

**Symptoms:**
- Memory leaks on navigation
- Duplicate stream processing
- State updates after unmount

**SOLUTION:**
```typescript
// ✅ Correct
useEffect(() => {
  if (!dataStream) return;

  const processStream = () => {
    const newDeltas = dataStream.slice(lastProcessedIndex.current + 1);
    lastProcessedIndex.current = dataStream.length - 1;
    newDeltas.forEach(delta => updateState(delta));
  };

  processStream();

  return () => {
    // Cleanup if needed
  };
}, [dataStream]); // Proper dependencies
```

### PROBLEM: Blocking onFinish
```typescript
// ❌ Wrong - Blocks stream completion
const result = streamText({
  onFinish: async ({ response }) => {
    await saveToDatabase(response); // Blocks stream
    await updateSearch(response);   // Blocks stream
  },
});
```

**Symptoms:**
- Slow stream completion
- UI hangs waiting for database
- Poor user experience

**SOLUTION:**
```typescript
// ✅ Correct - Non-blocking
import { after } from 'next/server';

const result = streamText({
  onFinish: async ({ response }) => {
    // Quick operations in main thread
    const messageId = response.messages[0].id;

    // Background operations
    after(async () => {
      await saveToDatabase(response);
      await updateSearch(response);
    });
  },
});
```

### PROBLEM: Missing Redis Graceful Degradation
```typescript
// ❌ Wrong - Crashes without Redis
const streamContext = createResumableStreamContext({
  waitUntil: after,
});

return new Response(
  await streamContext.resumableStream(streamId, () => stream),
);
```

**Symptoms:**
- App crashes when REDIS_URL not set
- Works in production, fails locally
- No fallback for simple streaming

**SOLUTION:**
```typescript
// ✅ Correct - Graceful degradation
let globalStreamContext: ResumableStreamContext | null = null;

function getStreamContext() {
  if (!globalStreamContext) {
    try {
      globalStreamContext = createResumableStreamContext({
        waitUntil: after,
      });
    } catch (error: any) {
      if (error.message.includes('REDIS_URL')) {
        console.log('Resumable streams disabled - no Redis');
      } else {
        console.error(error);
      }
    }
  }
  return globalStreamContext;
}

const streamContext = getStreamContext();

if (streamContext) {
  return new Response(
    await streamContext.resumableStream(streamId, () => stream),
  );
} else {
  return new Response(stream); // Fallback to simple stream
}
```

### PROBLEM: Unhandled Stream Errors
```typescript
// ❌ Wrong - No error handling
const stream = createDataStream({
  execute: async (dataStream) => {
    const result = streamText({ /* ... */ });
    result.mergeIntoDataStream(dataStream);
  },
});
```

**Symptoms:**
- Silent failures
- User sees loading state forever
- No error feedback

**SOLUTION:**
```typescript
// ✅ Correct - Error handling
const stream = createDataStream({
  execute: async (dataStream) => {
    try {
      const result = streamText({ /* ... */ });
      result.mergeIntoDataStream(dataStream);
    } catch (error) {
      console.error('Stream error:', error);
      dataStream.writeData({
        type: 'error',
        content: error.message,
      });
      throw error;
    }
  },
  onError: (error) => {
    console.error('Stream error:', error);
    return 'An error occurred during streaming';
  },
});
```

## CORS Issues

### PROBLEM: Restrictive CORS in Backend
```python
# ❌ Wrong - Too restrictive
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)
```

**Symptoms:**
- CORS errors in production
- Custom headers rejected
- OPTIONS requests fail

**SOLUTION:**
```python
# ✅ Correct - Allow all (proxied access)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Reasoning:** Backend accessed through frontend proxy, so allow all origins

### PROBLEM: Missing Content-Type Headers
```typescript
// ❌ Wrong
const response = await fetch('/api/users', {
  method: 'POST',
  body: JSON.stringify(data),
});
```

**Symptoms:**
- 415 Unsupported Media Type
- Backend can't parse JSON
- Request body empty

**SOLUTION:**
```typescript
// ✅ Correct
const response = await fetch('/api/users', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(data),
});
```

## Cache Issues

### PROBLEM: Next.js Caching Proxy Requests
```typescript
// ❌ Wrong - Caches responses
const response = await fetch(targetUrl, {
  method: 'GET',
  headers: forwardHeaders,
});
```

**Symptoms:**
- Stale data returned
- Updates not reflected
- Works after hard refresh

**SOLUTION:**
```typescript
// ✅ Correct - Disable caching
const response = await fetch(targetUrl, {
  method: 'GET',
  headers: forwardHeaders,
  cache: 'no-store',
});
```

## Debugging Commands

### Check Service Connectivity
```bash
# From frontend container
docker-compose exec frontend curl http://backend:8000/health

# From host
curl http://localhost:3000/api/health

# Check DNS resolution
docker-compose exec frontend nslookup backend
```

### Monitor Proxy Traffic
```bash
# View proxy logs
docker-compose logs -f frontend | grep "API Proxy"

# Check backend logs
docker-compose logs -f backend
```

### Test CORS
```bash
# Preflight request
curl -X OPTIONS http://localhost:3000/api/users \
  -H "Origin: http://localhost:3000" \
  -H "Access-Control-Request-Method: POST" \
  -v
```

### Verify Headers
```bash
# Check forwarded headers
curl http://localhost:3000/api/debug/headers -v
```
