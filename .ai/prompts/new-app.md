# Create New App

VARIABLES:
- NAME: {app-name}
- TYPE: {app-type}
- STACK: {tech-stack}
- DESCRIPTION: {description}

COMMANDS:
```bash
make new TYPE=app NAME={NAME}
```

KAMIWAZA_JSON:
```json
{
  "name": "{NAME}",
  "version": "1.0.0",
  "source_type": "kamiwaza",
  "visibility": "public",
  "description": "{DESCRIPTION}",
  "risk_tier": 1,
  "verified": false,
  "env_defaults": {
    "CALLBACK_URL": "https://localhost:{app_port}/callback",
    "PUBLIC_URL": "https://localhost:{app_port}"
  },
  "preferred_model_type": "reasoning"
}
```

DOCKER_COMPOSE:
```yaml
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

FINALIZE:
```bash
make sync-compose
make validate
```