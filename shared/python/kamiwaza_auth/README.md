# Kamiwaza Auth - Python

Forward auth utilities for FastAPI backends in Kamiwaza App Garden.

## Installation

```bash
# Install as editable package
pip install -e .

# Or copy to your project
cp -r kamiwaza_auth /path/to/your/backend/
```

## Quick Start

```python
from fastapi import FastAPI, Depends, Request
from kamiwaza_auth import Identity, require_auth, get_identity, KamiwazaClient

app = FastAPI()

# Protected endpoint
@app.get("/api/me")
async def get_me(identity: Identity = Depends(require_auth)):
    return {"email": identity.email}

# Optional auth
@app.get("/api/data")
async def get_data(request: Request):
    identity = await get_identity(request)
    return {"authenticated": identity.is_authenticated}

# Call Kamiwaza APIs
@app.get("/api/models")
async def list_models(request: Request):
    client = KamiwazaClient.from_env()
    return await client.get_models(request.headers)
```

## Components

- `Identity` - User identity dataclass
- `get_identity(request)` - Extract identity from headers or API
- `require_auth` - FastAPI dependency requiring authentication
- `require_role(role)` - FastAPI dependency requiring specific role
- `KamiwazaClient` - HTTP client for Kamiwaza APIs
- `forward_auth_headers(headers)` - Extract auth headers to forward
- `AuthConfig` - Configuration from environment variables

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `KAMIWAZA_API_URL` | Kamiwaza API URL | `http://host.docker.internal:7777/api` |
| `KAMIWAZA_ENDPOINT` | OpenAI endpoint | `http://host.docker.internal:8080` |
| `AUTH_VALIDATE_URL` | Auth validation URL | `{API_URL}/auth/validate` |
| `KAMIWAZA_USE_AUTH` | Enable auth | `true` |

## Documentation

See [Auth Integration Guide](../../docs/auth-integration-guide.md) for complete documentation.
