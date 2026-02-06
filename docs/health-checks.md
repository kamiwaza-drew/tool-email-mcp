# Health Checks Guide

This guide explains how Kamiwaza verifies that your extension is healthy and ready to serve traffic after deployment.

## Overview

Kamiwaza uses a **two-phase health verification** process:

1. **Container Health Check** - Docker's native `HEALTHCHECK` mechanism
2. **HTTP Probe** - HTTPS request through Traefik routing

Both phases must pass for a deployment to be marked as `DEPLOYED`. If either fails, the deployment status becomes `FAILED`.

## Deployment Status Lifecycle

```
UNINITIALIZED → PULLING_IMAGES → REQUESTED → DEPLOYED
                                           ↘ FAILED
```

| Status | Meaning |
|--------|---------|
| `UNINITIALIZED` | Deployment record created |
| `PULLING_IMAGES` | Docker images being pulled |
| `REQUESTED` | Containers starting |
| `DEPLOYED` | All health checks passed, app ready |
| `FAILED` | Health check or startup failed |

## Phase 1: Container Health Check

Kamiwaza polls Docker's native health status via `docker inspect` for each container.

### Timing

| Parameter | Value |
|-----------|-------|
| Timeout | 180 seconds |
| Poll interval | 5 seconds |
| Max attempts | 36 |

### Behavior by Container State

| Docker Health Status | Kamiwaza Action |
|---------------------|-----------------|
| `healthy` | Continue to next container |
| `unhealthy` | **Deployment fails immediately** |
| `starting` | Keep polling until timeout |
| No health check defined | **Skip wait, continue immediately** |

### Multi-Container Apps

For apps with multiple containers (e.g., frontend + backend):

- **All containers are checked sequentially**
- Containers without `HEALTHCHECK` are skipped
- First unhealthy container fails the entire deployment
- No partial success - either all pass or deployment fails

**Example timeline for a 2-container app:**
```
Container 1 (frontend): wait up to 180s → healthy ✓
Container 2 (backend):  wait up to 180s → healthy ✓
→ Proceed to Phase 2
```

### Defining Container Health Checks

Add a `HEALTHCHECK` instruction to your Dockerfile:

```dockerfile
# Simple HTTP health check
HEALTHCHECK --interval=10s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# For containers without curl
HEALTHCHECK --interval=10s --timeout=5s --start-period=30s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:8000/health || exit 1

# For Python apps with httpx
HEALTHCHECK --interval=10s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health').raise_for_status()"
```

**Parameters explained:**

| Parameter | Recommended | Description |
|-----------|-------------|-------------|
| `--interval` | 10s | Time between health checks |
| `--timeout` | 5s | Max time for check to complete |
| `--start-period` | 30s | Grace period before checks count as failures |
| `--retries` | 3 | Consecutive failures before unhealthy |

### Health Check Endpoint Implementation

Your app should expose a `/health` endpoint:

**FastAPI (Python):**
```python
@app.get("/health")
async def health_check():
    checks = {}

    # Check database connectivity
    try:
        db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {str(e)}"

    # Check external dependencies
    try:
        async with httpx.AsyncClient() as client:
            await client.get("http://dependency/health", timeout=2.0)
        checks["dependency"] = "ok"
    except Exception:
        checks["dependency"] = "degraded"

    status = "healthy" if checks.get("database") == "ok" else "unhealthy"
    return {"status": status, "checks": checks}
```

**Next.js (TypeScript):**
```typescript
// app/api/health/route.ts
import { NextResponse } from 'next/server';

export async function GET() {
    const checks: Record<string, string> = {};

    // Check backend connectivity
    try {
        const res = await fetch('http://backend:8000/health', {
            signal: AbortSignal.timeout(2000)
        });
        checks.backend = res.ok ? 'ok' : 'error';
    } catch {
        checks.backend = 'unreachable';
    }

    return NextResponse.json({
        status: 'healthy',
        checks
    });
}
```

## Phase 2: HTTP Probe

After container health checks pass, Kamiwaza sends HTTPS requests through Traefik to verify the app is accessible.

### Timing

| Parameter | Default | Environment Variable |
|-----------|---------|----------------------|
| Timeout | 60 seconds | `KAMIWAZA_EXTENSION_PROBE_TIMEOUT` |
| Retry interval | 1.0 second | `KAMIWAZA_EXTENSION_PROBE_INTERVAL` |

### Probe Behavior

- Sends HTTPS GET requests to your app via Traefik
- Tests the root path `/` and path-based routing URL
- **Success**: Any HTTP status code < 400
- **Failure**: Status >= 400, connection refused, or timeout

### Service and Tool Deployments

Extensions with names starting with `service-`, `tool-`, or `mcp-` **skip the HTTP probe phase**. This is because services and tools may not serve HTTP on the root path.

