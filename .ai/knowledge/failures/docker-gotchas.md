# Docker Gotchas

## Port Issues
PROBLEM: ports: ["3000:3000"]
SOLUTION: ports: ["${SERVICE_PORT}:3000"]

## Volume Issues
PROBLEM: volumes: ["./data:/app/data"]
SOLUTION: volumes: ["app_data:/app/data"]

## Resource Limits
PROBLEM: No limits defined
SOLUTION:
```yaml
deploy:
  resources:
    limits:
      cpus: '1'
      memory: 1G
```

## Host Access
PROBLEM: http://localhost:8080
SOLUTION:
```yaml
extra_hosts:
  - "host.docker.internal:host-gateway"
environment:
  - OPENAI_BASE_URL=http://host.docker.internal:8080
```

## App Garden Issues
PROBLEM: build: ./backend (without image field)
SOLUTION:
```yaml
# Option 1: Add image field in docker-compose.yml
services:
  backend:
    build: ./backend
    image: kamiwazaai/myapp-backend:1.0.0

# Option 2: Let sync-compose auto-generate (recommended)
# Just run: make sync-compose
# Result: image: kamiwazaai/{extension-name}-{service-name}:{version}
```

## Version Management Issues
PROBLEM: Image tags don't match kamiwaza.json version
SOLUTION: Run `make sync-compose` to auto-update from kamiwaza.json

PROBLEM: Manually maintaining versions in multiple files
SOLUTION: Only update version in kamiwaza.json, sync-compose handles the rest

## Health Checks
REQUIRED:
```dockerfile
HEALTHCHECK CMD curl -f http://localhost:8000/health || exit 1
```

## Security
PROBLEM: Running as root
SOLUTION:
```dockerfile
RUN useradd -m appuser && chown -R appuser /app
USER appuser
```

## Database Init
PROBLEM: Race condition
SOLUTION:
```yaml
init-db:
  command: python -m app.init_db
backend:
  depends_on:
    init-db:
      condition: service_completed_successfully
```

## Environment Defaults
PROBLEM: OPENAI_API_KEY with no default
SOLUTION: OPENAI_API_KEY=${OPENAI_API_KEY:-not-needed-kamiwaza}

## Debug Commands
```bash
docker-compose logs backend
docker-compose exec backend env
docker-compose exec backend curl http://host.docker.internal:8080/health
```
- Kamiwaza managed docker containers deployed through the app garden. Look them up rather than calling docker compose directly.