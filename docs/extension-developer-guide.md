# Extension Developer Guide

This guide walks through the process of creating and deploying extensions (apps, services, and tools) in the Kamiwaza Extensions subsystem.

## Overview

Extensions in the Kamiwaza Extensions subsystem are deployed using Docker Compose templates. Extensions include:

- **Apps**: Full-stack containerized applications with web interfaces
- **Services**: Backend utilities and infrastructure (automatically detected by "service-" prefix)
- **Tools**: Utility services and helper tools (automatically detected by "tool-" or "mcp-" prefix)

Extension code is packaged as Docker images that are pulled from a container registry when users deploy the extension.

## Extension Types

### Apps
- Serve web interfaces or APIs
- Respond to HTTP health checks on root path
- Can automatically connect to AI models
- Named without restrictions (e.g., "my-web-app", "docupro")

### Services
- Backend utilities (vector DBs, infra services, gRPC endpoints)
- **Must use "service-" prefix** (e.g., "service-milvus")
- Skip HTTP health checks (may not serve HTTP on root)
- Use `template_type=service` in metadata

### Tools
- Provide utility functions or helper services
- **Must use "tool-" or "mcp-" prefix** (e.g., "tool-code-analyzer")
- Skip HTTP health checks (may not serve HTTP on root)
- Can set `preferred_model_type=null` to skip model discovery

## Prerequisites

