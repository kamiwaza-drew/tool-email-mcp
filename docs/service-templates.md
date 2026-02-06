# Building Services (App Garden)

This doc explains how services differ from apps and tools, and how to build a service template correctly.

## What changed

The system now treats extensions as three explicit types:

- Apps: user-facing applications.
- Services: backend utilities and infrastructure (for example vector databases).
- Tools: tool servers (Tool Shed / MCP style utilities).

Apps and services live in App Garden, while tools live in Tool Shed. All three share the same template and deployment tables, but the type and name prefix drive routing and behavior.

## Taxonomy and classification rules

- `template_type` is stored on templates with allowed values: `app`, `tool`, `service`.
- API and JSON payloads accept plural values (`apps`, `tools`, `services`) and normalize to singular.
- If `template_type` is missing, the name prefix is used:
  - `tool-` or `mcp-` -> tool
  - `service-` -> service
  - anything else -> app
- Deployments are classified by deployment name (not the template). If a deployment name does not start with `service-`, it will be treated as an app in filters and routing.

## Catalog placement and sync

- Services are sourced from the App Garden catalog (`garden/v2/apps.json`). There is no `services.json`.
- Tools are sourced from the Tool Shed catalog (`garden/v2/tools.json`).
- App Garden remote sync only pulls the apps catalog, so services must live in `apps.json`.

## Runtime behavior differences

### Routing prefixes

- Apps: `/runtime/apps/{deployment_id}`
- Services: `/runtime/services/{deployment_id}`
- Tools: `/runtime/tools/{deployment_id}`

The prefix is selected from the deployment name (`app-`, `service-`, `tool-`) and the routing config service keys. The value is injected into `KAMIWAZA_APP_PATH` and template variables like `{app_access_path}`.

### Path router behavior

Traefik path routing treats services like tools, not like apps:

- Apps: prefix is forwarded, not stripped. Apps are expected to understand their base path.
- Services and tools: prefix is stripped before forwarding to the container. Services should serve at `/` and use `X-Forwarded-Prefix` only if they need to construct links.

### Health checks

- Apps get an HTTP probe after deployment.
- Services and tools skip the HTTP probe. This is intentional for non-HTTP or gRPC utilities.

### gRPC / TCP routing for services

- Service deployments that expose container port `19530` are treated as gRPC services (Milvus style).
- For these, Traefik maps a TCP route on the load balancer port and skips the HTTP path router.
- If you need gRPC, expose port 19530 in your compose file.

### Logs

- Services set `engine_type=service_garden` for container logs.
- `service_garden` is not treated as an extension log type, so logs land under `containers/service_garden/` rather than `extensions/app_garden/`.

## App vs Service vs Tool (quick comparison)

| Type | Purpose | template_type | Required prefix | Catalog | UI surface | Path prefix | HTTP probe | Path router behavior |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| App | User-facing UI or API | `app` (default) | none | `apps.json` | App Garden / Apps tab | `/runtime/apps` | yes | prefix forwarded (no strip) |
| Service | Backend utility / infra | `service` | `service-` | `apps.json` | App Garden / Services tab | `/runtime/services` | no | prefix stripped |
| Tool | Tool servers (MCP etc) | `tool` | `tool-` or `mcp-` | `tools.json` | Tool Shed | `/runtime/tools` | no | prefix stripped |

## How to build a service template

### 1) Name and type

- Template name MUST start with `service-`.
- Set `template_type` to `service` in the template payload or JSON.
- If you omit `template_type`, the `service-` prefix is still required for correct routing.

### 2) Compose file basics

- Services are deployed with Docker Compose the same way as apps.
- Expose at least one port (via `ports` or `expose`) so the deployment can map a primary port.
- If the service is gRPC (Milvus), expose port `19530` to trigger TCP routing.

### 3) Template variables and env

- Use `{app_access_path}` or `{app_path_url}` for the service runtime path.
- There is no `{service_access_path}` variable.
- `KAMIWAZA_APP_PATH` is set for services and contains `/runtime/services/{deployment_id}`.

### 4) Model discovery (if applicable)

- Services that do NOT need a model should set `preferred_model_type: null` to skip model discovery.
- If you want a model bound, set `preferred_model_type` (for example `any`, `fast`, `large`) and optionally `preferred_model_name`.

### 5) Catalog location

- Add the template to `garden/v2/apps.json` (local or remote catalog).
- Do NOT put service templates in `tools.json`.

### 6) Deployment naming

- Deployments must be named with `service-` prefix. If you accept a user-provided name, prefix it yourself.
- Context Service does this automatically for VectorDB and ontology services.

## Example service entry (apps.json)

```json
{
  "name": "service-kamiwaza-milvus",
  "template_type": "service",
  "version": "1.0.0",
  "compose_yml": "version: '3.8'\nservices:\n  milvus:\n    image: milvusdb/milvus:v2.3.3\n    ports:\n      - \"19530\"\n",
  "env_defaults": {
    "LOG_LEVEL": "info"
  }
}
```

## Validation checklist

- `GET /apps/app_templates?template_type=service` returns the template.
- `POST /apps/deploy` creates a deployment named `service-...`.
- `GET /apps/deployments?template_type=service` returns the deployment.
- Access path is `/runtime/services/{deployment_id}` when path routing is enabled.
- For gRPC services, the TCP port is mapped and HTTP path routing is skipped.

## Common gotchas

- Missing `service-` prefix on the deployment name causes the service to be treated as an app (wrong routing and health probes).
- Putting a service template in `tools.json` makes it a tool, not a service.
- Expecting a `service_access_path` template var will fail; use `app_access_path`.

## References (spec and code)

- Spec: `openspec/changes/add-context-service-phase0/specs/app-garden-services/spec.md`
- Spec: `openspec/changes/add-context-service-phase0/specs/context-service/spec.md`
- Design: `openspec/changes/add-context-service-phase0/design.md`
- Template typing: `kamiwaza/serving/schemas/templates.py`
- App Garden routing: `kamiwaza/serving/garden/apps/apps.py`
- Traefik routing: `kamiwaza/serving/traefik.py`
- Context service usage: `kamiwaza/services/context/services.py`
- UI tabs: `frontend/src/components/apps/AppGarden.js`
