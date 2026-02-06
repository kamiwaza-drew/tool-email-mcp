# Add Endpoint

VARIABLES:
- METHOD: {GET|POST|PUT|DELETE}
- PATH: {endpoint-path}
- EXTENSION_NAME: {extension-name}
- DESCRIPTION: {what-it-does}

ROUTER_PATTERN:
```python
# api/routes/{resource}.py
from fastapi import APIRouter, Depends, HTTPException
router = APIRouter(prefix="/{resource}", tags=["{resource}"])

@router.{METHOD}("/{PATH}")
async def {endpoint_name}(
    request: {RequestSchema},
    service: Service = Depends()
):
    """Endpoint description"""
    return await service.{method}(request)
```

SCHEMA_PATTERN:
```python
# schemas/{resource}.py
from pydantic import BaseModel
class {Request}Schema(BaseModel):
    field: str
```

TEST_PATTERN:
```python
# tests/test_api.py
def test_{endpoint_name}():
    response = client.{method}("/api/{path}", json={})
    assert response.status_code == 200
```

LLM_INTEGRATION:
```python
client = AsyncOpenAI(
    api_key="not-needed-kamiwaza",
    base_url=settings.kamiwaza_endpoint
)
```

ERROR_CODES:
- 400: Validation error
- 404: Not found
- 409: Conflict
- 500: Server error