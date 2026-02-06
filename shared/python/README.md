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

### Protected Endpoints

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

### Session Router (Optional)

Add standard session endpoints with one line:

```python
from fastapi import FastAPI
from kamiwaza_auth import create_session_router

app = FastAPI()
app.include_router(create_session_router())
# Adds: GET /session, GET /auth/login-url, POST /auth/logout
```

### Error Handling

```python
from kamiwaza_auth import SessionExpiredError, UpstreamAuthError

# Raise when user's session is invalid
raise SessionExpiredError("Your session has expired. Please log in again.")

# Raise when external service returns auth failure
raise UpstreamAuthError(message="External API rejected credentials", service="github")
```

### JWT Utilities

```python
from kamiwaza_auth import (
    decode_jwt_claims,
    extract_token_from_request,
    calculate_session_expires_at,
    MAX_SESSION_SECONDS,
)

# Decode JWT without verification (Kamiwaza already validated)
claims = decode_jwt_claims(token)
user_id = claims.get("sub")

# Extract token from request (cookie or header)
token = extract_token_from_request(request)

# Calculate when session expires
expires_at = calculate_session_expires_at(request)  # Unix timestamp
```

## Components

### Identity

- `Identity` - User identity dataclass with `user_id`, `email`, `name`, `roles`
- `get_identity(request)` - Extract identity from headers or API
- `require_auth` - FastAPI dependency requiring authentication
- `require_role(role)` - FastAPI dependency requiring specific role

### Client

- `KamiwazaClient` - HTTP client for Kamiwaza APIs
- `forward_auth_headers(headers)` - Extract auth headers to forward

### Errors

- `SessionExpiredError` - HTTPException with 401 status for expired sessions
- `UpstreamAuthError` - HTTPException with 502 status for external auth failures

### JWT Utilities

- `decode_jwt_claims(token)` - Decode JWT without verification
- `extract_token_from_request(request)` - Get token from cookie/header
- `calculate_session_expires_at(request)` - Calculate session expiry timestamp
- `MAX_SESSION_SECONDS` - Default session duration (28800 = 8 hours)

### Session Router

- `create_session_router(prefix?, tags?)` - Create router with session endpoints:
  - `GET /session` - Get current session info
  - `GET /auth/login-url` - Build login URL with redirect
  - `POST /auth/logout` - Logout and get redirect URLs

### Config

- `AuthConfig` - Configuration from environment variables

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `KAMIWAZA_API_URL` | Kamiwaza API URL | `http://host.docker.internal:7777/api` |
| `KAMIWAZA_ENDPOINT` | OpenAI endpoint | `http://host.docker.internal:8080` |
| `KAMIWAZA_PUBLIC_API_URL` | Public API URL for redirects | `https://localhost/api` |
| `AUTH_VALIDATE_URL` | Auth validation URL | `{API_URL}/auth/validate` |
| `KAMIWAZA_USE_AUTH` | Enable auth | `true` |

## Documentation

See [Auth Integration Guide](../../docs/auth-integration-guide.md) for complete documentation.
