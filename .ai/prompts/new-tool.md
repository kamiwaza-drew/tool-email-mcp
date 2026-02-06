# Create New Tool

VARIABLES:
- NAME: {tool-name}  # must start with tool- or mcp-
- DESCRIPTION: {description}
- FUNCTIONS: {function-list}

COMMANDS:
```bash
make new TYPE=tool NAME={NAME}
```

KAMIWAZA_JSON:
```json
{
  "name": "{NAME}",
  "template_type": "tool",
  "version": "1.0.0",
  "source_type": "kamiwaza",
  "visibility": "public",
  "description": "{DESCRIPTION}",
  "category": "tool",
  "tags": ["mcp"],
  "risk_tier": 1,
  "verified": false
}
```

MCP_SERVER:
```python
# src/{NAME}_tool/server.py
from mcp import FastMCP
mcp = FastMCP("{NAME}-tool")

@mcp.tool()
async def {FUNCTION}(param: str) -> dict:
    """Description for AI"""
    return {"result": "value"}

app = mcp.create_fastapi_app()
```

DOCKERFILE:
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install -e .
EXPOSE 8000
CMD ["uvicorn", "src.{NAME}_tool.server:app", "--host", "0.0.0.0", "--port", "8000"]
```

FINALIZE:
```bash
make sync-compose
make validate
```
