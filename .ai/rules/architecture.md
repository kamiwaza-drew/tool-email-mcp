# Architecture Rules - Kamiwaza Extensions

## Extension Types
TYPE: app
STRUCTURE: apps/{name}/frontend/, apps/{name}/backend/, apps/{name}/docker-compose.yml
SERVICES: multi-container (frontend, backend, optional db)

TYPE: service
STRUCTURE: services/{name}/docker-compose.yml (optional backend/ for source)
SERVICES: App Garden backend utilities; name prefix service-; template_type=service

TYPE: tool
STRUCTURE: tools/{name}/src/, tools/{name}/Dockerfile
SERVICES: single MCP server, port 8000, path /mcp

## Required Files
METADATA: kamiwaza.json (version, risk_tier, env_defaults)
DOCKER: Dockerfile, docker-compose.yml, docker-compose.appgarden.yml (generated)
DOCS: README.md

## kamiwaza.json
```json
{
  "name": "{ExtensionName}",
  "version": "X.Y.Z",
  "source_type": "kamiwaza",
  "risk_tier": 0|1|2,
  "env_defaults": {
    "VAR": "value",
    "CALLBACK": "https://localhost:{app_port}/callback"
  }
}
```

## Template Variables
AVAILABLE: {app_port}, {model_port}, {deployment_id}, {app_name}
SYSTEM_PROVIDED: KAMIWAZA_APP_PORT, KAMIWAZA_MODEL_PORT, KAMIWAZA_DEPLOYMENT_ID

## Docker Rules
NO_HOST_PORTS: ports: ["8000"] not "8000:8000"
NO_BIND_MOUNTS: volumes: ["data:/app/data"] not "./data:/app/data"
RESOURCE_LIMITS: deploy.resources.limits.cpus="2", memory="2G"
EXTRA_HOSTS: "host.docker.internal:host-gateway"

## Image Management
NAMING: kamiwazaai/{extension-name}-{service-name}:{version}[-stage]
VERSION_SOURCE: kamiwaza.json version field (single source of truth)
AUTO_UPDATE: sync-compose.py updates tags and generates image fields
BUILD_REPLACEMENT: When build field removed, image field auto-generated
EXTERNAL_IMAGES: postgres, redis, etc. kept unchanged
STAGE_TAGS: dev={version}-dev, stage={version}-stage, prod={version}

### Docker Compose Pattern
```yaml
# docker-compose.yml (source for local dev)
services:
  backend:
    build:
      context: .
      dockerfile: backend/Dockerfile
    image: kamiwazaai/myapp-backend:1.0.0  # Optional but recommended

  frontend:
    build:
      context: .
      dockerfile: frontend/Dockerfile
    # Image will be auto-generated if omitted

# docker-compose.appgarden.yml (auto-generated)
services:
  backend:
    image: kamiwazaai/myapp-backend:1.0.0  # From kamiwaza.json version
    # build field removed

  frontend:
    image: kamiwazaai/myapp-frontend:1.0.0  # Auto-generated
```

### Version Synchronization
- kamiwaza.json: "version": "1.0.0"
- Docker tags: 1.0.0 (no 'v' prefix)
- Stage suffix: -dev, -stage, or none (prod)
- Updated by: make sync-compose
- Used by: make build, make push

## MCP Tool Pattern
```python
from mcp import FastMCP
mcp = FastMCP("tool-name")

@mcp.tool()
async def function_name(param: str) -> dict:
    """Description for AI"""
    return {"result": "value"}

app = mcp.create_fastapi_app()
```

## App Pattern
FRONTEND_ENV: NEXT_PUBLIC_API_URL=http://backend:8000
BACKEND_ENV: OPENAI_BASE_URL=${KAMIWAZA_ENDPOINT:-http://host.docker.internal:8080}
BACKEND_ENV: OPENAI_API_KEY=${OPENAI_API_KEY:-not-needed-kamiwaza}

## Networking Patterns

### Frontend-Backend Proxy
```typescript
// frontend/src/app/api/[...path]/route.ts
const BACKEND_URL = process.env.BACKEND_URL || 'http://backend:8000';

async function handler(request: NextRequest, method: string) {
  const targetUrl = buildTargetUrl(request);
  const response = await fetch(targetUrl, {
    method,
    headers: getForwardHeaders(request),
    cache: 'no-store',
  });
  return NextResponse.json(await response.json());
}
```

EXCLUDED_HEADERS: host, connection, content-length, transfer-encoding, upgrade
FORWARD_HEADERS: content-type, authorization, custom headers
CORS_HANDLING: Backend allows all origins, proxy handles OPTIONS

### API Client Pattern
```typescript
// frontend/src/utils/apiClient.ts
const BASE_URL = ""; // Empty - uses proxy

export async function apiGet<T>(endpoint: string): Promise<T> {
  const url = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
  const res = await fetch(url);
  return res.json();
}
```

### SSE Streaming (Real-Time)
```typescript
// Server-side (Next.js API route)
import { createDataStream, streamText } from 'ai';

const stream = createDataStream({
  execute: async (dataStream) => {
    const result = streamText({
      model: kamiwazaModel(port, modelId),
      messages: [...],
      onFinish: async ({ response }) => {
        dataStream.writeData({
          type: 'custom-event',
          content: data,
        });
      },
    });
    result.mergeIntoDataStream(dataStream);
  },
});

return new Response(stream);
```

### Docker Service Communication
```yaml
services:
  frontend:
    environment:
      - BACKEND_URL=http://backend:8000
    depends_on:
      - backend

  backend:
    ports:
      - "8000"  # Internal only
    extra_hosts:
      - "host.docker.internal:host-gateway"
    environment:
      - KAMIWAZA_ENDPOINT=http://host.docker.internal:8080
```

SERVICE_NAMES: Use Docker service names (backend, frontend, db)
HOST_ACCESS: Use host.docker.internal for Kamiwaza LLM
NO_LOCALHOST: Never use localhost in Docker environment
REFERENCES: @.ai/knowledge/successful/networking-patterns.md, @.ai/knowledge/successful/realtime-connections.md

## Validation Commands
CREATE: make new TYPE={app|service|tool} NAME={name}
SYNC: make sync-compose
VALIDATE: make validate
BUILD: make build TYPE={app|service|tool} NAME={name}
TEST: make test TYPE={app|service|tool} NAME={name}

## Environment Patterns
KAMIWAZA_ACCESS: KAMIWAZA_ENDPOINT, KAMIWAZA_API_URI
MODEL_ACCESS: OPENAI_BASE_URL=$KAMIWAZA_ENDPOINT, OPENAI_API_KEY=not-needed-kamiwaza
DYNAMIC_CONFIG: Use {app_port} in env_defaults for runtime URLs

## Anti-Patterns
FORBIDDEN: Hardcoded ports, bind mounts, missing resource limits
FORBIDDEN: Build contexts in appgarden.yml, hardcoded localhost URLs
FORBIDDEN: Synchronous MCP operations, shared dependencies between extensions
