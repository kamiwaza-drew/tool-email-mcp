# Create New Service

VARIABLES:
- NAME: {service-name}  # must start with service-
- STACK: {tech-stack}
- DESCRIPTION: {description}

COMMANDS:
```bash
make new TYPE=service NAME={NAME}
```

KAMIWAZA_JSON:
```json
{
  "name": "{NAME}",
  "template_type": "service",
  "version": "1.0.0",
  "source_type": "kamiwaza",
  "visibility": "public",
  "description": "{DESCRIPTION}",
  "risk_tier": 1,
  "verified": false,
  "preferred_model_type": null
}
```

DOCKER_COMPOSE:
```yaml
services:
  service:
    image: myorg/{NAME}:1.0.0
    ports:
      - "19530"
    deploy:
      resources:
        limits:
          cpus: "1.0"
          memory: "1G"
```

FINALIZE:
```bash
make sync-compose
make validate
```
