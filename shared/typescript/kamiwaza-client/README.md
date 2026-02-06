# @kamiwaza/client

TypeScript SDK for the Kamiwaza platform. Mirrors the official Python SDK structure.

## Installation

```bash
# From the repository
pnpm add @kamiwaza/client

# Or using the tgz package
pnpm add ./kamiwaza-client-0.1.0.tgz
```

## Quick Start

```typescript
import { KamiwazaClient } from '@kamiwaza/client';

// Create client with API key
const client = new KamiwazaClient({
  baseUrl: 'https://kamiwaza.example.com/api',
  apiKey: 'your-api-key',
});

// List active model deployments
const deployments = await client.serving.listActiveDeployments();
console.log(deployments);
```

## Environment Variables

The client reads configuration from environment variables if not provided directly:

| Variable | Description |
|----------|-------------|
| `KAMIWAZA_API_URL` or `KAMIWAZA_BASE_URL` | Base URL for the API |
| `KAMIWAZA_PUBLIC_API_URL` | Public URL for model endpoints |
| `KAMIWAZA_API_KEY` or `KAMIWAZA_API_TOKEN` | API key for authentication |

## Authentication

### API Key Authentication

For server-to-server communication with a static API key:

```typescript
const client = new KamiwazaClient({
  baseUrl: 'https://kamiwaza.example.com/api',
  apiKey: process.env.KAMIWAZA_API_KEY,
});
```

### ForwardAuth Authentication

For App Garden apps running behind Traefik ForwardAuth:

```typescript
import { KamiwazaClient, ForwardAuthAuthenticator, forwardAuthHeaders } from '@kamiwaza/client';

// In an API route handler
const authHeaders = forwardAuthHeaders(request.headers);
const client = new KamiwazaClient({
  baseUrl: process.env.KAMIWAZA_API_URL,
  authenticator: new ForwardAuthAuthenticator(authHeaders),
});
```

## Services

### ServingService

Manage model deployments:

```typescript
// List all deployments
const deployments = await client.serving.listDeployments();

// List active deployments with endpoints
const active = await client.serving.listActiveDeployments();

// Get specific deployment
const deployment = await client.serving.getDeployment('deployment-uuid');

// Deploy a model
const deploymentId = await client.serving.deployModel({
  m_id: 'model-uuid',
  engine_name: 'vllm',
});

// Stop a deployment
await client.serving.stopDeployment('deployment-uuid');
```

## API Mapping

| Python SDK | TypeScript SDK |
|------------|----------------|
| `client.serving.list_deployments()` | `client.serving.listDeployments()` |
| `client.serving.list_active_deployments()` | `client.serving.listActiveDeployments()` |
| `client.serving.get_deployment(id)` | `client.serving.getDeployment(id)` |
| `client.serving.deploy_model(req)` | `client.serving.deployModel(req)` |
| `client.serving.stop_deployment(id)` | `client.serving.stopDeployment(id)` |

## Development

```bash
# Install dependencies
pnpm install

# Build
pnpm build

# Type check
pnpm typecheck

# Run tests
pnpm test
```

## License

MIT