If your extension is a service or tool:
1. Name it with `service-`, `tool-`, or `mcp-` prefix (e.g., `service-milvus`, `tool-code-analyzer`)
2. Container health check is still performed if defined
3. HTTP probe is automatically skipped

## Recommended Configuration

### For Apps (Web Interfaces)

```dockerfile
# Dockerfile
FROM python:3.11-slim
# ... your setup ...

HEALTHCHECK --interval=10s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```python
# app/main.py
@app.get("/health")
async def health():
    return {"status": "healthy"}
```

### For Tools and Services (MCP Servers / Infra)

```dockerfile
# Dockerfile
FROM python:3.11-slim
# ... your setup ...

# Health check still recommended for container readiness
HEALTHCHECK --interval=10s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000
CMD ["uvicorn", "src.server:app", "--host", "0.0.0.0", "--port", "8000"]
```

Name your extension with `service-`, `tool-`, or `mcp-` prefix to skip HTTP probe.

### For Multi-Container Apps

Each container with a health check should define one in its Dockerfile:

```yaml
# docker-compose.yml
services:
  frontend:
    build: ./frontend
    # Dockerfile includes HEALTHCHECK

  backend:
    build: ./backend
    # Dockerfile includes HEALTHCHECK

  worker:
    build: ./worker
    # No HEALTHCHECK defined - Kamiwaza skips wait for this container
```

## Troubleshooting

### Deployment Stuck in REQUESTED

**Symptoms:** Deployment never reaches DEPLOYED, eventually times out.

**Causes:**
1. Container health check failing
2. App not starting within `--start-period`
3. Health endpoint returning errors

**Debug steps:**
```bash
# Check container health status
docker inspect <container_id> | jq '.[0].State.Health'

# View health check logs
docker inspect <container_id> | jq '.[0].State.Health.Log'

# Check container logs
docker logs <container_id>
```

### Deployment FAILED with "unhealthy"

**Symptoms:** Deployment fails with message about container being unhealthy.

**Causes:**
1. Health check command failing
2. App crashing on startup
3. Dependencies not ready

**Debug steps:**
```bash
# Check what the health check is trying to do
docker inspect <container_id> | jq '.[0].Config.Healthcheck'

# Run the health check manually
docker exec <container_id> curl -f http://localhost:8000/health

# Check if the app is running
docker exec <container_id> ps aux
```

### HTTP Probe Timeout

**Symptoms:** Container health passes but deployment still fails.

**Causes:**
1. App not responding on expected port
2. Traefik routing misconfigured
3. App returning HTTP errors on root path

**Debug steps:**
```bash
# Test the app directly
curl -k https://localhost:<assigned_port>/

# Check Traefik logs
docker logs traefik

# Verify port mappings
docker port <container_id>
```

### No Health Check Defined

If you don't define a `HEALTHCHECK` in your Dockerfile:

- **Phase 1 is skipped** for that container
- Kamiwaza proceeds directly to Phase 2 (HTTP probe)
- App must respond to HTTP requests within 60 seconds of container start

This can be risky because:
- Your app may not be fully initialized when HTTP probe starts
- Database migrations may still be running
- Connections to external services may not be established

**Recommendation:** Always define a `HEALTHCHECK` in your Dockerfile.

## Environment Variables

Operators can tune probe timing via environment variables on the Kamiwaza server:

| Variable | Default | Description |
|----------|---------|-------------|
| `KAMIWAZA_EXTENSION_PROBE_TIMEOUT` | 60 | HTTP probe timeout (seconds) |
| `KAMIWAZA_EXTENSION_PROBE_INTERVAL` | 1.0 | HTTP probe retry interval (seconds) |

Container health check timing (180s timeout, 5s poll) is currently hardcoded.

## Best Practices

1. **Always define HEALTHCHECK** - Don't rely on HTTP probe alone
2. **Use start-period** - Give your app time to initialize
3. **Check dependencies** - Health endpoint should verify database, cache, etc.
4. **Return fast** - Health checks should complete in < 5 seconds
5. **Be specific** - Return detailed status for debugging
6. **Graceful degradation** - Consider returning 200 with degraded status for non-critical failures

## Quick Reference

| Phase | Timeout | What It Checks | Skip Condition |
|-------|---------|----------------|----------------|
| Container Health | 180s | Docker HEALTHCHECK | No HEALTHCHECK defined |
| HTTP Probe | 60s | HTTPS via Traefik | Name starts with `service-`, `tool-`, or `mcp-` |

| Deployment Status | Meaning |
|-------------------|---------|
| `DEPLOYED` | Both phases passed |
| `FAILED` | Any phase failed |
| `REQUESTED` | Health checks in progress |
