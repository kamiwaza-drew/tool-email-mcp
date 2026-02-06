# email-mcp-extensions

REPO: Kamiwaza extensions for kamiwazaai
AI_RESOURCES: @.ai/README.md

## Structure
- apps/{name}/: Multi-service applications
- services/{name}/: App Garden backend services
- tools/{name}/: MCP protocol servers
- scripts/: Automation (Python/Shell)
- build/: Generated registry (gitignored)

## Extension Requirements
METADATA: kamiwaza.json (name, version, risk_tier, env_defaults)
DOCKER: Dockerfile, docker-compose.yml, docker-compose.appgarden.yml
MCP_TOOLS: Port 8000, path /mcp
REFERENCE: @.ai/rules/architecture.md

## Template Variables
USE_IN: kamiwaza.json env_defaults
AVAILABLE: {app_port}, {model_port}, {deployment_id}, {app_name}
SYSTEM: KAMIWAZA_APP_PORT, KAMIWAZA_MODEL_PORT, KAMIWAZA_DEPLOYMENT_ID

## Commands
```bash
# Create
make new TYPE={app|service|tool} NAME={name}

# CI/Release Pipeline (in order)
make build TYPE={type} NAME={name}
make test TYPE={type} NAME={name}
make sync-compose
make validate
make build-registry
make push TYPE={type} NAME={name}

# Local Testing
cd {path} && docker-compose up --build
```

PIPELINE: @.ai/rules/development-lifecycle.md

## Common Tasks
CREATE_APP: @.ai/prompts/new-app.md
CREATE_TOOL: @.ai/prompts/new-tool.md
CREATE_SERVICE: @.ai/prompts/new-service.md
ADD_ENDPOINT: @.ai/prompts/add-endpoint.md
VALIDATE: @.ai/prompts/validate-extension.md
WRITE_TESTS: @.ai/prompts/write-tests.md

## Development Rules
ARCHITECTURE: @.ai/rules/architecture.md
PYTHON: @.ai/rules/python-standards.md
LIFECYCLE: @.ai/rules/development-lifecycle.md
TESTING: @.ai/rules/testing.md
STYLE: @.ai/rules/style.md
TOOLS: @.ai/rules/tool-usage.md

## Patterns
APP_PATTERNS: @.ai/knowledge/successful/app-patterns.md
MCP_PATTERNS: @.ai/knowledge/successful/mcp-patterns.md
DOCKER_ISSUES: @.ai/knowledge/failures/docker-gotchas.md
APPGARDEN_LIMITS: @.ai/knowledge/failures/appgarden-limits.md

## Validation Rules
NO_HOST_PORTS: ports: ["8000"] not "8000:8000"
NO_BIND_MOUNTS: volumes: ["data:/app/data"] not "./data:/app/data"
RESOURCE_LIMITS: deploy.resources.limits required
HEALTH_CHECK: @app.get("/health") required (apps only)

## Environment Setup
KAMIWAZA_LLM: OPENAI_BASE_URL=${KAMIWAZA_ENDPOINT:-http://host.docker.internal:8080}
API_KEY: OPENAI_API_KEY=${OPENAI_API_KEY:-not-needed-kamiwaza}
EXTRA_HOSTS: host.docker.internal:host-gateway

## Docker Image Naming
PREFIX: kamiwazaai
PATTERN: kamiwazaai/{extension-name}-{service-name}:v{version}

## Quick Reference
LIST: make list
VALIDATE_ALL: make validate
BUILD_ALL: make build-all
TEST_ALL: make test-all
CI_CHECKS: make ci-validate

## Template Updates
UPDATE_CMD: copier update
TEMPLATE_SOURCE: Created from Kamiwaza extensions template
PRESERVED_DIRS: apps/, services/, tools/ (never overwritten on update)
