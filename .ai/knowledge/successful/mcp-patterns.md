# MCP Tool Patterns

## Basic MCP Server
```python
from mcp import FastMCP
mcp = FastMCP("tool-name")

@mcp.tool()
async def function_name(input: InputModel) -> dict:
    """AI description"""
    return {"result": value}

app = mcp.create_fastapi_app()

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
```

## Stateful Tool Manager
```python
class ToolManager:
    def __init__(self):
        self.state = None
        self._lock = asyncio.Lock()

    async def ensure_state(self):
        async with self._lock:
            if not self.state:
                self.state = await initialize()

manager = ToolManager()

@mcp.tool()
async def use_state():
    await manager.ensure_state()
    return manager.state
```

## External API Integration
```python
class APIClient:
    def __init__(self):
        self.base_url = os.getenv("API_BASE_URL")
        self._client = None

    async def request_with_retry(self, endpoint, retries=3):
        for attempt in range(retries):
            try:
                response = await self._client.get(endpoint)
                response.raise_for_status()
                return response.json()
            except Exception:
                if attempt < retries - 1:
                    await asyncio.sleep(2 ** attempt)
                else:
                    raise
```

## Docker Pattern
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install -e .
USER appuser
EXPOSE 8000
CMD ["uvicorn", "src.server:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Testing Pattern
```python
@pytest.mark.asyncio
async def test_tool():
    result = await mcp.call_tool("function", {"param": "value"})
    assert result["status"] == "success"
```