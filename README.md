# email-mcp-extensions

Kamiwaza extensions repository for kamiwazaai.

## Overview

This repository contains Kamiwaza platform extensions:
- **Apps** (`apps/`): Multi-service applications deployed to App Garden
- **Services** (`services/`): App Garden backend services (e.g., vector databases)
- **Tools** (`tools/`): MCP protocol servers deployed to Tool Shed

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.10+
- [uv](https://github.com/astral-sh/uv) (recommended) or pip

### Setup

```bash
# Install development dependencies
make install

# List available extensions
make list
```

### Creating Extensions

```bash
# Create a new app
make new TYPE=app NAME=my-app

# Create a new service
make new TYPE=service NAME=service-milvus

# Create a new tool
make new TYPE=tool NAME=my-tool
```

### Development Workflow

```bash
# Build an extension
make build TYPE=app NAME=my-app

# Test an extension
make test TYPE=app NAME=my-app

# Validate all extensions
make validate

# Run full CI pipeline
make ci-pipeline
```

## Structure

```
email-mcp-extensions/
├── apps/                    # Multi-service applications
│   └── {app-name}/
│       ├── kamiwaza.json    # Extension metadata
│       ├── docker-compose.yml
│       ├── backend/
│       └── frontend/
├── services/                # App Garden backend services
│   └── {service-name}/
│       ├── kamiwaza.json
│       └── docker-compose.yml
├── tools/                   # MCP tool servers
│   └── {tool-name}/
│       ├── kamiwaza.json
│       ├── Dockerfile
│       └── src/
├── shared/                  # Shared libraries
│   ├── python/
│   └── typescript/
├── make/                    # Build system modules
├── scripts/                 # Build/test scripts
└── .ai/                     # AI assistant rules
```

## Extension Requirements

Each extension must have:
- `kamiwaza.json` with name, version, risk_tier
- `Dockerfile` for each service
- `docker-compose.yml` for local development
- Health endpoint at `GET /health` (apps only)

See `.ai/rules/architecture.md` for detailed requirements.

## Updating from Upstream

This repository was created from the Kamiwaza extensions template. To pull infrastructure updates:

```bash
# Update shared infrastructure (preserves apps/, services/, and tools/)
copier update --trust --skip-answered --defaults

# Review changes
git diff

# Commit updates
git add -A && git commit -m "Update infrastructure from upstream"
```

Tip: keep `.copier-answers.yml` committed so the template source is known. The flags above make the update non-interactive by reusing stored answers.

## Commands Reference

| Command | Description |
|---------|-------------|
| `make list` | List all extensions |
| `make new TYPE=app NAME=x` | Create new app |
| `make new TYPE=service NAME=x` | Create new service |
| `make new TYPE=tool NAME=x` | Create new tool |
| `make build TYPE=app NAME=x` | Build extension |
| `make test TYPE=app NAME=x` | Test extension |
| `make validate` | Validate all extensions |
| `make sync-compose` | Generate App Garden configs |
| `make build-registry` | Build extension registry |
| `make ci-pipeline` | Run full CI pipeline |

## Configuration

Docker images are prefixed with: `kamiwazaai/`

## GitHub Bootstrap

After creating the repo on GitHub, configure topics, branches, and protection rules:

```bash
# Interactive mode - prompts for each option
./scripts/setup-github-repo.sh

# Or use a config file for non-interactive setup
cp .github/repo-setup.yml.example .github/repo-setup.yml
# Edit config as needed, then run:
./scripts/setup-github-repo.sh
```

**What it configures:**
- Topics (`extensions`)
- Develop branch from main
- Branch naming rules (enforces `feature/*`, `fix/*`, etc.)
- Branch protection (PR reviews, status checks, force push blocking)

See `.github/repo-setup.yml.example` for all configuration options.

## License

Proprietary - kamiwazaai
