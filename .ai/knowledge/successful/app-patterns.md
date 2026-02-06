# App Patterns

## Multi-Service Architecture
```yaml
# docker-compose.yml
services:
  frontend:
    build: ./frontend
    environment:
      - NEXT_PUBLIC_API_URL=http://backend:8000
  backend:
    build: ./backend
    volumes:
      - backend_data:/app/data
    environment:
      - OPENAI_BASE_URL=${KAMIWAZA_ENDPOINT:-http://host.docker.internal:8080}
volumes:
  backend_data:
```

## Template Variables
```json
{
  "env_defaults": {
    "OAUTH_REDIRECT_URI": "https://localhost:{app_port}/api/auth/callback",
    "PUBLIC_URL": "https://localhost:{app_port}",
    "WEBHOOK_URL": "https://localhost:{app_port}/webhooks"
  }
}
```

## Configuration
```python
class Settings(BaseSettings):
    oauth_redirect_uri: str = os.getenv("OAUTH_REDIRECT_URI", "")
    kamiwaza_app_port: str = os.getenv("KAMIWAZA_APP_PORT", "8000")
    kamiwaza_endpoint: str = os.getenv("KAMIWAZA_ENDPOINT", "http://host.docker.internal:8080")
```

## LLM Service
```python
class LLMService:
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key="not-needed-kamiwaza",
            base_url=settings.kamiwaza_endpoint
        )

    async def generate_stream(self, prompt: str):
        stream = await self.client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            stream=True
        )
        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
```

## Health Check
```python
@app.get("/health")
async def health_check():
    checks = {}
    try:
        db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except:
        checks["database"] = "error"
    return {"status": "healthy", "checks": checks}
```

## Frontend API Client
```typescript
const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

class APIClient {
  async request<T>(endpoint: string, options = {}): Promise<T> {
    const response = await fetch(`${API_BASE}/api${endpoint}`, options);
    if (!response.ok) throw new Error(response.statusText);
    return response.json();
  }
}
```

## Resource Limits
```yaml
deploy:
  resources:
    limits:
      cpus: '1'
      memory: 1G
```