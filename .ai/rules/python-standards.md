# Python Standards - Kamiwaza Extensions

## FastAPI Structure
PATH: backend/app/main.py, backend/app/api/, backend/app/core/, backend/app/models/
PATTERN: FastAPI with CORS, health check at /health
ROUTERS: app.include_router(router, prefix="/api")

## Configuration
```python
from pydantic_settings import BaseSettings
class Settings(BaseSettings):
    database_url: str = "sqlite:///./data/app.db"
    kamiwaza_endpoint: str = os.getenv("KAMIWAZA_ENDPOINT", "http://host.docker.internal:8080")
    kamiwaza_app_port: str = os.getenv("KAMIWAZA_APP_PORT", "8000")
    oauth_redirect_uri: str = os.getenv("OAUTH_REDIRECT_URI", "")
settings = Settings()
```

## Pydantic V1 (Current)
```python
class Schema(BaseModel):
    id: UUID
    name: str = Field(..., min_length=1)
    class Config:
        orm_mode = True  # REQUIRED
```
CONVERT: [Schema.from_orm(obj) for obj in query.all()]

## Database Patterns
SQLITE_DEFAULT: sqlite:///./data/app.db
UUID_COMPAT: from kamiwaza.lib.util import get_uuid_column_type; DBUUID = get_uuid_column_type()
UUID_SQL: text("SELECT * WHERE id = :id"), {'id': str(uuid_obj)}

## MCP Tool Pattern
```python
from mcp import FastMCP
mcp = FastMCP("tool-name")

@mcp.tool()
async def function_name(input: InputModel) -> dict:
    """AI description"""
    return {"result": value}

app = mcp.create_fastapi_app()
```

## Kamiwaza LLM
```python
client = openai.AsyncOpenAI(
    api_key="not-needed-kamiwaza",
    base_url=settings.kamiwaza_endpoint
)
response = await client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": prompt}]
)
```

## App Garden Variables
RUNTIME: KAMIWAZA_APP_PORT, KAMIWAZA_APP_URL, KAMIWAZA_DEPLOYMENT_ID
MODEL: KAMIWAZA_MODEL_PORT, KAMIWAZA_MODEL_URL (if deployed)
TEMPLATE: Use {app_port} in kamiwaza.json env_defaults

## Error Handling
CUSTOM: class ServiceException(Exception): pass
NOT_FOUND: raise ResourceNotFoundException(f"Resource {id} not found")
VALIDATION: Use Pydantic schemas for input validation

## Docker Requirements
HEALTHCHECK: CMD curl -f http://localhost:8000/health || exit 1
NON_ROOT: RUN useradd -m appuser && chown -R appuser /app; USER appuser
EXPOSE: EXPOSE 8000

## Security
NO_LOG: passwords, tokens, keys
VALIDATE: All inputs with Pydantic
SQL: Parameterized queries only
SANITIZE: Error messages before returning