# Kamiwaza Extensions Developer Guide

This is the comprehensive technical reference for building Kamiwaza extensions. For contribution workflow and process (forking, PRs, publishing), see [CONTRIBUTING.md](CONTRIBUTING.md).

## Table of Contents
- [Developer Tools Setup](#developer-tools-setup)
- [Overview](#overview)
- [Extension Types](#extension-types)
- [Extension Structure](#extension-structure)
- [Creating a New Extension](#creating-a-new-extension)
- [Metadata Requirements](#metadata-requirements)
- [Docker Requirements](#docker-requirements)
- [Testing Extensions](#testing-extensions)
- [Deployment](#deployment)
- [Best Practices](#best-practices)

## Developer Tools Setup

Install these CLI tools for efficient development:

### Code Search & Navigation

**ast-grep** - Structural code search
```bash
# macOS
brew install ast-grep

# Linux
cargo install ast-grep

# npm (alternative)
npm install -g @ast-grep/cli
```

**ripgrep (rg)** - Fast text search
```bash
# macOS
brew install ripgrep

# Linux (Debian/Ubuntu)
apt install ripgrep

# Linux (Fedora)
dnf install ripgrep
```

**fd** - Fast file finder
```bash
# macOS
brew install fd

# Linux (Debian/Ubuntu)
apt install fd-find

# Linux (Fedora)
dnf install fd-find
```

**fzf** - Fuzzy finder for interactive selection
```bash
# macOS
brew install fzf

# Linux
git clone --depth 1 https://github.com/junegunn/fzf.git ~/.fzf
~/.fzf/install
```

### Data Processing

**jq** - JSON processor
```bash
# macOS
brew install jq

# Linux (Debian/Ubuntu)
apt install jq
```

**yq** - YAML/XML processor
```bash
# macOS
brew install yq

# Linux
wget https://github.com/mikefarah/yq/releases/latest/download/yq_linux_amd64 -O /usr/local/bin/yq
chmod +x /usr/local/bin/yq
```

### Diff & Merge

**difftastic (difft)** - Syntax-aware diff
```bash
# macOS
brew install difftastic

# Linux
cargo install difftastic
```

**mergiraf** - Git merge conflict handler
```bash
# Any platform with cargo
cargo install mergiraf

# Configure git to use mergiraf
git config --global merge.tool mergiraf
git config --global mergetool.mergiraf.cmd 'mergiraf "$LOCAL" "$BASE" "$REMOTE" -o "$MERGED"'
```

### GitHub

**gh** - GitHub CLI
```bash
# macOS
brew install gh

# Linux (Debian/Ubuntu)
curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
apt update
apt install gh

# Authenticate
gh auth login
```

### Verification

Test your installations:
```bash
ast-grep --version
rg --version
fd --version
fzf --version
jq --version
yq --version
difft --version
mergiraf --version
gh --version
```

### Usage

See `.ai/rules/tool-usage.md` for patterns and examples.

Quick examples:
```bash
# Find TypeScript functions
ast-grep run --lang ts -p 'function $NAME($$$) { $$$ }'

# Search text in Python files
rg 'pattern' --type py

# Find all Dockerfiles
fd Dockerfile

# Interactive file selection
fd '\.py$' | fzf

# Parse JSON
jq '.field' file.json

# View diff with syntax highlighting
difft file1.py file2.py

# Create GitHub issue
gh issue create --title "Bug" --body "Description"
```

## Overview

Kamiwaza extensions are containerized applications that extend the platform's capabilities. There are two types of extensions:

- **Apps**: Full applications with user interfaces (e.g., chatbots, dashboards)
- **Tools**: MCP (Model Context Protocol) servers that provide AI models with additional capabilities (e.g., web search, browser automation)

## Extension Types

### Apps
Apps are complete applications that typically include:
- Frontend interface (web UI)
- Backend services
- Database connections
- Multiple Docker containers orchestrated with docker-compose

Examples: Kaizen (AI assistant), Shinobi Bench (benchmarking platform)

### Tools
Tools are MCP servers that:
- Expose specific capabilities via the MCP protocol
- Run as single containers
- Integrate with AI models to provide additional functionality

Examples: websearch-tool, playwright-tool

## Extension Structure

### Basic Structure
Every extension must have:
```
{type}s/{extension-name}/
├── kamiwaza.json              # Extension metadata (required)
├── Dockerfile                 # Container definition (required)
├── docker-compose.yml         # Local development compose
├── docker-compose.appgarden.yml # App Garden deployment (auto-generated)
└── README.md                  # Documentation with configuration details
```

### App Structure Example
```
apps/my-app/
├── kamiwaza.json
├── docker-compose.yml
├── docker-compose.appgarden.yml
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   └── src/
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── src/
├── tests/
└── README.md
```

### Tool Structure Example
```
tools/my-tool/
├── kamiwaza.json
├── Dockerfile
├── docker-compose.yml
├── docker-compose.appgarden.yml
├── requirements.txt or package.json
├── server.py or index.js
├── tests/
└── README.md
```

## Creating a New Extension

The repository supports three types of extensions:
1. **Internal** - Full source code included in the repository
2. **External** - References Docker images maintained elsewhere
3. **Hybrid** - Uses git submodules for source code

### 1. Quick Start

#### Internal Extension (with source)
```bash
# Create a new app with source
make new-internal TYPE=app NAME=my-analyzer

# Create a new tool with source
make new-internal TYPE=tool NAME=my-mcp-server
```

#### External Extension (external images)
```bash
# Create a new app referencing external images
make new-external TYPE=app NAME=my-external-app

# Create a new tool referencing external images  
make new-external TYPE=tool NAME=my-external-tool
```

#### Hybrid Extension (git submodule)
```bash
# Create with submodule
make new-hybrid TYPE=app NAME=my-hybrid-app REPO=https://github.com/user/repo.git
```

### 2. Add Metadata
Create `kamiwaza.json` in your extension directory:

#### For Apps:
```json
{
  "name": "my-analyzer",
  "version": "1.0.0",
  "source_type": "kamiwaza",
  "visibility": "public",
  "description": "AI-powered data analyzer with web interface",
  "category": "analytics",
  "tags": ["ai", "analytics", "dashboard"],
  "author": "Your Name",
  "license": "MIT",
  "homepage": "https://github.com/yourusername/my-analyzer",
  "risk_tier": 1,
  "verified": false,
  "env_defaults": {
    "API_PORT": "8000",
    "UI_PORT": "3000"
  },
  "preferred_model_type": "reasoning",
  "fail_if_model_type_unavailable": false
}
```

#### For Tools:
```json
{
  "name": "tool-my-mcp-server",
  "version": "1.0.0",
  "source_type": "kamiwaza",
  "visibility": "public",
  "description": "MCP server that provides custom functionality",
  "category": "productivity",
  "tags": ["mcp", "tool", "automation"],
  "author": "Your Name",
  "license": "MIT",
  "homepage": "https://github.com/yourusername/my-mcp-server",
  "image": "kamiwazaai/my-mcp-server:v1.0.0",
  "risk_tier": 1,
  "verified": false,
  "capabilities": ["custom_capability"],
  "required_env_vars": ["API_KEY"],
  "env_defaults": {
    "PORT": "8000",
    "MCP_PATH": "/mcp"
  }
}
```

### 3. Create Docker Configuration

#### Dockerfile Best Practices:
```dockerfile
FROM node:20-alpine
WORKDIR /app

# Copy dependencies first for better caching
COPY package*.json ./
RUN npm ci --only=production

# Copy source code
COPY . .

# Run as non-root user
USER node

EXPOSE 8000
CMD ["node", "server.js"]
```

#### Local docker-compose.yml:
```yaml
version: "3.9"

services:
  my-service:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./src:/app/src  # Hot reload for development
    environment:
      - NODE_ENV=development
      - API_KEY=${API_KEY}
```

### 4. Generate App Garden Compose
```bash
# Automatically transform for App Garden compatibility
make sync-compose TYPE=app NAME=my-analyzer
```

This creates `docker-compose.appgarden.yml` with:
- Dynamic port allocation (no host ports)
- No bind mounts
- Resource limits
- Kamiwaza host access

### 5. Add Documentation
Create a comprehensive README.md including:
- Description and features
- Configuration options
- Environment variables
- Usage examples
- Development setup

## Metadata Requirements

### Required Fields
| Field | Type | Description |
|-------|------|-------------|
| name | string | Extension name (tools must start with "tool-") |
| version | string | Semantic version (e.g., "1.0.0") |
| source_type | string | Must be "kamiwaza" |
| visibility | string | "public" or "private" |
| description | string | Clear description of functionality |
| risk_tier | integer | Security level: 0 (low), 1 (medium), 2 (high)* |
| verified | boolean | Verification status |

> **⚠️ Important**: Due to a known issue ([#481](https://github.com/kamiwaza-internal/kamiwaza/issues/481)), risk_tier 2 tools cannot be deployed as the UI doesn't prompt for required BREAK_GLASS justification. Until fixed, use only risk_tier 0 or 1.

### Optional Fields
| Field | Type | Description |
|-------|------|-------------|
| category | string | Extension category |
| tags | array | Searchable tags |
| author | string | Creator name |
| license | string | License type |
| homepage | string | Project URL |
| env_defaults | object | Default environment variables |
| preview_image | string | Path to preview image |

### Tool-Specific Fields
| Field | Type | Description |
|-------|------|-------------|
| image | string | Docker image name |
| capabilities | array | MCP capabilities provided |
| required_env_vars | array | Required environment variables |

### App-Specific Fields
| Field | Type | Description |
|-------|------|-------------|
| preferred_model_type | string | Preferred AI model type |
| preferred_model_name | string | Specific model preference |
| fail_if_model_type_unavailable | boolean | Strict model requirement |

## Docker Requirements

### Image Naming
- Apps: `kamiwazaai/{app-name}:{version}`
- Tools: `kamiwazaai/{tool-name}:{version}`
- Multi-service apps: `kamiwazaai/{app-name}-{service}:{version}`

### App Garden Compatibility
Your docker-compose must be compatible with App Garden:

**Allowed:**
- ✅ Named volumes
- ✅ Container ports (e.g., `ports: ["8000"]`)
- ✅ Service-to-service networking
- ✅ Environment variables with defaults
- ✅ Resource limits

**Not Allowed:**
- ❌ Host port mappings (e.g., `"8000:8000"`)
- ❌ Bind mounts (e.g., `./src:/app/src`)
- ❌ Build contexts (must use pre-built images)
- ❌ Host network mode
- ❌ Privileged containers

### Resource Limits
Always specify resource limits:
```yaml
deploy:
  resources:
    limits:
      cpus: "1.0"
      memory: "1G"
```

Recommended limits by service type:
- Frontend/UI: 0.5 CPU, 512M memory
- Backend API: 1.0 CPU, 1G memory
- Database: 0.5 CPU, 512M memory
- Redis/Cache: 0.25 CPU, 256M memory
- MCP Tools: 0.5-1.0 CPU, 512M-2G memory

### Kamiwaza Integration
For services that need to access Kamiwaza APIs:
```yaml
extra_hosts:
  - "host.docker.internal:host-gateway"
environment:
  - KAMIWAZA_API_URI=${KAMIWAZA_API_URI:-https://host.docker.internal/api}
  - KAMIWAZA_ENDPOINT=${KAMIWAZA_ENDPOINT:-http://host.docker.internal:7777/api/}
```

## Testing Extensions

### 1. Validate Metadata
```bash
# Check all validation rules
make validate

# Check only metadata
make validate-metadata

# Check only compose files
make validate-compose
```

### 2. Build Images
```bash
# Build specific extension
make build TYPE=app NAME=my-analyzer

# Build all extensions
make build-all
```

### 3. Run Tests
```bash
# Test specific extension
make test TYPE=tool NAME=my-mcp-server

# Test all extensions
make test-all
```

### 4. Local Testing
```bash
cd apps/my-analyzer
docker-compose up

# In another terminal
curl http://localhost:8000/health
```

## External Extensions Guide

External extensions allow you to maintain your source code in a separate repository while still participating in the Kamiwaza ecosystem. This approach is ideal for:
- Private/proprietary code
- Extensions with complex CI/CD requirements
- Projects that need independent versioning

### Requirements for External Extensions

1. **Published Docker Images**: Your images must be available in a Docker registry
2. **Metadata File**: Provide kamiwaza.json with extension details
3. **Compose File**: For apps, provide docker-compose.appgarden.yml
4. **Documentation**: Include README.md with usage instructions

### Structure for External Apps
```
apps/my-external-app/
├── kamiwaza.json              # Required metadata
├── docker-compose.appgarden.yml # References your images
└── README.md                  # Links to source repo
```

### Structure for External Tools  
```
tools/my-external-tool/
├── kamiwaza.json              # Required metadata (includes 'image' field)
└── README.md                  # Documentation
```

### Example External App
```json
// kamiwaza.json
{
  "name": "my-external-app",
  "version": "1.2.3",
  "source_type": "kamiwaza",
  "visibility": "public",
  "description": "My app maintained externally",
  "homepage": "https://github.com/myorg/my-app",
  // ... other required fields
}
```

```yaml
# docker-compose.appgarden.yml
version: '3.9'
services:
  backend:
    image: myorg/my-app-backend:v1.2.3
    ports:
      - "8000"
    environment:
      DATABASE_URL: ${DATABASE_URL}
    extra_hosts:
      - "host.docker.internal:host-gateway"
    deploy:
      resources:
        limits:
          cpus: "1.0"
          memory: "1G"
```

### Development Workflow

1. **Local Development**: Work in your own repository
2. **Build & Test**: Use your own CI/CD pipeline
3. **Publish Images**: Push to Docker Hub or other registry
4. **Submit PR**: Add only metadata files to kamiwaza-extensions

### Image Verification

The build system can verify your images exist:
```bash
# Check if images exist locally
make verify-images

# Check if images exist in registry
make verify-images-registry

# Build will verify external images
make build TYPE=app NAME=my-external-app
```

### Best Practices

1. **Semantic Versioning**: Use consistent version tags
2. **Image Naming**: Follow the pattern `org/extension-name:version`
3. **Documentation**: Clearly document configuration options
4. **Registry Access**: Ensure images are publicly accessible
5. **Updates**: Keep metadata version in sync with image tags

## Deployment

### 1. Build Registry
After adding or updating extensions:
```bash
# Generate apps.json and tools.json
make build-registry
```

This creates:
- `build/garden/default/apps.json` - All app definitions
- `build/garden/default/tools.json` - All tool definitions

### 2. Push Docker Images
```bash
# Build and tag your images
docker build -t kamiwazaai/my-app:v1.0.0 .
docker push kamiwazaai/my-app:v1.0.0
```

### 3. Submit to Kamiwaza
1. Ensure all validations pass
2. Push Docker images to registry
3. Submit PR with your extension
4. Registry files are auto-generated on merge

## Best Practices

### General
1. **Single Responsibility**: Each extension should do one thing well
2. **Documentation**: Include comprehensive README with examples
3. **Versioning**: Use semantic versioning (MAJOR.MINOR.PATCH)
4. **Testing**: Include tests for your extension
5. **Security**: Follow least-privilege principles

### Docker
1. **Small Images**: Use alpine-based images when possible
2. **Layer Caching**: Order Dockerfile commands for optimal caching
3. **Non-root User**: Always run containers as non-root
4. **Health Checks**: Include health check endpoints
5. **Graceful Shutdown**: Handle SIGTERM properly

### Environment Variables
1. **Defaults**: Provide sensible defaults in env_defaults
2. **Documentation**: Document all environment variables
3. **Secrets**: Never hardcode secrets or API keys
4. **Validation**: Validate required variables at startup

### MCP Tools
1. **Standard Ports**: Use port 8000 for MCP endpoint
2. **Path Convention**: Expose MCP at `/mcp`
3. **Error Handling**: Return proper MCP error responses
4. **Capabilities**: Clearly define what your tool can do
5. **Streaming**: Support SSE for long-running operations

### Apps
1. **Responsive UI**: Ensure UI works on various screen sizes
2. **API Design**: Follow RESTful principles
3. **State Management**: Handle state appropriately
4. **Error Messages**: Provide helpful error messages
5. **Loading States**: Show progress for long operations

## Troubleshooting

### Common Issues

**Metadata validation fails:**
- Check required fields are present
- Verify version format (X.Y.Z)
- Ensure risk_tier is 0, 1, or 2

**Compose validation fails:**
- Remove host port mappings
- Remove bind mounts
- Add resource limits
- Add extra_hosts for Kamiwaza access

**Build fails:**
- Ensure Dockerfile exists
- Check base image is accessible
- Verify build context paths
- Review build logs for errors

**Tests not found:**
- Place tests in `tests/` directory
- Name test files appropriately
- Include test dependencies

### Getting Help
1. Check existing extensions for examples
2. Run validation tools for specific errors
3. Review CI/CD logs for failures
4. Submit issues to the repository

## Command Reference

```bash
# Discovery
make list                    # List all extensions
make list-apps              # List only apps
make list-tools             # List only tools

# Building
make build TYPE=X NAME=Y    # Build specific extension
make build-all              # Build all extensions

# Testing  
make test TYPE=X NAME=Y     # Test specific extension
make test-all               # Test all extensions

# Validation
make validate               # Validate everything
make validate-metadata      # Check metadata only
make validate-compose       # Check compose files only

# Compose Management
make sync-compose           # Sync all compose files
make check-compose          # Check if sync needed

# Registry
make build-registry         # Generate registry files

# Development
make new TYPE=X NAME=Y      # Create new extension
```

---

For more examples, explore the existing extensions in the `apps/`, `services/`, and `tools/` directories.
