# Repository Guidelines

## Canonical Reference
- Treat `.ai/` as the source of truth. Start with `@.ai/README.md` for structure, then apply the specific standards in `@.ai/rules/architecture.md`, `python-standards.md`, `style.md`, and `testing.md` relevant to the task.
- When in doubt, quote the appropriate rule (e.g., `@.ai/rules/architecture.md#docker-rules`) in your notes before implementing.

## Project Structure & Module Organization
- Follow the layout defined in `@.ai/rules/architecture.md`: apps live in `apps/<extension>` with frontend/backend splits; services live in `services/<extension>`; tools stay in `tools/<extension>/src`.
- Required metadata (`Dockerfile`, `docker-compose.yml`, `kamiwaza.json`, `README.md`) stay at each extension root. Generated artifacts are confined to `build/`; docs synced via mkdocs belong in `docs/`.
- Mirror runtime modules inside `tests/` and keep shared helpers in `shared/`; add automation to `scripts/`.

## Build, Test, and Development Commands
- `make list` / `make list-apps|list-services|list-tools` – enumerate registered extensions to confirm naming matches `.ai` prompt templates.

**CI/Release Pipeline (run in order):**
1. `make build TYPE=app NAME=kaizen-app` – build the container image; pivot `TYPE`/`NAME` to match the target.
2. `make test TYPE=tool NAME=websearch-tool` – dispatches to `pytest`, `npm test`, or `go test ./...` automatically.
3. `make sync-compose` – sync all App Garden compose files from docker-compose.yml.
4. `make validate` – runs manifest linting plus compose drift checks mandated in `@.ai/rules/testing.md`.
5. `make build-registry` – regenerates registry files under `build/kamiwaza-extension-registry/garden/{v2|default}`.
6. `make push TYPE={type} NAME={name}` – push images to registry when ready to release.

See `@.ai/rules/development-lifecycle.md` for complete pipeline details.

## Coding Style & Naming Conventions
- Observe the limits from `@.ai/rules/style.md`: concise functions (<30 lines), kebab-case directories, snake_case Python modules, and image names `kamiwazaai/<extension-name>`.
- Python work adheres to Ruff (≤120 chars) + mypy with semantic imports; FastAPI patterns are in `@.ai/rules/python-standards.md`.
- JS/TS packages keep scripts in `package.json`, pin dependencies, and prefer `npm ci` in Dockerfiles.

## Testing Guidelines
- Align with `@.ai/rules/testing.md`: co-locate unit tests under each extension’s `tests/` tree, ensure `/health` coverage, and mock Kamiwaza LLM calls.
- Declare test-only dependencies in `requirements.txt` or `package.json`; add compose smoke tests for multi-service flows.
- Always run `make test TYPE=<type> NAME=<name>` and `make validate` before submitting.

## Commit & Pull Request Guidelines
- Use Conventional commits (`feat:`, `fix:`, `refactor:`) and avoid AI references per `@.ai/rules/style.md`.
- PRs document impact, reference tracking issues, include evidence for runtime/UI changes, and only request review after passing `make validate`, `make build`, and `make test`.

## Security & Configuration Tips
- Keep env defaults in `kamiwaza.json`, rely on `.env` overlays for secrets, and pin base images. Sync compose changes with `make sync-compose` to update all `docker-compose.appgarden.yml` files.
- For registry publishing, set per-stage AWS profiles in `.env` (`AWS_PROFILE_DEV/STAGE/PROD`) per `.env.example`.
- To push templates to a running Kamiwaza instance, use `make kamiwaza-push TYPE={app|service|tool} NAME=<name>`. If updating an existing template, pass `TEMPLATE_ID=<uuid>` to update in place instead of creating a duplicate.
- To publish to the public registry, use `make publish STAGE={dev|stage|prod}` (publishes both registry files and Docker images).

## Claude Code Skills

### Available Skills

#### kamiwaza-logs
Analyze Kamiwaza platform logs including core services, apps, tools, and containers.

**Use when:**
- Debugging deployment issues
- Investigating service errors
- Checking container health
- Analyzing app startup failures

**Invocation:** The skill reads logs from `$KAMIWAZA_ROOT/logs/` directory. Set `KAMIWAZA_ROOT` environment variable to point to the Kamiwaza installation.

#### update-docs
Update documentation based on branch changes. Reviews commits since branch creation and updates `docs/`, `.ai/`, `CLAUDE.md`, and `AGENTS.md` files with production-grade quality.

**Use when:**
- Completing a feature branch with significant changes
- Preparing for PR review
- Major refactoring affecting documentation

**Quality standards:**
- Production-grade documentation
- Thorough verification of all examples
- Consistent terminology across documents
- Can delegate to sub-agents for large updates

#### shared-libs
Package and install Kamiwaza shared libraries (Python wheel and TypeScript packages) to apps, services, and tools.

**Use when:**
- Building shared Python/TypeScript packages
- Installing shared libs into extensions
- Updating dependencies across extensions

#### update-from-template
Update this repository from the upstream Kamiwaza extensions template using copier.

**Use when:**
- Syncing infrastructure changes from template
- Pulling latest build scripts and configs
- Updating CI pipeline configurations