1. Your application containerized with Docker
2. A Docker Compose file that defines your services
3. Access to a container registry (Docker Hub, GitHub Container Registry, etc.)
4. Docker installed locally for building and pushing images
5. **For multi-arch builds:** Docker Buildx with `docker-container` driver and QEMU (see [Publish Multi-Arch Docker Images](#publish-multi-arch-docker-images-with-make-publish-images))

## Quickstart

### Essential Make Targets

| Command | Purpose | When to Use |
|---------|---------|-------------|
| `make new TYPE={app\|service\|tool} NAME={name}` | Scaffold new extension | Creating a new app, service, or tool |
| `make package-libs` | Build shared auth libraries | Before building apps that use auth |
| `make build TYPE={type} NAME={name}` | Build Docker images | After code changes |
| `make test TYPE={type} NAME={name}` | Run tests | After implementation |
| `make sync-compose` | Generate App Garden compose | After docker-compose.yml changes |
| `make validate` | Validate metadata/configs | Before committing |
| `make build-registry` | Build extension catalog | Before releasing |
| `make publish-images` | Build and push multi-arch images | When publishing to registry |
| `make publish` | Publish registry AND multi-arch images | Full release to registry |
| `make package-registry` | Create distribution tarball | For offline distribution |
| `make ci-pipeline` | Run full CI pipeline | Before merging/releasing |

### Development Targets

| Command | Purpose |
|---------|---------|
| `make build-all` | Build all extensions |
| `make test-all` | Test all extensions |
| `make list` | List all extensions |
| `make clean` | Clean build artifacts |
| `make serve-registry PORT=58888` | Serve registry via HTTPS |

### Loading Extensions (Developer Testing)

| Command | Purpose |
|---------|---------|
| `make kamiwaza-push TYPE=app|service NAME={name}` | Push template to Kamiwaza API |
| `make kamiwaza-list` | List templates on Kamiwaza |
| Configure `KAMIWAZA_EXTENSION_STAGE=LOCAL` | Load from filesystem/HTTPS |

### CI Pipeline

The `make ci-pipeline` command runs the complete CI/release workflow:

```bash
make ci-pipeline
```

**Pipeline Steps:**
1. **Build** - Build all extension Docker images (`make build-all`)
2. **Test** - Run all extension tests (`make test-all`)
3. **Sync** - Generate App Garden compose files (`make sync-compose`)
4. **Validate** - Validate all metadata and configs (`make validate`)
5. **Registry** - Build extension catalog (`make build-registry`)
6. **Package** - Create distribution tarball (`make package-registry`)

**Output:** Creates `dist/kamiwaza-registry-YYYYMMDD-HHMMSS.tar.gz` for distribution.

**Use when:** Running full CI checks before merging PRs or releasing extensions.

### Typical Workflows

**Create and test a new extension:**
```bash
# Create extension
make new TYPE=app NAME=my-app

# Implement your code...

# Build and test
make build TYPE=app NAME=my-app
make test TYPE=app NAME=my-app

# Validate and load into Kamiwaza
make sync-compose
make validate
make build-registry
make kamiwaza-push TYPE=app NAME=my-app
```

**Create and test a new service:**
```bash
make new TYPE=service NAME=service-milvus
make build TYPE=service NAME=service-milvus
make test TYPE=service NAME=service-milvus
make sync-compose
make validate
make build-registry
make kamiwaza-push TYPE=service NAME=service-milvus
```

**Run full CI before releasing:**
```bash
# Single command for complete CI pipeline
make ci-pipeline

# Output: dist/kamiwaza-registry-YYYYMMDD-HHMMSS.tar.gz
```

**Update an existing extension:**
```bash
# Make changes...
# Bump version in kamiwaza.json

# Rebuild and test
make build TYPE=app NAME=my-app
make test TYPE=app NAME=my-app
make sync-compose
make validate
make build-registry
```

## Step-by-Step Process

### Step 1: Create New Extension with `make new`

The `make new` command scaffolds a new extension with the proper directory structure and initial configuration files.

**Command:**
```bash
make new TYPE={app|service|tool} NAME={extension-name}
```

**Parameters:**
- `TYPE`: `app` (full-stack application), `service` (backend utility), or `tool` (MCP server)
- `NAME`: Your extension name (lowercase, hyphens for spaces)

**Examples:**
```bash
# Create a new app
make new TYPE=app NAME=document-processor

# Create a new service
make new TYPE=service NAME=service-milvus

# Create a new tool
make new TYPE=tool NAME=code-analyzer
```

**Generated Structure:**

For **apps**:
```
apps/document-processor/
├── kamiwaza.json           # Extension metadata (configure this!)
├── docker-compose.yml      # Local development compose file
├── docker-compose.appgarden.yml  # Generated App Garden version
├── README.md              # Extension documentation
├── frontend/              # Frontend service (if applicable)
│   └── Dockerfile
└── backend/               # Backend service
    └── Dockerfile
```

For **services**:
```
services/service-milvus/
├── kamiwaza.json          # Extension metadata (configure this!)
├── docker-compose.yml     # Local development compose file
├── docker-compose.appgarden.yml  # Generated App Garden version
├── README.md             # Extension documentation
└── backend/              # Optional service code
    └── Dockerfile
```

For **tools**:
```
tools/code-analyzer/
├── kamiwaza.json          # Extension metadata (configure this!)
├── docker-compose.yml     # Service definition
├── docker-compose.appgarden.yml  # Generated App Garden version
├── README.md             # Extension documentation
└── src/                  # Tool source code
    └── server.py         # MCP server implementation
```

### Step 2: Configure kamiwaza.json Metadata

After running `make new`, you need to configure the generated `kamiwaza.json` file. This file is the **single source of truth** for extension configuration.

**Location**: `apps/{extension-name}/kamiwaza.json`, `services/{extension-name}/kamiwaza.json`, or `tools/{extension-name}/kamiwaza.json`

#### Required Fields

```json
{
  "name": "your-extension-name",
  "version": "1.0.0",
  "source_type": "kamiwaza",
  "risk_tier": 0
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | ✅ | Extension name (must match directory name) |
| `version` | string | ✅ | Semantic version (e.g., "1.0.0") - single source of truth for Docker image tags |
| `source_type` | string | ✅ | Always "kamiwaza" for extensions in this repository |
| `risk_tier` | number | ✅ | Security risk level: 0 (safe), 1 (low risk), 2 (requires review) |

#### Optional Fields

```json
{
  "name": "my-app",
  "version": "1.0.0",
  "source_type": "kamiwaza",
  "risk_tier": 1,
  "visibility": "public",
  "description": "Brief description of what this extension does",
  "category": "productivity",
  "tags": ["ai", "document-processing"],
  "verified": false,
  "preferred_model_type": "fast",
  "fail_if_model_type_unavailable": false,
  "preferred_model_name": "qwen",
  "fail_if_model_name_unavailable": false,
  "env_defaults": {
    "CALLBACK_URL": "https://localhost:{app_port}/callback",
    "PUBLIC_URL": "https://localhost:{app_port}",
    "KAMIWAZA_API_URI": "https://host.docker.internal/api"
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `visibility` | string | "public" or "private" (default: "public") |
| `description` | string | User-facing description shown in extension catalog |
| `category` | string | Extension category (e.g., "productivity", "development", "ai") |
| `tags` | array | Search tags for the extension catalog |
| `verified` | boolean | Whether extension is officially verified (default: false) |
| `preferred_model_type` | string | Preferred AI model type: "fast", "large", "reasoning", "vl", "any", or null |
| `fail_if_model_type_unavailable` | boolean | Fail deployment if preferred model type not available (default: false) |
| `preferred_model_name` | string | Preferred model name substring (e.g., "qwen", "llama") |
| `fail_if_model_name_unavailable` | boolean | Fail deployment if preferred model name not available (default: false) |
| `env_defaults` | object | Default environment variables with template variable support |

#### Template Variables in env_defaults

You can use template variables in `env_defaults` that are substituted at deployment time:

| Variable | Substituted With | Example |
|----------|------------------|---------|
| `{app_port}` | Application's load balancer port | `61110` |
| `{model_port}` | AI model's service port | `61111` |
| `{deployment_id}` | Unique deployment UUID | `a1b2c3d4-...` |
| `{app_name}` | Application deployment name | `my-app-instance` |

**Example with template variables:**
```json
{
  "env_defaults": {
    "PUBLIC_URL": "https://localhost:{app_port}",
    "CALLBACK_URL": "https://localhost:{app_port}/api/callback",
    "WEBHOOK_URL": "https://localhost:{app_port}/webhooks/{deployment_id}",
    "INSTANCE_ID": "{deployment_id}"
  }
}
```

#### Model Type Preferences

Extensions that use AI models can specify preferences:

```json
{
  "preferred_model_type": "vl",
  "fail_if_model_type_unavailable": false
}
```

**Available model types:**
- `"fast"` - Small, quick models (< 70B parameters)
- `"large"` - Large models (≥ 70B parameters)
- `"reasoning"` - Reasoning-capable models (QwQ, DeepSeek-R1)
- `"vl"` - Vision-language models (for image processing)
- `"any"` - Any available model (default)
- `null` - Skip model discovery (for tools that don't need AI)

#### Example: App with AI Model Integration

```json
{
  "name": "document-processor",
  "version": "1.2.0",
  "source_type": "kamiwaza",
  "visibility": "public",
  "description": "AI-powered document processing and analysis",
  "category": "productivity",
  "tags": ["ai", "documents", "ocr"],
  "risk_tier": 1,
  "verified": false,
  "preferred_model_type": "vl",
  "fail_if_model_type_unavailable": false,
  "env_defaults": {
    "PUBLIC_URL": "https://localhost:{app_port}",
    "CALLBACK_URL": "https://localhost:{app_port}/api/callback",
    "KAMIWAZA_API_URI": "https://host.docker.internal/api"
  }
}
```

#### Example: MCP Tool

```json
{
  "name": "code-analyzer-tool",
  "version": "1.0.0",
  "source_type": "kamiwaza",
  "visibility": "public",
  "description": "MCP tool for analyzing code quality and complexity",
  "category": "development",
  "tags": ["mcp", "code-analysis", "development"],
  "risk_tier": 0,
  "verified": false,
  "preferred_model_type": null
}
```

#### Important Notes

**Version Management:**
- The `version` field in `kamiwaza.json` is the single source of truth for all image tags and release versions

**Reserved Environment Variables:**
- `KAMIWAZA_API_URL` - Injected by Extensions subsystem (don't override in env_defaults)
- `OPENAI_BASE_URL` - Injected by Extensions subsystem when model is deployed (don't override)
- `KAMIWAZA_APP_PORT` - Injected at runtime
- `KAMIWAZA_MODEL_PORT` - Injected at runtime
- `KAMIWAZA_DEPLOYMENT_ID` - Injected at runtime

**Best Practices:**
- Use semantic versioning (major.minor.patch)
- Set `risk_tier` based on security implications (0 for read-only tools, 1-2 for apps with write access)
- Provide clear, concise descriptions for the extension catalog
- Use template variables in `env_defaults` for dynamic URLs and ports
- For tools that use dynamic model selection or don't need AI models, set `preferred_model_type: null`

### Step 3: Implement Your Extension

Now implement your extension by editing the generated Dockerfiles, writing your application code, and configuring docker-compose for local development.

#### Edit Generated Dockerfiles

The `make new` command generates starter Dockerfiles. Edit them to match your application's needs.

**For apps** - Edit separate Dockerfiles for frontend and backend:

```dockerfile
# frontend/Dockerfile
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build
CMD ["npm", "start"]
```

```dockerfile
# backend/Dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**For tools** - Edit the generated Dockerfile:

```dockerfile
# Dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install -e .
EXPOSE 8000
CMD ["uvicorn", "src.server:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### Implement Required Health Endpoint (Apps Only)

**Apps must implement a `/health` endpoint** for container orchestration and monitoring. Services and tools can skip this requirement.

**Characteristics:**
- **Path**: `/health` (at root level)
- **Method**: GET
- **Response**: JSON with status field
- **Status Code**: 200 when healthy
- **Response Time**: < 1 second
- **Dependencies**: Should check critical services (database, cache, etc.)

**Python/FastAPI implementation:**

```python
# app/main.py
from fastapi import FastAPI

app = FastAPI()

@app.get("/health")
async def health_check():
    """Health check endpoint for container orchestration"""
    return {"status": "healthy"}
```

**With dependency checks:**

```python
@app.get("/health")
async def health_check():
    """Health check with database verification"""
    checks = {}

    # Check database connection
    try:
        db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = "error"
        return {"status": "degraded", "checks": checks}, 503

    # Check other dependencies
    try:
        redis.ping()
        checks["redis"] = "ok"
    except Exception:
        checks["redis"] = "error"
        return {"status": "degraded", "checks": checks}, 503

    return {"status": "healthy", "checks": checks}
```

**Node.js/Express implementation:**

```javascript
// app.js
app.get('/health', (req, res) => {
  res.json({ status: 'healthy' });
});
```

**Why it's required:**
- Kamiwaza uses this endpoint to verify your app is running
- Deployment will fail if the health check doesn't return 200
- Container orchestration systems use it for restart/replacement decisions

#### Configure docker-compose.yml for Local Development

Create a `docker-compose.yml` for **local development and testing**. Don't worry about App Garden compatibility yet - `make sync-compose` (Step 6) will automatically transform this file for production deployment.

**Basic structure:**

```yaml
version: '3.8'

services:
  backend:
    build:
      context: .
      dockerfile: backend/Dockerfile
    image: kamiwazaai/myapp-backend:latest  # :latest for local dev
    ports:
      - "8000"
    environment:
      - DATABASE_URL=postgres://user:pass@postgres:5432/db
    volumes:
      - backend_data:/app/data
    depends_on:
      - postgres

  postgres:
    image: postgres:15-alpine  # External images keep specific versions
    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
      - POSTGRES_DB=dbname
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  backend_data:
  postgres_data:
```

**Key points for local development:**
- Use `build` contexts pointing to your Dockerfiles
- **For kamiwazaai/* images**: Use `:latest` tag - `make sync-compose` will replace with versioned tags from `kamiwaza.json`
- **For external images** (postgres, redis, etc.): Use specific version tags (e.g., `postgres:15-alpine`)
- Services communicate using service names (e.g., `http://backend:8000`)
- Use named volumes for data persistence
- Environment variables can use `${VAR:-default}` syntax

**Image tag substitution:**
When you run `make sync-compose`, it will:
- Replace `kamiwazaai/myapp-backend:latest` with `kamiwazaai/myapp-backend:v1.0.0` (from kamiwaza.json)
- Leave external images unchanged (`postgres:15-alpine` stays as-is)
- Generate `docker-compose.appgarden.yml` for App Garden deployment

#### Test Locally

Test your extension before running the full build pipeline:

```bash
cd apps/your-extension-name
# or
cd tools/your-tool-name

# Start services
docker-compose up --build

# Test health endpoint
curl http://localhost:8000/health
```

### Step 4: Build Docker Images with `make build`

Build your extension's Docker images with proper tagging.

**Command:**
```bash
make build TYPE={app|service|tool} NAME={extension-name}
```

**What it does:**
- Builds all Docker images defined in your docker-compose.yml
- Tags images as `kamiwazaai/{extension-name}-{service-name}:v{version}`
- Version comes from `kamiwaza.json` (single source of truth)

**Examples:**
```bash
# Build an app
make build TYPE=app NAME=document-processor

# Build a tool
make build TYPE=tool NAME=code-analyzer
```

**Image naming convention:**
- Single source of truth: `version` field in `kamiwaza.json`
- Docker tag format: `kamiwazaai/{extension-name}-{service-name}:v{version}`
- Example: `kamiwazaai/document-processor-backend:v1.2.0`

**Important:** The build process reads the version from `kamiwaza.json`, so ensure it's set correctly before building.

### Step 5: Run Tests with `make test`

Run your extension's test suite in an isolated environment that mirrors production.

**Command:**
```bash
make test TYPE={app|service|tool} NAME={extension-name}
```

**What it does:**
- Automatically detects test framework (pytest, npm test, go test, etc.)
- Creates isolated testing environment within Docker containers
- Runs all tests with proper dependency isolation
- Reports results and failures
- Cleans up test environment after completion

**Examples:**
```bash
# Test an app
make test TYPE=app NAME=document-processor

# Test a tool
make test TYPE=tool NAME=code-analyzer
```

#### Test Isolation for Python Extensions

For **Python** extensions (FastAPI backends, MCP tools), `make test` uses **pytest** in an isolated container environment:

**Test Structure:**
```
apps/my-app/backend/
├── app/
│   ├── __init__.py
│   ├── main.py
│   └── services/
├── tests/
│   ├── __init__.py
│   ├── conftest.py          # Shared fixtures
│   ├── test_api.py          # API endpoint tests
│   └── test_services.py     # Service logic tests
├── requirements.txt          # Production dependencies
└── requirements-dev.txt      # Test dependencies (pytest, httpx, etc.)
```

**Isolation mechanism:**
- Tests run inside the Docker container (not on host)
- Uses the extension's built Docker image
- Installs test dependencies from `requirements-dev.txt` or `dev-requirements.txt`
- Creates fresh test database/services per run
- No interference with host Python environment

**Example test with fixtures:**
```python
# tests/conftest.py
import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture
def client():
    """Isolated test client for each test"""
    return TestClient(app)

@pytest.fixture
def test_db():
    """Isolated test database"""
    # Setup test database
    db = create_test_database()
    yield db
    # Teardown
    drop_test_database(db)

# tests/test_api.py
def test_health_endpoint(client):
    """Test health check returns 200"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_create_resource(client, test_db):
    """Test resource creation with isolated DB"""
    response = client.post("/api/resources", json={"name": "test"})
    assert response.status_code == 201
```

**Test dependencies (`requirements-dev.txt` or `dev-requirements.txt`):**
```txt
pytest>=7.4.0
pytest-asyncio>=0.21.0
httpx>=0.24.0              # For async client testing
pytest-cov>=4.1.0          # Coverage reporting
```

#### Test Isolation for Node.js Extensions

For **Node.js** extensions (Next.js frontends, React apps), `make test` uses the project's configured test framework. **We recommend Vitest** for its speed and modern features.

**Test Structure:**
```
apps/my-app/frontend/
├── src/
│   ├── components/
│   ├── pages/
│   └── utils/
├── tests/
│   ├── unit/
│   │   ├── components.test.tsx
│   │   └── utils.test.ts
│   └── integration/
│       └── api.test.ts
├── package.json              # Defines test script
└── vitest.config.ts          # Vitest configuration (recommended)
```

**Isolation mechanism:**
- Tests run inside the Node.js container
- Uses the extension's built Docker image
- Installs dev dependencies from `package.json`
- Creates isolated test environment per run
- No interference with host Node.js/npm

**Example test configuration with Vitest (`package.json`):**
```json
{
  "scripts": {
    "test": "vitest run",
    "test:watch": "vitest",
    "test:coverage": "vitest run --coverage"
  },
  "devDependencies": {
    "vitest": "^1.0.0",
    "@vitejs/plugin-react": "^4.2.0",
    "@testing-library/react": "^14.0.0",
    "@testing-library/user-event": "^14.5.0",
    "@vitest/ui": "^1.0.0",
    "jsdom": "^23.0.0"
  }
}
```

**Vitest configuration (`vitest.config.ts`):**
```typescript
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: './tests/setup.ts',
    coverage: {
      reporter: ['text', 'json', 'html'],
      exclude: ['node_modules/', 'tests/'],
    },
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
});
```

**Example test with Vitest and React Testing Library:**
```typescript
// tests/unit/components.test.tsx
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { UserProfile } from '@/components/UserProfile';

describe('UserProfile Component', () => {
  it('renders user name correctly', () => {
    render(<UserProfile name="John Doe" />);
    expect(screen.getByText('John Doe')).toBeInTheDocument();
  });

  it('displays loading state', () => {
    render(<UserProfile name="" loading={true} />);
    expect(screen.getByRole('status')).toBeInTheDocument();
  });
});
```

**Alternative: Jest** (if you prefer Jest over Vitest):
```json
{
  "scripts": {
    "test": "jest --coverage"
  },
  "devDependencies": {
    "jest": "^29.5.0",
    "@testing-library/react": "^14.0.0",
    "@testing-library/jest-dom": "^6.0.0"
  }
}
```

#### How `make test` Works

1. **Detects test framework** by examining extension files:
   - Python: Looks for `pytest.ini`, `requirements-dev.txt`, or `tests/` directory
   - Node.js: Checks `package.json` for `test` script (supports vitest, jest, etc.)
   - Go: Looks for `*_test.go` files

2. **Builds test environment**:
   ```bash
   # For Python
   docker-compose run --rm backend bash -c "
     pip install -r requirements-dev.txt &&
     pytest tests/ -v --cov=app
   "
   
   # For Node.js (Vitest)
   docker-compose run --rm frontend npm test
   # Runs: vitest run
   ```

3. **Runs tests in isolation**:
   - Fresh container from built image
   - Separate network for test services
   - Isolated filesystem (no host mounts during tests)
   - Clean environment variables

4. **Reports results**:
   - Test pass/fail status
   - Coverage reports (if configured)
   - Failed test details
   - Exit code (0 = success, non-zero = failure)

#### Test Best Practices

**For Python:**
- Use `pytest` markers for test categories (`@pytest.mark.integration`)
- Mock external dependencies (Kamiwaza API, databases)
- Use `pytest-asyncio` for async tests
- Configure coverage in `pytest.ini` or `pyproject.toml`

**For Node.js (Vitest):**
- Use `describe.each` or `it.each` for parameterized tests
- Mock API calls with `vi.mock()` or `msw` (Mock Service Worker)
- Test components in isolation
- Configure coverage thresholds in `vitest.config.ts`
- Enable `globals: true` in config to avoid importing `describe`, `it`, `expect`

**Common patterns:**
```python
# Python: Mock Kamiwaza API
@pytest.fixture
def mock_kamiwaza_client(monkeypatch):
    mock = Mock()
    mock.models.list.return_value = [{"name": "test-model"}]
    monkeypatch.setattr("app.services.kamiwaza.client", mock)
    return mock
```

```typescript
// TypeScript (Vitest): Mock fetch calls
import { vi } from 'vitest';

global.fetch = vi.fn(() =>
  Promise.resolve({
    json: () => Promise.resolve({ data: 'test' }),
  })
);
```

```typescript
// TypeScript (Vitest): Mock modules
import { vi } from 'vitest';

vi.mock('@/lib/api-client', () => ({
  fetchData: vi.fn(() => Promise.resolve({ success: true })),
}));
```

#### Debugging Failed Tests

```bash
# Run tests with verbose output
make test TYPE=app NAME=my-app

# If tests fail, access the container for debugging
cd apps/my-app
docker-compose run --rm backend bash

# Inside container - run specific test
pytest tests/test_api.py::test_health_endpoint -v

# Check test logs
docker-compose logs backend
```

**Required:** All extensions must have tests and pass validation before merging. Tests ensure your extension works in the isolated container environment used by Kamiwaza.

### Step 6: Sync App Garden Compose with `make sync-compose`

Generate the App Garden-compatible docker-compose file from your local development version.

**Command:**
```bash
make sync-compose
```

**What it does:**
- Reads `docker-compose.yml` and `kamiwaza.json`
- Generates `docker-compose.appgarden.yml` with:
  - Removed `build` contexts (uses pre-built images)
  - Fixed port mappings (single port values)
  - Removed bind mounts (uses named volumes only)
  - Updated image tags to `v{version}` from `kamiwaza.json`
  - Added `image` fields for services with only `build` contexts
    - Image naming: `kamiwazaai/{extension-name}-{service-name}:v{version}`
    - Extension name from directory/kamiwaza.json
    - Service name from docker-compose.yml service key
    - Version from kamiwaza.json

**Example transformation:**

Before (`docker-compose.yml`):
```yaml
services:
  backend:
    build:
      context: .
      dockerfile: backend/Dockerfile
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
```

After (`docker-compose.appgarden.yml`):
```yaml
services:
  backend:
    image: kamiwazaai/myapp-backend:v1.0.0
    ports:
      - "8000"
    volumes:
      - backend_data:/app/data

volumes:
  backend_data:
```

**Important:** Run `make sync-compose` after:
- Changing `version` in `kamiwaza.json`
- Modifying `docker-compose.yml`
- Building new image versions

### Step 7: Validate with `make validate`

Validate all extension metadata and configurations before committing.

**Command:**
```bash
make validate
```

**What it validates:**
- `kamiwaza.json` format and required fields
- Docker Compose file syntax
- App Garden compatibility (no bind mounts, correct port format)
- Image format and accessibility
- Resource limits defined
- No build contexts in appgarden files
- Extra hosts configuration (if using host.docker.internal)
- **Services only**: Extension name starts with "service-" prefix
- **Tools only**: Extension name starts with "tool-" or "mcp-" prefix

**Manual verification required (Apps only):**

Since `make validate` performs static file checks only, you must manually verify your app's health endpoint:

- `/health` endpoint exists and responds with HTTP 200
- Test locally: `curl http://localhost:8000/health`
- Response should be valid JSON with `{"status": "healthy"}`
- Response time should be < 1 second

**Fix issues:** If validation fails, address the reported issues and run `make sync-compose` if needed.

### Step 8: Build Registry with `make build-registry`

Generate the extension registry JSON files for catalog publishing.

**Command:**
```bash
make build-registry
```

**What it does:**
- Cleans and recreates the entire `build/` directory (ephemeral working directory)
- Scans all extensions in `apps/`, `services/`, and `tools/`
- Aggregates metadata from `kamiwaza.json` files
- Embeds `docker-compose.appgarden.yml` content into catalog files
- Copies preview images to registry structure
- Generates catalog files in `build/kamiwaza-extension-registry/garden/default/`

**Output structure:**
```
build/  (ephemeral working directory - cleaned on each run)
└── kamiwaza-extension-registry/
    ├── package-setup.sh
    ├── serve-registry.py
    ├── README.md
    ├── kamiwaza-registry.env.template
    └── garden/
        └── default/
            ├── apps.json
            ├── tools.json
            └── app-garden-images/
                └── *.png

dist/  (distribution packages - persistent)
└── kamiwaza-registry-YYYYMMDD-HHMMSS.tar.gz
```

**Important:** The `build/` directory is completely cleaned on each run and contains ephemeral working files. Distribution packages are saved to `dist/` via `make package-registry`.

**When to run:** Before releasing or publishing extensions to the catalog.

### Step 9: Load Extensions into Kamiwaza (Developer Testing)

After building your extension registry, you can load extensions into a running Kamiwaza instance for testing. There are three methods depending on your development setup.

#### Option 1: Local Filesystem (Same Host)

**Best for:** Development when extensions repo and Kamiwaza instance are on the same machine.

**Setup:**
1. Build the registry:
   ```bash
   make build-registry
   ```

2. Configure Kamiwaza's `env.sh` file:
   ```bash
   export KAMIWAZA_EXTENSION_STAGE=LOCAL
   export KAMIWAZA_EXTENSION_LOCAL_STAGE_URL="file:///path/to/kamiwaza-extensions/build/kamiwaza-extension-registry"
   ```

3. Restart Kamiwaza to apply the configuration

**How it works:**
- Extensions automatically load when you visit the Apps, Services, or Tools pages in Kamiwaza
- Changes are detected when the `version` field in `kamiwaza.json` increases
- No need to push images or templates - reads directly from filesystem
- Fastest iteration cycle for development

**Example workflow:**
```bash
# 1. Make changes to your extension
vim apps/my-app/backend/app/main.py

# 2. Bump version in kamiwaza.json
# Change "version": "1.0.0" to "version": "1.0.1"

# 3. Rebuild images and registry
make build TYPE=app NAME=my-app
make sync-compose
make build-registry

# 4. Reload Kamiwaza Apps page - new version appears automatically
```

#### Option 2: HTTPS Server (Different Hosts / Airgapped)

**Best for:** Development when extensions repo and Kamiwaza instance are on different machines, or for airgapped environments.

**Setup:**
1. Build the registry:
   ```bash
   make build-registry
   ```

2. Start the HTTPS server (on extensions repo machine):
   ```bash
   make serve-registry PORT=58888
   ```

   This starts an HTTPS server with a self-signed certificate serving the registry.

3. Configure Kamiwaza's `env.sh` file (on Kamiwaza machine):
   ```bash
   export KAMIWAZA_EXTENSION_STAGE=LOCAL
   export KAMIWAZA_EXTENSION_LOCAL_STAGE_URL="https://extension-server:58888"
   ```

4. Restart Kamiwaza to apply the configuration

**How it works:**
- Extensions load from the HTTPS endpoint when you visit Apps, Services, or Tools pages
- Version increments in `kamiwaza.json` trigger updates
- Self-signed certificate is automatically generated
- Useful for team development across multiple machines

**Server options:**
- Default port: 58888
- Custom port: `make serve-registry PORT=9000`
- Server runs until stopped with Ctrl+C

#### Option 3: Push to Kamiwaza Instance API

**Best for:** Testing template metadata and deployment configurations without rebuilding the entire registry.

**Setup:**
1. Build the registry:
   ```bash
   make build-registry
   ```

2. Push a specific app template:
   ```bash
   make kamiwaza-push TYPE=app NAME=my-app
   ```

   This pushes the app template directly to your Kamiwaza instance's API.

3. Force overwrite with `TEMPLATE_ID` parameter:
   ```bash
   make kamiwaza-push TYPE=app NAME=my-app TEMPLATE_ID=existing-template-uuid
   ```

   Use `TEMPLATE_ID` to force overwrite an existing template, useful when:
   - Updating an existing template with a different name
   - Replacing a template without incrementing version
   
4. List existing templates:
   ```bash
   make kamiwaza-list
   ```

**How it works:**
- Pushes template metadata to Kamiwaza's `/apps/app_templates` API endpoint
- Requires Kamiwaza instance to be running and accessible
- Reads template data from `build/kamiwaza-extension-registry/garden/default/apps.json`
- Uses authentication from your Kamiwaza configuration

**Authentication:**
- Uses credentials from environment or prompts interactively
- Set `KAMIWAZA_API_URL` to your instance (default: http://localhost)
- Configure in `~/.kamiwaza/config.yaml` or set `KAMIWAZA_USERNAME`/`KAMIWAZA_PASSWORD`

**Example:**
```bash
# Push updated template to Kamiwaza
make kamiwaza-push TYPE=app NAME=document-processor

# Force overwrite existing template
make kamiwaza-push TYPE=app NAME=document-processor TEMPLATE_ID=a1b2c3d4-uuid

# List all templates on the instance
make kamiwaza-list

# List templates in JSON format
make kamiwaza-list FORMAT=json
```



#### Version Detection

**Important:** Kamiwaza detects extension updates by comparing the `version` field in `kamiwaza.json`. To see your changes:

1. Increment the version:
   ```json
   {
     "name": "my-app",
     "version": "1.0.1"  // Changed from 1.0.0
   }
   ```

2. Rebuild the registry:
   ```bash
   make build-registry
   ```

3. Reload the Apps, Services, or Tools page in Kamiwaza

The new version will appear in the catalog automatically.

## Packaging and Distribution

### Full Release with `make publish`

Publish both the extension registry and multi-arch Docker images in a single command.

**Command:**
```bash
make publish STAGE={dev|stage|prod}
```

**Prerequisite:** set per-stage AWS profiles in `.env`:
```bash
AWS_PROFILE_DEV=kamiwaza-registry-dev
AWS_PROFILE_STAGE=kamiwaza-registry-stage
AWS_PROFILE_PROD=kamiwaza-registry-prod
```

**What it does:**
- Runs `make publish-registry` - Uploads registry metadata to S3
- Runs `make publish-images` - Builds and pushes multi-arch Docker images

**Examples:**
```bash
# Publish everything to dev (default)
make publish

# Publish everything to production
make publish STAGE=prod

# Preview what would be published
make publish-dry-run STAGE=prod
```

This is the recommended command for releasing extensions to a registry.

### Publish Multi-Arch Docker Images with `make publish-images`

Build and push Docker images for multiple architectures (linux/amd64 and linux/arm64) to your container registry.

**Command:**
```bash
make publish-images STAGE={dev|stage|prod}
```

**What it does:**
- Builds Docker images for both `linux/amd64` and `linux/arm64` architectures
- Pushes images directly to the registry using `docker buildx build --push`
- Creates a multi-arch manifest automatically
- Tags images based on the deployment stage

**Prerequisites:**

Multi-arch builds require Docker Buildx with the `docker-container` driver and QEMU for cross-platform emulation:

```bash
# One-time setup (if not already configured)
docker buildx create --use --name multiarch --driver docker-container
docker run --privileged --rm tonistiigi/binfmt --install all
```

**Stage-based tagging:**

| Stage | Tag Format | Example | Use Case |
|-------|------------|---------|----------|
| dev | {version}-dev | 1.0.0-dev | Development testing |
| stage | {version}-stage | 1.0.0-stage | QA/staging environments |
| prod | {version} | 1.0.0 | Production deployments |

**Examples:**
```bash
# Build and push multi-arch images for dev (default)
make publish-images

# Build and push for production
make publish-images STAGE=prod

# Build for specific platforms only
make publish-images PLATFORMS=linux/amd64

# Preview what would be built (dry run)
make publish-images-dry-run STAGE=prod
```

**Environment variables:**
- `STAGE` - Deployment stage: dev, stage, or prod (default: dev)
- `PLATFORMS` - Comma-separated platforms (default: linux/amd64,linux/arm64)

**Note:** For local development and testing, use `make build` which builds single-arch images for your host platform and loads them into the local Docker daemon.

### Package Registry with `make package-registry`

Create a distributable tarball containing the registry and Docker images for offline installation.

**Command:**
```bash
make package-registry
```

**What it does:**
- Runs `make build-registry` if registry doesn't exist
- Creates timestamped tarball in `dist/kamiwaza-registry-YYYYMMDD-HHMMSS.tar.gz`
- Packages the entire `build/kamiwaza-extension-registry/` directory
- Preserves all catalog files, helper scripts, and Docker images

**Output:**
```
dist/
└── kamiwaza-registry-20251014-120000.tar.gz
```

**Distribution:**
```bash
# Extract on target system
tar -xzf kamiwaza-registry-20251014-120000.tar.gz
cd kamiwaza-extension-registry
./package-setup.sh
```

## Cleanup Commands

Manage build artifacts and dependencies with a hierarchy of clean targets.

### Clean Build Artifacts

Remove build files while preserving dependencies and distribution packages:

```bash
make clean
```

**What it removes:**
- `build/` directory (ephemeral working files)
- Python bytecode (`__pycache__`, `*.pyc`)
- Test caches (`.pytest_cache`, `.mypy_cache`, etc.)
- Coverage files

**What it preserves:**
- `dist/` packages
- `node_modules/`
- `.venv/`

### Clean Dependencies

Remove all dependency caches:

```bash
make clean-deps
```

**What it removes:**
- All `node_modules/` directories (Node.js)
- `.venv/` directory (Python)

### Clean Everything

Remove all build artifacts and dependencies (except dist/):

```bash
make clean-all
```

Equivalent to: `make clean clean-deps`

### Clean Distribution Packages

Remove everything including distribution packages (nuclear option):

```bash
make distclean
```

**What it removes:**
- Everything from `clean-all`
- `dist/` directory with all packaged tarballs

**Use when:** Starting completely fresh or freeing maximum disk space.

**Hierarchy:**
```
clean          # Build artifacts only
clean-deps     # Dependencies only
clean-all      # clean + clean-deps
distclean      # clean-all + dist/
```

## Complete Workflow Example

Here's the complete workflow for creating and releasing an extension:

```bash
# 1. Create new extension
make new TYPE=app NAME=my-awesome-app

# 2. Edit kamiwaza.json
cd apps/my-awesome-app
vim kamiwaza.json  # Configure metadata

# 3. Implement your extension
# ... create Dockerfiles, write code ...

# 4. Test locally
docker-compose up --build
curl http://localhost:8000/health

# 5. Build images
make build TYPE=app NAME=my-awesome-app

# 6. Run tests
make test TYPE=app NAME=my-awesome-app

# 7. Sync App Garden compose
make sync-compose

# 8. Validate
make validate

# 9. Build registry
make build-registry

# 10. Load into Kamiwaza for testing (see Step 9 options)
# Option 1: Local filesystem
export KAMIWAZA_EXTENSION_STAGE=LOCAL
export KAMIWAZA_EXTENSION_LOCAL_STAGE_URL="file:///path/to/build/kamiwaza-extension-registry"

# Option 2: HTTPS server
make serve-registry

# Option 3: Push to Kamiwaza API
make kamiwaza-push TYPE=app NAME=my-awesome-app

# 11. Commit and push
git add apps/my-awesome-app
git commit -m "Add my-awesome-app extension"
git push
```

## CI/Release Pipeline Order

The complete CI/release pipeline:

**Individual extension workflow:**
1. `make build TYPE={type} NAME={name}` - Build Docker images (local, single-arch)
2. `make test TYPE={type} NAME={name}` - Run tests
3. `make sync-compose` - Generate App Garden compose files
4. `make validate` - Validate metadata and configs
5. `make build-registry` - Build extension registry
6. Load into Kamiwaza for testing (see Step 9)
7. `make publish STAGE=prod` - Build/push multi-arch images AND publish registry

**Full CI pipeline (all extensions):**
```bash
make ci-pipeline
```

This runs:
1. `make build-all` - Build all extensions
2. `make test-all` - Test all extensions
3. `make sync-compose` - Sync all compose files
4. `make validate` - Validate all extensions
5. `make build-registry` - Build registry
6. `make package-registry` - Create distribution tarball

### Step 10: Import to Kamiwaza (External Deployment)

This step is for deploying extensions to a running Kamiwaza instance.

**Option 1: Via Web UI**
1. Navigate to the Extensions page
2. Click "Sync Extensions" button to import from the remote catalog
3. Your extension will be imported automatically

**Option 2: Via API**
```bash
# Sync all extensions from catalog
curl -X POST https://localhost/api/v1/apps/remote/sync \
  -H "Authorization: Bearer YOUR_TOKEN"

# Sync specific extensions by name
curl -X POST https://localhost/api/v1/apps/remote/sync \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"names": ["your-app-name", "your-tool-name"]}'
```

## AI Model Integration

There are two different mechanisms for integrating AI models into your extensions, depending on how your app connects to the models:

> **⚠️ Important**: `KAMIWAZA_API_URL` and `OPENAI_BASE_URL` are reserved variables in Kamiwaza and should not be used in your app at this point. Once automatic variable generation is implemented in Kamiwaza, this will change.

### 1. Using the Kamiwaza SDK

If your app uses the Kamiwaza SDK, it can directly discover and connect to deployed models:

```python
 # Example using Kamiwaza SDK
  import os
  from kamiwaza_sdk import KamiwazaClient

  # Initialize client using injected environment variable
  api_url = os.environ.get("KAMIWAZA_API_URL", "https://host.docker.internal/api")
  client = KamiwazaClient(api_uri=api_url)

  # Discover available models
  models = client.models.list()
  deployed_models = [m for m in models if m.status == "DEPLOYED"]

  # Connect to a specific model
  model = client.models.get("Qwen2.5-VL-3B-Instruct-bf16")
  if model and model.status == "DEPLOYED":
      # Use the model directly through SDK
      response = model.generate(messages=[{"role": "user", "content": "Hello"}])
```

**Benefits of SDK approach:**
- Direct model discovery and connection
- Automatic port resolution
- Built-in error handling and retry logic
- No need for environment variable injection

### 2. OpenAI-Compatible REST Endpoints

For apps that are designed to connect via OpenAI-compatible REST endpoints, the Extensions subsystem can inject environment variables pointing to OpenAI-compatible endpoints.

The Extensions subsystem automatically provides OpenAI-compatible environment variables when an AI model is defined at deployment time:

```bash
OPENAI_BASE_URL=http://host.docker.internal:{model_port}/v1
```

Where `{model_port}` is the load balancer port for the deployed model (e.g., 61104).

### Template Variables

The Extensions subsystem supports template variables in environment values that are substituted at deployment time:

| Variable | Description | Example Value |
|----------|-------------|---------------|
| `{app_port}` | Application's assigned load balancer port | `61110` |
| `{model_port}` | Deployed AI model's service port | `61111` |
| `{deployment_id}` | Unique deployment UUID | `a1b2c3d4-...` |
| `{app_name}` | Application deployment name | `my-app-instance` |

Example usage in your compose file:
```yaml
environment:
  - PUBLIC_URL=http://localhost:{app_port}
  - MODEL_ENDPOINT=http://localhost:{model_port}/v1
  - INSTANCE_ID={deployment_id}
  - SERVICE_NAME={app_name}_worker
```

These variables are automatically substituted when the app is deployed.


> **Important:** The value injected by the Extensions subsystem must include the actual numeric port. After deployment, open the App details page > **Environment**, and confirm `OPENAI_BASE_URL` resolves to something like `http://host.docker.internal:61104/v1`. If you still see the literal `{model_port}` placeholder, override the variable with the correct port from the **Models** view; otherwise AI calls will fail with connection errors.

**Example using custom HTTP client:**
```python
# Example using custom HTTP client (like auto-ids app)
import aiohttp
import json
import os

class AIClient:
    def __init__(self):
        self.endpoint = os.getenv("OPENAI_BASE_URL", "").rstrip("/")
        self.model = os.getenv("AI_MODEL", "Qwen2.5-VL-3B-Instruct-bf16")
        self.session = None

    async def connect(self):
        """Connect to the AI service"""
        self.session = aiohttp.ClientSession()
        # Test connection
        async with self.session.get(f"{self.endpoint}/models") as response:
            return response.status == 200

    async def generate_response(self, messages, max_tokens=100):
        """Generate response using OpenAI-compatible API"""
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.7
        }

        async with self.session.post(
            f"{self.endpoint}/chat/completions",
            json=payload,
            headers={"Content-Type": "application/json"}
        ) as response:
            if response.status == 200:
                result = await response.json()
                return result["choices"][0]["message"]["content"]
            else:
                error_text = await response.text()
                raise Exception(f"AI request failed: {error_text}")

    async def close(self):
        """Close the session"""
        if self.session:
            await self.session.close()
```

**Alternative: Using OpenAI client library:**
```python
# Example using OpenAI client library
import openai

# Use environment variables injected by Extensions subsystem
client = openai.OpenAI(
    base_url=os.getenv("OPENAI_BASE_URL"),
    api_key="dummy"  # Kamiwaza doesn't require API keys
)

# Make requests using standard OpenAI format
response = client.chat.completions.create(
    model="Qwen2.5-VL-3B-Instruct-bf16",
    messages=[{"role": "user", "content": "Hello"}],
    max_tokens=100
)
```

### Best Practices for AI Integration

#### For SDK-based Apps

1. **Use the Kamiwaza SDK**: Direct model discovery and connection
   ```python
   # ✅ Correct - Using SDK for model discovery
   from kamiwaza_sdk import KamiwazaClient
   
   client = KamiwazaClient(api_uri=os.getenv("KAMIWAZA_API_URI"))
   models = client.models.list()
   deployed_models = [m for m in models if m.status == "DEPLOYED"]
   ```

2. **Handle Model Selection**: Let users choose models via environment variables
   ```yaml
   environment:
     - PREFERRED_MODEL=${PREFERRED_MODEL:-any}
     - MODEL_TYPE=${MODEL_TYPE:-fast}  # fast, large, reasoning, vl
   ```

#### For OpenAI-Compatible Apps

1. **Use Standard OpenAI Format**: Always use OpenAI-compatible requests
   ```python
   # ✅ Correct - Standard OpenAI format payload
   payload = {
       "model": "Qwen2.5-VL-3B-Instruct-bf16",
       "messages": [{"role": "user", "content": "Hello"}],
       "max_tokens": 100,
       "temperature": 0.7
   }
   ```

2. **Implement Custom HTTP Client**: Use aiohttp or similar for direct HTTP requests
   ```python
   # ✅ Correct - Custom HTTP client approach
   async with self.session.post(
       f"{self.endpoint}/chat/completions",
       json=payload,
       headers={"Content-Type": "application/json"}
   ) as response:
       result = await response.json()
   ```

3. **Rely on Environment Variables**: Don't hardcode model endpoints
   ```yaml
   environment:
     - OPENAI_BASE_URL=${OPENAI_BASE_URL:-}  # Injected by Extensions subsystem
     - AI_MODEL=${AI_MODEL:-Qwen2.5-VL-3B-Instruct-bf16}
   
   ```

   > **⚠️ Important**: `OPENAI_BASE_URL` is a reserved variable in Kamiwaza and should not be redefined in your app.

4. **Handle Model Selection**: Let users choose models via environment variables
   ```yaml
   environment:
     - PREFERRED_MODEL=${PREFERRED_MODEL:-any}
     - MODEL_TYPE=${MODEL_TYPE:-fast}  # fast, large, reasoning, vl
   ```

### Load Balancer vs Direct Model Access

**Always use the load balancer approach** (provided by the Extensions subsystem):

```bash
# ✅ Correct - Via load balancer (Extensions default)
OPENAI_BASE_URL=http://host.docker.internal:61104/v1

# ❌ Wrong - Direct model connection
OPENAI_BASE_URL=http://host.docker.internal:59661/v1
```

**Why load balancer is better:**
- **Reliability**: Load balancer handles failover and routing
- **Compatibility**: Uses standard OpenAI format
- **Scalability**: Can route to multiple model instances
- **Consistency**: Same approach across all extensions

### Model Type Preferences

Extensions can specify model preferences that the Extensions subsystem will honor:

```json
{
  "name": "your-app",
  "preferred_model_type": "vl",
  "fail_if_model_type_unavailable": false,
  "preferred_model_name": "qwen",
  "fail_if_model_name_unavailable": false,
  "env_defaults": {
    "KAMIWAZA_API_URI": "https://host.docker.internal/api"
  }
}
```

Model types:
- `fast`: Small, quick models (< 70B parameters)
- `large`: Large models (≥ 70B parameters)
- `reasoning`: Reasoning-capable models (QwQ, DeepSeek-R1, etc.)
- `vl`: Vision-language models (for image processing)
- `any`: Any available model (default)

## Shared Libraries

Kamiwaza provides shared libraries for common functionality like authentication, session management, and middleware. These libraries are available for both Python (FastAPI backends) and TypeScript (Next.js frontends).

### Available Libraries

| Library | Language | Package Name | Purpose |
|---------|----------|--------------|---------|
| kamiwaza_auth | Python | `kamiwaza_auth-*.whl` | Authentication, session management, JWT utilities |
| @kamiwaza/auth | TypeScript | `kamiwaza-auth-*.tgz` | Auth middleware, session hooks, base path handling |

### Building Shared Libraries

Build the shared libraries before using them in your extensions:

```bash
# Build all shared libraries
make package-libs

# Build only Python package
make package-libs PYTHON_ONLY=1

# Build only TypeScript package
make package-libs TS_ONLY=1

# Clean and rebuild
make package-libs CLEAN=1
```

### Package Locations

After building, packages are located at:

| Package | Location |
|---------|----------|
| Python wheel | `shared/python/dist/kamiwaza_auth-{version}-py3-none-any.whl` |
| TypeScript tgz | `shared/typescript/kamiwaza-auth/kamiwaza-auth-{version}.tgz` |

### Installing in Your Extension

#### Python (FastAPI Backends)

1. **Copy the wheel** to your app's backend directory:
   ```bash
   cp shared/python/dist/kamiwaza_auth-0.1.0-py3-none-any.whl apps/my-app/backend/
   ```

2. **Add to requirements.txt** (at the top, before other deps):
   ```txt
   # Kamiwaza auth shared library (bundled wheel)
   ./kamiwaza_auth-0.1.0-py3-none-any.whl

   # Other dependencies...
   fastapi==0.115.6
   uvicorn[standard]==0.34.0
   ```

3. **The wheel is installed** automatically when Docker runs `pip install -r requirements.txt`

#### TypeScript (Next.js Frontends)

1. **Copy the package** to your app's frontend directory:
   ```bash
   cp shared/typescript/kamiwaza-auth/kamiwaza-auth-0.1.0.tgz apps/my-app/frontend/
   ```

2. **Add to package.json** dependencies:
   ```json
   {
     "dependencies": {
       "@kamiwaza/auth": "file:./kamiwaza-auth-0.1.0.tgz",
       "next": "^14.2.10",
       ...
     }
   }
   ```

3. **Run npm install** to link the package:
   ```bash
   cd apps/my-app/frontend && npm install
   ```

### Usage Examples

#### Python Imports

```python
# Identity and authentication
from kamiwaza_auth import get_identity, require_auth
from kamiwaza_auth.identity import Identity

# Session management endpoints (add to your FastAPI app)
from kamiwaza_auth.endpoints import create_session_router

# Error types
from kamiwaza_auth.errors import SessionExpiredError, AuthenticationError

# JWT utilities
from kamiwaza_auth.jwt import decode_jwt, calculate_session_expires_at
```

**Adding session endpoints to your FastAPI app:**

```python
from fastapi import FastAPI
from kamiwaza_auth.endpoints import create_session_router

app = FastAPI()

# Add standard session endpoints:
# - GET /session - Get current session info
# - GET /auth/login-url - Build login redirect URL
# - POST /auth/logout - Logout and get redirect URLs
app.include_router(create_session_router())

# Or with a custom prefix
app.include_router(create_session_router(prefix="/api"))
```

#### TypeScript Imports

```typescript
// Session management hooks and context
import { useSession, SessionProvider, AuthGuard } from '@kamiwaza/auth';

// Middleware for Next.js
import { createAuthMiddleware, DEFAULT_MIDDLEWARE_MATCHER } from '@kamiwaza/auth/middleware';

// Base path utilities for App Garden routing
import { getBasePath, useBasePath } from '@kamiwaza/auth/base-path';

// Server-side session fetching
import { fetchSession, logout } from '@kamiwaza/auth/session/fetch';
```

**Setting up middleware in Next.js:**

```typescript
// middleware.ts
import { createAuthMiddleware, DEFAULT_MIDDLEWARE_MATCHER } from '@kamiwaza/auth/middleware';

export const middleware = createAuthMiddleware();

export const config = {
  matcher: DEFAULT_MIDDLEWARE_MATCHER,
};
```

**Using session hooks in components:**

```tsx
// components/UserProfile.tsx
'use client';

import { useSession } from '@kamiwaza/auth';

export function UserProfile() {
  const { session, isLoading, error } = useSession();

  if (isLoading) return <div>Loading...</div>;
  if (error) return <div>Error: {error.message}</div>;
  if (!session) return <div>Not logged in</div>;

  return (
    <div>
      <p>Welcome, {session.name}</p>
      <p>Email: {session.email}</p>
    </div>
  );
}
```

### Important Notes

- **Packages are gitignored**: The `.whl` and `.tgz` files are excluded from version control
- **Build before Docker builds**: Run `make package-libs` before `make build TYPE=app NAME=...`
- **Version updates**: When shared libraries are updated, rebuild packages and copy to your apps
- **CI pipeline**: Include `make package-libs` in your CI workflow before building extensions

### Workflow Example

```bash
# 1. Build shared libraries
make package-libs

# 2. Copy to your app (if not already done)
cp shared/python/dist/kamiwaza_auth-*.whl apps/my-app/backend/
cp shared/typescript/kamiwaza-auth/kamiwaza-auth-*.tgz apps/my-app/frontend/

# 3. Build your extension
make build TYPE=app NAME=my-app

# 4. Test locally
cd apps/my-app && docker-compose up --build
```

## Configuration Best Practices

### URLs and Networking

1. **Inter-service communication**: Use service names
   ```yaml
   API_URL: http://backend:8000
   DATABASE_URL: postgres://user:pass@postgres:5432/db
   ```

2. **External APIs**: Use environment variables with defaults
   ```yaml
   EXTERNAL_API: ${EXTERNAL_API:-https://api.example.com}
   ```

3. **Kamiwaza API access**: Use `host.docker.internal`
4.
4. **Reverse proxy prefixes**: When your app is served under `/api`, set `API_ROOT_PATH=/api` so FastAPI generates correct OpenAPI URLs
   ```yaml
   KAMIWAZA_API_URL: ${KAMIWAZA_API_URL:-https://host.docker.internal/api}
   ```
   > **⚠️ Important**: `KAMIWAZA_API_URL` is a reserved variable in Kamiwaza and should not be redefined in your app.



### Resource Limits

Add resource constraints to prevent overconsumption:
```yaml
deploy:
  resources:
    limits:
      cpus: "1.0"
      memory: "512M"
```

### Health Checks

Include health checks for better monitoring:
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
  interval: 30s
  timeout: 10s
  retries: 3
```

## Registry Options

You can use any Docker-compatible registry:

- **Docker Hub**: `image: username/app:tag`
- **GitHub Container Registry**: `image: ghcr.io/org/app:tag`
- **Google Container Registry**: `image: gcr.io/project/app:tag`
- **Amazon ECR**: `image: 123456789.dkr.ecr.region.amazonaws.com/app:tag`
- **Private Registry**: `image: registry.company.com/app:tag`

For private registries, ensure Kamiwaza nodes are authenticated:
```bash
docker login registry.company.com
```

## Production Best Practice: Using Nginx Proxy

For production deployments with separate frontend and backend services, using an nginx proxy eliminates CORS issues and provides a single entry point:

### Benefits
- **No CORS configuration needed** - Everything is served from the same origin
- **Single port exposure** - Simplifies Kamiwaza routing
- **Better performance** - Nginx can serve static assets efficiently
- **Path-based routing** - Clean URL structure (e.g., `/api` for backend)
- **SSE Support** - Proper handling of Server-Sent Events and WebSocket connections

### Implementation

Add an nginx proxy service as your primary service:

```yaml
services:
  proxy:
    image: nginx:alpine
    ports:
      - "80"
    command: |
      sh -c "cat > /etc/nginx/nginx.conf << 'EOF'
      events { worker_connections 1024; }
      http {
        client_max_body_size 100M;
        upstream frontend { server frontend:3000; }
        upstream backend { server backend:8001; }

        server {
          listen 80;

          location /api/ {
            proxy_pass http://backend/;
            proxy_set_header Host \$$host;
            proxy_set_header X-Real-IP \$$remote_addr;
            proxy_set_header X-Forwarded-For \$$proxy_add_x_forwarded_for;
            # SSE-specific configuration
            proxy_http_version 1.1;
            proxy_set_header Connection '';
            proxy_set_header Cache-Control no-cache;
            proxy_buffering off;
            proxy_read_timeout 300;
            proxy_connect_timeout 300;
            proxy_send_timeout 300;
          }

          location / {
            proxy_pass http://frontend/;
            proxy_set_header Host \$$host;
            proxy_set_header X-Real-IP \$$remote_addr;
            proxy_set_header X-Forwarded-For \$$proxy_add_x_forwarded_for;
          }
        }
      }
      EOF
      nginx -g 'daemon off;'"
    depends_on:
      - frontend
      - backend

  frontend:
    image: your-frontend:latest
    environment:
      # Use proxy hostname for SSE, relative for API calls
      - NEXT_PUBLIC_API_BASE_URL=http://proxy/api
      - NEXT_PUBLIC_API_URL=/api
    # No ports exposed

  backend:
    image: your-backend:latest
    # No ports exposed
```

This approach ensures your app works consistently regardless of how Kamiwaza assigns ports or routes traffic.

## Real-Time Connections: SSE and WebSockets

Many modern applications require real-time updates (progress bars, live notifications, chat features). This section covers how to properly configure Server-Sent Events (SSE) and WebSocket connections in extensions.

### Understanding the Connection Challenge

**The Problem**: Real-time connections behave differently than regular HTTP requests:

- **Regular API calls**: Short-lived, browser handles relative URLs automatically
- **SSE/WebSocket connections**: Long-lived, require explicit hostnames for security

```javascript
// ✅ Regular API calls work with relative URLs
fetch('/api/data')  // Browser resolves automatically

// ❌ SSE connections fail with relative URLs
new EventSource('/api/sse/stream')  // Browser can't resolve hostname

// ✅ SSE connections need full URLs
new EventSource('http://proxy/api/sse/stream')  // Works correctly
```

### Frontend Configuration for Real-Time Connections

#### Environment Variables

Configure your frontend environment variables to handle both regular API calls and real-time connections:

```yaml
frontend:
  environment:
    # For SSE/WebSocket connections - needs full hostname
    - NEXT_PUBLIC_API_BASE_URL=http://proxy/api
    # For regular API calls - can use relative URLs
    - NEXT_PUBLIC_API_URL=/api
```

#### JavaScript Implementation

```javascript
// ✅ Correct SSE connection
const eventSource = new EventSource(`${process.env.NEXT_PUBLIC_API_BASE_URL}/sse/jobs`);

// ✅ Correct WebSocket connection
const ws = new WebSocket(`ws://proxy/api/ws`);

// ✅ Regular API calls still work with relative URLs
const response = await fetch('/api/data');
```

### Backend Configuration

#### SSE Endpoints

Mount your SSE router under the API prefix:

```python
# main.py
from app.routers import sse

# Mount SSE under /api for consistency
app.include_router(sse.router, prefix="/api/sse", tags=["sse"])
```

#### WebSocket Endpoints

```python
# For WebSocket connections
@app.websocket("/api/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    # Handle WebSocket logic
```

### Nginx Configuration for Real-Time Connections

The nginx proxy needs specific configuration to handle long-lived connections:

```nginx
location /api/ {
    proxy_pass http://backend/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;

    # Critical for SSE and WebSocket connections
    proxy_http_version 1.1;
    proxy_set_header Connection '';
    proxy_set_header Cache-Control no-cache;
    proxy_buffering off;

    # Extended timeouts for long-lived connections
    proxy_read_timeout 300;
    proxy_connect_timeout 300;
    proxy_send_timeout 300;
}
```

### Common Real-Time Connection Patterns

#### 1. Job Progress Updates

```javascript
// Frontend: Connect to job progress stream
const eventSource = new EventSource(`${API_BASE_URL}/sse/jobs`);

eventSource.addEventListener('job_progress', (event) => {
  const data = JSON.parse(event.data);
  updateProgressBar(data.progress);
  updateStatusMessage(data.stage);
});

eventSource.addEventListener('heartbeat', () => {
  console.log('Connection alive');
});
```

```python
# Backend: Send progress updates
async def broadcast_job_progress(job_id: str, progress: float, stage: str):
    data = {
        "job_id": job_id,
        "progress": progress,
        "stage": stage,
        "timestamp": datetime.now().isoformat()
    }
    await sse_service.broadcast_event('job_progress', data)
```

#### 2. Live Notifications

```javascript
// Frontend: Listen for notifications
const eventSource = new EventSource(`${API_BASE_URL}/sse/notifications`);

eventSource.addEventListener('notification', (event) => {
  const notification = JSON.parse(event.data);
  showNotification(notification.message, notification.type);
});
```

#### 3. Real-Time Chat

```javascript
// Frontend: WebSocket for chat
const ws = new WebSocket(`ws://proxy/api/ws/chat`);

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  displayMessage(message);
};

function sendMessage(text) {
  ws.send(JSON.stringify({ type: 'message', text }));
}
```

### Testing Real-Time Connections

#### From Container

```bash
# Test SSE endpoint
curl -N -H "Accept: text/event-stream" http://proxy/api/sse/jobs

# Test WebSocket endpoint
wscat -c ws://proxy/api/ws
```

#### From Frontend Container

```bash
# Test SSE through proxy
curl -N -H "Accept: text/event-stream" http://proxy/api/sse/jobs

# Test direct backend connection
curl -N -H "Accept: text/event-stream" http://backend:8001/api/sse/jobs
```

### Troubleshooting Real-Time Connections

#### Common Issues

1. **SSE Connection Fails**:
   - ✅ Check that `NEXT_PUBLIC_API_BASE_URL` includes full hostname
   - ✅ Verify nginx proxy configuration includes SSE-specific headers
   - ✅ Ensure backend SSE endpoint is mounted under `/api/sse`

2. **WebSocket Connection Fails**:
   - ✅ Use `ws://proxy/api/ws` not `ws://localhost/api/ws`
   - ✅ Ensure nginx proxy supports WebSocket upgrades
   - ✅ Check that backend WebSocket endpoint is accessible

3. **Connection Drops Frequently**:
   - ✅ Increase nginx timeout values
   - ✅ Implement client-side reconnection logic
   - ✅ Add heartbeat/ping mechanisms

#### Debug Commands

```bash
# Check if SSE endpoint is accessible
curl -v http://proxy/api/sse/status

# Test WebSocket connection
wscat -c ws://proxy/api/ws -v

# Check nginx logs
docker logs <proxy-container-name>

# Check backend logs
docker logs <backend-container-name>
```

### Best Practices

1. **Use nginx proxy for all real-time connections** - Don't expose backend ports directly
2. **Implement proper error handling** - Real-time connections can fail and need reconnection
3. **Add heartbeat mechanisms** - Keep connections alive and detect failures
4. **Use appropriate timeouts** - Balance between connection stability and resource usage
5. **Test thoroughly** - Real-time connections behave differently in containerized environments

## Networking Patterns in Containerized Apps

Understanding how different types of connections work in containerized environments is crucial for successful extension integration.

### Connection Types and Requirements

| Connection Type | URL Resolution | Hostname Required | Use Case |
|----------------|----------------|-------------------|----------|
| **Regular HTTP** | Browser auto-resolves | ❌ No | API calls, page loads |
| **SSE (EventSource)** | Manual resolution | ✅ Yes | Real-time updates, progress bars |
| **WebSocket** | Manual resolution | ✅ Yes | Chat, live collaboration |
| **Server-to-Server** | Service names | ❌ No | Database, internal APIs |

### URL Resolution Patterns

#### 1. Browser-to-Container Connections

```javascript
// ✅ Regular API calls - Browser handles resolution
fetch('/api/data')  // → http://current-host/api/data

// ❌ Real-time connections - Need explicit hostname
new EventSource('/api/sse/stream')  // Fails - no hostname

// ✅ Real-time connections - Full URL required
new EventSource('http://proxy/api/sse/stream')  // Works
```

#### 2. Container-to-Container Connections

```yaml
# ✅ Use service names for internal communication
environment:
  - DATABASE_URL=postgres://user:pass@postgres:5432/db
  - REDIS_URL=redis://redis:6379
  - API_URL=http://backend:8000
```

#### 3. Container-to-Host Connections

```yaml
# ✅ Use host.docker.internal for host services
environment:
  - KAMIWAZA_API_URI=http://host.docker.internal:61116/api
  - EXTERNAL_API=http://host.docker.internal:8080
```

### Environment Variable Strategy

Configure your app to handle different connection types:

```yaml
frontend:
  environment:
    # For real-time connections (SSE/WebSocket)
    - NEXT_PUBLIC_API_BASE_URL=http://proxy/api
    # For regular API calls
    - NEXT_PUBLIC_API_URL=/api
    # For server-to-server communication
    - INTERNAL_API_URL=http://backend:8000
```

```javascript
// Frontend code handles different connection types
const apiClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL  // Relative for regular calls
});

const eventSource = new EventSource(
  `${process.env.NEXT_PUBLIC_API_BASE_URL}/sse/stream`  // Full URL for SSE
);
```

### Common Networking Mistakes

#### ❌ Wrong: Exposing Backend Ports Directly

```yaml
# Don't do this - exposes backend directly
backend:
  ports:
    - "8000:8000"  # ❌ Bypasses nginx proxy
```

#### ✅ Correct: Use Nginx Proxy

```yaml
# Do this - single entry point through nginx
proxy:
  ports:
    - "80"
  # Routes /api/* to backend

backend:
  # No ports exposed - accessed through proxy
```

#### ❌ Wrong: Hardcoded URLs

```yaml
# Don't do this - hardcoded URLs break in different environments
environment:
  - API_URL=http://localhost:8000  # ❌ Won't work in containers
```

#### ✅ Correct: Environment Variables with Defaults

```yaml
# Do this - flexible configuration
environment:
  - API_URL=${API_URL:-http://backend:8000}  # ✅ Works everywhere
```

### Testing Network Connectivity

#### From Host Machine

```bash
# Test proxy endpoint
curl http://localhost/api/health

# Test SSE stream
curl -N -H "Accept: text/event-stream" http://localhost/api/sse/jobs
```

#### From Container

```bash
# Test internal service communication
curl http://backend:8000/health

# Test through proxy
curl http://proxy/api/health

# Test SSE through proxy
curl -N -H "Accept: text/event-stream" http://proxy/api/sse/jobs
```

#### Debug Network Issues

```bash
# Check container networking
docker network ls
docker network inspect <network-name>

# Check service resolution
docker exec <container> nslookup backend
docker exec <container> nslookup proxy

# Test connectivity
docker exec <container> ping backend
docker exec <container> curl http://backend:8000/health
```

### Network Security Considerations

1. **Don't expose unnecessary ports** - Use nginx proxy as single entry point
2. **Use service names for internal communication** - Don't use localhost
3. **Validate external URLs** - Use environment variables with validation
4. **Implement proper CORS** - Let nginx proxy handle CORS, not individual services
5. **Use HTTPS in production** - Configure SSL termination at nginx level

## Troubleshooting

### Common Issues

1. **Port conflicts**: Always use dynamic port allocation
2. **Volume mount errors**: Use named volumes, not local paths
3. **Image pull failures**: Ensure images are pushed and accessible
4. **Service discovery**: Use service names for internal communication
5. **SSE/WebSocket connection failures**: Use full URLs with hostname for real-time connections
6. **CORS issues**: Use nginx proxy instead of exposing backend ports directly
7. **Network connectivity**: Test both internal (service-to-service) and external (browser-to-container) connections

### AI Integration Issues

1. **Model Connection Failures**:
   - ✅ Verify `OPENAI_BASE_URL` is injected by the Extensions subsystem
   - ✅ Ensure the value does **not** contain the `{lb_port}` placeholder—replace it with the actual numeric load balancer port from the Kamiwaza UI
   - ✅ If docs fail to load, confirm `API_ROOT_PATH` matches the proxy prefix (e.g., `/api`)
   - ✅ Use standard OpenAI format, not model-specific formats
   - ✅ Check model deployment status in Kamiwaza UI
   - ❌ Don't hardcode model ports or endpoints

2. **MLX Model Issues**:
   - Use OpenAI format with `model` field included
   - Rely on load balancer routing, not direct MLX connection
   - For vision models, embed images in message content (OpenAI format)

3. **Engine Mismatch Issues**:
   - If you see `engine: "vllm"` but `engine_name: "mlx"`, this is a known Kamiwaza bug
   - Apps should handle both `engine` and `engine_name` fields when detecting model types
   - The load balancer approach avoids these detection issues

4. **Environment Variable Issues**:
   ```bash
   # Check if variables are properly injected
   docker inspect <container-name> | grep -A 10 '"Env":'
   
   # Look for:
   OPENAI_BASE_URL=http://host.docker.internal:{model_port}/v1
   ```

### Debugging Tips

1. Check deployment logs in Kamiwaza UI
2. Verify images are accessible:
   ```bash
   docker pull yourusername/app:tag
   ```
3. Test compose file locally first
4. Use environment variable defaults for flexibility
5. **Test AI connection**: Verify model endpoints respond to OpenAI format requests
6. **Check model deployment**: Ensure target models are in "DEPLOYED" status

## Example: AI-Powered Apps

### Example 1: Document Processing App (DocuPro) - SDK Approach

```yaml
version: '3.8'

services:
  backend:
    image: kamiwazaai/docupro-backend:latest
    ports:
      - "8000"
    environment:
      # Extensions subsystem will inject OPENAI_BASE_URL and KAMIWAZA_API_URL automatically
      - PREFERRED_MODEL_TYPE=vl  # Vision-language for document processing
    volumes:
      - docupro-storage:/app/storage
    depends_on:
      - redis

  redis:
    image: redis:7-alpine
    volumes:
      - redis-data:/data

volumes:
  redis-data:
  docupro-storage:
```

**Backend code using SDK:**
```python
# docupro_backend.py
from kamiwaza_sdk import KamiwazaClient
import os

class DocuProService:
    def __init__(self):
        self.client = KamiwazaClient(
            api_uri=os.getenv("KAMIWAZA_API_URL")
        )

    def get_vision_model(self):
        """Find and return a deployed vision-language model"""
        models = self.client.models.list()
        vl_models = [
            m for m in models
            if m.status == "DEPLOYED" and "vl" in m.name.lower()
        ]
        return vl_models[0] if vl_models else None

    def process_document(self, document_path):
        """Process document using vision model"""
        model = self.get_vision_model()
        if not model:
            raise Exception("No vision model available")

        # Use SDK to generate response
        response = model.generate(
            messages=[{
                "role": "user",
                "content": f"Analyze this document: {document_path}"
            }]
        )
        return response
```

### Example 2: AI Chatbot App - OpenAI-Compatible Approach

```yaml
version: '3.8'

services:
  web:
    image: kamiwazaai/appgarden-ai-chatbot:latest
    ports:
      - "3000"
    environment:
      # Extensions subsystem injects OPENAI_BASE_URL and KAMIWAZA_API_URL
      - PREFERRED_MODEL_TYPE=${PREFERRED_MODEL_TYPE:-fast}
    depends_on:
      - postgres
      - redis

  postgres:
    image: postgres:15-alpine
    environment:
      - POSTGRES_DB=chatbot
      - POSTGRES_USER=chatbot
      - POSTGRES_PASSWORD=chatbot_password
    volumes:
      - postgres-data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    volumes:
      - redis-data:/data

volumes:
  postgres-data:
  redis-data:
```

**Backend code using custom HTTP client:**
```python
# chatbot_backend.py
import aiohttp
import json
import os

class ChatbotService:
    def __init__(self):
        self.endpoint = os.getenv("KAMIWAZA_API_URL", "").rstrip("/")
        self.model = os.getenv("AI_MODEL", "Qwen2.5-VL-3B-Instruct-bf16")
        self.session = None

    async def connect(self):
        """Connect to the AI service"""
        self.session = aiohttp.ClientSession()
        # Test connection
        async with self.session.get(f"{self.endpoint}/models") as response:
            return response.status == 200

    async def generate_response(self, user_message):
        """Generate chatbot response using OpenAI-compatible API"""
        try:
            payload = {
                "model": self.model,
                "messages": [{"role": "user", "content": user_message}],
                "max_tokens": 150,
                "temperature": 0.7
            }

            async with self.session.post(
                f"{self.endpoint}/chat/completions",
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return result["choices"][0]["message"]["content"]
                else:
                    error_text = await response.text()
                    return f"Error: {error_text}"
        except Exception as e:
            return f"Error: {str(e)}"

    async def close(self):
        """Close the session"""
        if self.session:
            await self.session.close()
```

**Key differences between approaches:**

| Aspect | SDK Approach | OpenAI-Compatible Approach |
|--------|-------------|---------------------------|
| **Model Discovery** | Automatic via SDK | Manual via environment variables |
| **Port Resolution** | Handled by SDK | Requires environment variable injection |
| **Error Handling** | Built into SDK | Manual implementation needed |
| **Dependencies** | Requires Kamiwaza SDK | Uses custom HTTP client (aiohttp) or OpenAI client |
| **Flexibility** | Direct API access | Limited to OpenAI-compatible endpoints |
| **Implementation** | SDK handles connection logic | Custom connection and error handling |

## Example: DocuPro App

Here's a complete example of adding the DocuPro document processing app:

**docker-compose.yml** (adapted for Kamiwaza):
```yaml
version: '3.8'

services:
  frontend:
    image: kamiwazaai/docupro-frontend:latest
    ports:
      - "3001"
    environment:
      - NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL:-http://backend:8000/api}
      - API_URL=http://backend:8000/api
    depends_on:
      - backend

  backend:
    image: kamiwazaai/docupro-backend:latest
    ports:
      - "8000"
    environment:
      - USE_MLX_VLM=${USE_MLX_VLM:-false}
      - REDIS_URL=redis://redis:6379
      - KAMIWAZA_API_URI=${KAMIWAZA_API_URI:-https://host.docker.internal/api}
    volumes:
      - docupro-storage:/app/storage
    depends_on:
      - redis

  redis:
    image: redis:7-alpine
    volumes:
      - redis-data:/data

volumes:
  redis-data:
  docupro-storage:
```

This configuration:
- Uses dynamic ports
- Connects services by name (backend, redis)
- Uses named volumes for persistence
- Allows Kamiwaza API integration via environment variables

## Operational Best Practices for Extensions (SSE, Proxy, Frontend builds)

### Frontend (Next.js) environment variables
- NEXT_PUBLIC_* variables are evaluated at build time. Changing them in Compose/runtime won’t affect an already-built image.
- When you change any NEXT_PUBLIC_* values, rebuild and retag the frontend image, push it, and update your app to use the new tag.
- Prefer proxy-relative URLs instead of absolute localhost addresses in browser code:
  - Recommended: `const sseUrl = '/api/sse/jobs'` and use `/api/*` for regular API calls.
  - Avoid: `http://localhost:8001/...` (breaks in containers and behind proxies).

### Proxy routing for real-time connections
- Use the proxy as the single entrypoint. Route all backend traffic under `/api`.
- Expose SSE at `/api/sse/*` so it rides the same `/api/` location block (no extra proxy stanza required).
- Critical proxy settings for SSE:
  ```nginx
  proxy_http_version 1.1;
  proxy_set_header Connection '';
  proxy_set_header Cache-Control no-cache;
  proxy_buffering off;
  proxy_read_timeout 300;
  proxy_connect_timeout 300;
  proxy_send_timeout 300;
  ```

### SSE in multi-process deployments
Extensions may run multiple workers/replicas. In-memory SSE connection lists won't work across processes. Use a pub/sub bus.

- Pattern:
  - Publishers (job updates) emit to a shared channel
  - Subscribers (the process holding the EventSource) forward events to the browser
- Backends:
  - Redis (recommended)
  - Postgres LISTEN/NOTIFY (works; serialize publishes)
- Postgres tip: Calling `publish()` concurrently on one asyncpg connection can raise `InterfaceError: another operation is in progress`.
  - Solution: enqueue updates to an `asyncio.Queue` and run a single background task that drains the queue and calls `broadcast.publish(...)` serially.
- Start/stop cross-cutting services in FastAPI lifespan (or startup/shutdown events):
  ```python
  @asynccontextmanager
  async def lifespan(app: FastAPI):
      # DB init
      await init_database()
      # Broadcaster init
      broadcast = Broadcast('postgres://user:pass@host:5432/db')  # or redis://...
      await broadcast.connect()
      # Start SSE publisher loop after broadcaster connects
      sse_service.start_background_tasks()
      yield
      await broadcast.disconnect()
  ```

### Extension deployment lifecycle
- The compose used by the Extensions subsystem is embedded in `garden/default/apps.json` or `garden/default/tools.json` (compose_yml field). Editing a local docker-compose file won't affect a deployed extension.
- Deployment checklist:
  1) Build and push images (frontend and backend) with new tags
  2) Update the extension's image tags (via UI or by updating the embedded compose)
  3) Redeploy/restart the extension
  4) For frontend changes involving NEXT_PUBLIC_* vars, ensure the image was rebuilt

### Quick validation commands
- From host (replace `{PORT}` with your app’s port):
  ```bash
  curl http://localhost:{PORT}/api/health
  curl -N -H "Accept: text/event-stream" http://localhost:{PORT}/api/sse/jobs
  ```
- From frontend container:
  ```bash
  curl http://proxy/api/health
  curl -N -H "Accept: text/event-stream" http://proxy/api/sse/jobs
  ```

### Common pitfalls and fixes
- **Undefined NEXT_PUBLIC_* in browser**: you changed envs but didn’t rebuild the frontend image → rebuild, retag, redeploy.
- **SSE uses localhost:8001**: absolute URL in code → switch to relative `/api/sse/jobs`.
- **No progress events / “Broadcasting to 0 clients”**: using in-memory SSE across workers → add pub/sub (Redis or Postgres) and subscribe in the process that owns the EventSource.
- **asyncpg InterfaceError on publish**: concurrent publishes → serialize via a single publisher loop.
- **Requests to `/sse/*` hitting the frontend**: route SSE under `/api/sse/*` or add an explicit `location /sse/` block to proxy to the backend.
