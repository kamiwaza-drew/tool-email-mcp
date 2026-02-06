# Testing Rules - Kamiwaza Extensions

## Validation Checklist
[ ] kamiwaza.json valid
[ ] Docker builds succeed
[ ] docker-compose.yml works locally
[ ] App Garden config generated (make sync-compose)
[ ] No hardcoded ports/secrets
[ ] Resource limits defined
[ ] Health endpoint returns 200 (apps only)
[ ] Kamiwaza LLM calls work
[ ] All tests pass (make test)

## Commands
VALIDATE: make validate-ext TYPE={type} NAME={name}
TEST: make test TYPE={type} NAME={name}
LOCAL: cd {path} && docker-compose up --build
HEALTH: curl http://localhost:8000/health
CI: make ci-validate

## Test Structure
APP: backend/tests/test_api.py, backend/tests/test_services.py
TOOL: tests/test_server.py, tests/test_functions.py
FIXTURE: tests/conftest.py

## Required Tests
```python
# Health endpoint (apps only)
def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200

# MCP tool registration (tools only)
@pytest.mark.asyncio
async def test_tool_function():
    result = await mcp.call_tool("function_name", {"param": "value"})
    assert result["status"] == "success"
```

## Mock Patterns
```python
# Mock Kamiwaza LLM
with patch('openai.AsyncOpenAI') as mock:
    mock.return_value.chat.completions.create.return_value.choices[0].message.content = "response"

# Mock external API
with patch('aiohttp.ClientSession') as mock:
    mock.return_value.__aenter__.return_value.get.return_value.__aenter__.return_value.json.return_value = {"data": "test"}
```

## Common Failures
PORTS: Use ports: ["8000"] not "8000:8000"
HEALTH: Apps must have @app.get("/health")
KAMIWAZA: Use KAMIWAZA_ENDPOINT env var
PYDANTIC: Convert SQLAlchemy objects with .from_orm()

## Test Markers
ASYNC: @pytest.mark.asyncio
SLOW: @pytest.mark.slow
DOCKER: @pytest.mark.docker

## Testing Workflow

### Run Extension Tests
```bash
# Full test suite
make test TYPE={type} NAME={name}

# Local manual testing
cd {path}
docker-compose up --build
curl http://localhost:8000/health
```

### Test Development
1. Write test cases in tests/ directory
2. Follow test structure patterns above
3. Use appropriate mocks for external dependencies
4. Run tests locally before committing
5. Ensure all tests pass in CI pipeline

### Debugging Test Failures
1. Check ports available: lsof -ti:{port}
2. Review test output for specific failures
3. Run single test: pytest tests/test_file.py::test_name
4. Check service logs: docker-compose logs {service}
5. Verify environment configuration

See development-lifecycle.md for full CI/release pipeline.
