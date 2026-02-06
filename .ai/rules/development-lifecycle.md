# Development Lifecycle - Kamiwaza Extensions

## Local Development Workflow

### 1. Create Extension
```bash
make new TYPE={app|tool} NAME={name}
```

### 2. Implement Features
- Edit source files
- Follow architecture.md patterns
- Use python-standards.md or relevant language standards

### 3. Test Locally
```bash
cd {extension-path}
docker-compose up --build
curl http://localhost:8000/health
```

### 4. Iterate
- Make changes
- Test incrementally
- Commit frequently (every 15-30 min)

## CI/Release Pipeline

### Automated Full Pipeline
```bash
# Run complete CI pipeline for all extensions
make ci-pipeline
```

This automated command runs:
1. `make build-all` - Build all extension Docker images
2. `make test-all` - Run all extension tests
3. `make sync-compose` - Sync all App Garden compose files
4. `make validate` - Validate all metadata and configs
5. `make build-registry` - Build extension registry
6. `make package-registry` - Create distribution tarball

**Output:** Creates `dist/kamiwaza-registry-YYYYMMDD-HHMMSS.tar.gz`

**Use when:** Running full CI before merging PRs or releasing extensions

### Individual Extension Pipeline
```bash
# 1. Build Docker images
make build TYPE={type} NAME={name}

# 2. Run tests
make test TYPE={type} NAME={name}

# 3. Sync App Garden compose files
make sync-compose

# 4. Validate metadata and configs
make validate

# 5. Build extension registry
make build-registry

# 6. Push images (when ready to release)
make push TYPE={type} NAME={name}
```

### When to Run Each Command

**make build**
- WHEN: After code changes, before testing
- BUILDS: Docker images with proper tags
- OUTPUT: kamiwazaai/{name}:{version}-dev (local builds always use -dev suffix)
- STAGE: Local builds always create dev stage images

**make test**
- WHEN: After successful build
- RUNS: Extension test suite
- REQUIRES: Docker images built, ports available

**make sync-compose**
- WHEN: After docker-compose.yml changes OR version updates
- GENERATES: docker-compose.appgarden.yml (App Garden compatible)
- REMOVES: build contexts, fixes ports/volumes
- UPDATES: Image tags from kamiwaza.json version (single source of truth)
- ADDS: Image fields for services with only build contexts
- PATTERN: kamiwazaai/{extension-name}-{service-name}:{version}

**make validate**
- WHEN: Before committing, in CI
- CHECKS: kamiwaza.json, docker files, naming conventions
- VALIDATES: App Garden compatibility, preview_image paths, kamiwaza_version constraints

**make build-registry**
- WHEN: Before releasing, after all extensions validated
- GENERATES: build/registry.json
- AGGREGATES: All extension metadata

**make push**
- WHEN: Ready to publish extension
- DEFAULT: Verifies images exist locally, then pushes (no build)
- BUILD_FLAG: Use `--build` flag to build before pushing
- PUSHES: Docker images to registry with stage-appropriate tags
- REQUIRES: Images must exist locally (run `make build` first, or use `--build`)
- STAGE: Set STAGE=dev|stage|prod for appropriate tagging

## Version Management

### Single Source of Truth
VERSION_SOURCE: kamiwaza.json is the single source of truth for extension versions
AUTO_SYNC: make sync-compose automatically updates image tags from kamiwaza.json
FORMAT: X.Y.Z in kamiwaza.json → X.Y.Z in Docker image tags (no 'v' prefix)

### Stage-Based Tagging
Docker image tags vary by deployment stage:

| Stage | Tag Format | Example | Use Case |
|-------|------------|---------|----------|
| dev | {version}-dev | 1.0.0-dev | Local development, CI builds |
| stage | {version}-stage | 1.0.0-stage | Staging/QA environments |
| prod | {version} | 1.0.0 | Production deployments |

**Important:** The `latest` tag is only created for local builds (developer convenience). It is never pushed to registries. Production should always reference specific versions.

### Version Update Workflow
1. Update version in kamiwaza.json
2. Run `make sync-compose` (or `make build`, which includes sync-compose)
3. docker-compose.appgarden.yml automatically updates with new version tags
4. Build and push with new version

### Image Naming Convention
PATTERN: kamiwazaai/{extension-name}-{service-name}:{version}[-stage]
EXAMPLES:
- kaizen-backend:1.0.1-dev (local dev)
- kaizen-frontend:1.0.1-stage (staging)
- micro-ats-backend:1.0.0 (production)
- playwright-mcp:1.0.0

### Auto-Generation
- Services with only `build` fields get `image` fields auto-generated
- Image name constructed from extension name and service name
- Version tag appended from kamiwaza.json
- External images (postgres, redis) preserved unchanged

### Version Consistency
- build-extension.sh reads version from kamiwaza.json for tagging
- sync-compose.py reads version from kamiwaza.json for compose files
- Both use "{version}" format for Docker tags (no 'v' prefix)
- No manual version management needed

## Publishing Workflow

### Publishing Images
The `publish-images.sh` script (via `make push`) handles Docker image publishing:

```bash
# Verify images exist and push (default behavior)
make push TYPE=app NAME=my-app

# Build images before pushing
make push TYPE=app NAME=my-app BUILD=1

# Push for staging environment
STAGE=stage make push TYPE=app NAME=my-app

# Push for production
STAGE=prod make push TYPE=app NAME=my-app

# Dry run to see what would be pushed
make push TYPE=app NAME=my-app DRY_RUN=1
```

### Publishing Stages
| Stage | Command | Tag Created | Use Case |
|-------|---------|-------------|----------|
| dev | `make push` or `STAGE=dev make push` | 1.0.0-dev | Development testing |
| stage | `STAGE=stage make push` | 1.0.0-stage | QA/staging |
| prod | `STAGE=prod make push` | 1.0.0 | Production release |

### Publishing Registry

The extension registry uses a **version-aware upsert** mechanism that prevents accidental overwrites and version conflicts.

#### Safe Upsert Workflow

```bash
# 1. Dry-run to see what would happen (recommended before publishing)
make publish-registry DRY_RUN=1

# 2. Publish with version-aware upsert
make publish-registry                    # Safe upsert to dev (default)
STAGE=stage make publish-registry        # Safe upsert to staging
STAGE=prod make publish-registry         # Safe upsert to production
```

**Note:** `publish-registry` automatically rebuilds the registry for the target stage
to ensure image tags match (e.g., prod registry uses `1.0.0` tags, not `1.0.0-dev`).

**Prerequisite:** set per-stage AWS profiles in `.env`:
```
AWS_PROFILE_DEV=kamiwaza-registry-dev
AWS_PROFILE_STAGE=kamiwaza-registry-stage
AWS_PROFILE_PROD=kamiwaza-registry-prod
```

#### Upsert Workflow Steps

The `make publish-registry` command executes:

1. **Rebuild** registry for target stage (ensures correct image tags)
2. **Validate** local registry (kamiwaza.json format, version constraints)
3. **Acquire lock** on S3 bucket (prevents concurrent writes)
4. **Backup** current remote state (timestamped local copy)
5. **Download** current registry
6. **Merge** using version-aware logic:
   - **INSERT**: New extension or disjoint kamiwaza_version range
   - **REPLACE**: Newer version with same/superset kamiwaza_version
   - **FAIL**: Same version (immutable), downgrade, or narrower support
7. **Push** merged registry to S3
8. **Verify** upload integrity
9. **Release lock** (cleanup on success or failure) and restore backup if needed

#### Version-Aware Merge Logic

| Scenario | Action | Reason |
|----------|--------|--------|
| New extension | INSERT | First publish |
| Newer version, same kamiwaza_version | REPLACE | Version upgrade |
| Same version, same kamiwaza_version | FAIL | Immutable versions |
| Older version | FAIL | Cannot downgrade |
| Disjoint kamiwaza_version range | INSERT | Coexist for different Kamiwaza versions |
| Superset kamiwaza_version | REPLACE | Expands support |
| Subset kamiwaza_version | FAIL | Would narrow support |
| Partial overlap | FAIL | Ambiguous, requires manual resolution |

#### Registry Publishing Commands

| Command | Description |
|---------|-------------|
| `make publish-registry` | Safe upsert with locking and backup |
| `make publish-registry DRY_RUN=1` | Show merge simulation without changes |
| `make publish-registry FORCE=1` | Force push (bypass version checks, emergency use) |
| `make remove-publish-lock` | Remove registry lock for a stage |
| `make download-registry` | Download current remote registry for inspection |
| `make publish-registry-direct` | Legacy direct S3 sync (no version checks) |

#### Error Handling

- **Lock exists**: Another publish is in progress or a previous publish failed. Investigate and remove the lock: `make remove-publish-lock STAGE={stage}` or `aws s3 rm s3://{bucket}/garden/{garden_dir}/registry.lock`
- **Merge conflict**: Version or constraint conflict detected. Use `DRY_RUN=1` to see details, then either bump version or use `FORCE=1` if appropriate.
- **Backup location**: `build/registry-backups/{stage}/{timestamp}/`

## Development Patterns

### Feature Development
```bash
# Start feature
make new TYPE=app NAME=my-feature

# Develop iteratively
cd apps/my-feature
docker-compose up --build
# ... make changes ...
docker-compose restart backend

# Run full pipeline before PR
make build TYPE=app NAME=my-feature
make test TYPE=app NAME=my-feature
make sync-compose
make validate
```

### Bug Fix
```bash
# Fix code
cd {extension-path}

# Test locally
docker-compose up --build

# Run tests
make test TYPE={type} NAME={name}

# Validate
make validate
```

### Pre-Commit Checklist
- [ ] make build TYPE={type} NAME={name}
- [ ] make test TYPE={type} NAME={name}
- [ ] make sync-compose
- [ ] make validate
- [ ] Git commit with clear message

### Pre-Release Checklist
- [ ] Version bumped in kamiwaza.json
- [ ] make sync-compose (updates appgarden image tags)
- [ ] All extensions pass make validate
- [ ] make build TYPE={type} NAME={name} (creates {version}-dev images)
- [ ] STAGE=prod make publish-registry DRY_RUN=1 (verify no merge conflicts, auto-rebuilds registry)
- [ ] STAGE=prod make push TYPE={type} NAME={name} (pushes production tags)
- [ ] STAGE=prod make publish-registry (publishes registry with upsert, auto-rebuilds for prod)

## Shortcuts

### Validate All Extensions
```bash
make validate
```

### Build All Extensions
```bash
make build-all
```

### Test Specific Extension
```bash
make test TYPE=app NAME=ai-chatbot-app
```

### Clean Build
```bash
docker system prune -f
make build TYPE={type} NAME={name}
```

## Troubleshooting

### Build Fails
1. Check Dockerfile syntax
2. Verify base image exists
3. Check for missing dependencies
4. Review build logs for errors

### Tests Fail
1. Check ports available (lsof -ti:{port})
2. Verify services started (docker-compose ps)
3. Check test logs
4. Run single test for isolation

### Validation Fails
1. Check kamiwaza.json format
2. Verify docker-compose.appgarden.yml synced
3. Fix reported issues
4. Re-run make sync-compose if needed

### Registry Build Fails
1. Ensure all extensions have kamiwaza.json
2. Check for JSON syntax errors
3. Verify all extensions validated
4. Check build/ directory permissions

### Registry Publish Fails

**Lock already exists:**
```bash
# Check who holds the lock
aws s3 cp s3://{bucket}/garden/{garden_dir}/registry.lock - | jq

# After investigation, remove lock manually
aws s3 rm s3://{bucket}/garden/{garden_dir}/registry.lock

# Or use the helper target
make remove-publish-lock STAGE={stage}
```

**Version conflict (same version exists):**
1. Run `make publish-registry DRY_RUN=1` to see details
2. Bump version in kamiwaza.json
3. Run `make sync-compose && make build-registry`
4. Try publishing again

**Constraint conflict (narrowing kamiwaza_version):**
1. Cannot narrow support - would break existing users
2. Either keep broader constraint or use `FORCE=1` (emergency only)

**Backup restoration needed:**
```bash
# Backups are in build/registry-backups/{stage}/{timestamp}/
# To restore manually:
aws s3 sync build/registry-backups/dev/YYYYMMDD-HHMMSS/ s3://{bucket}/garden/v2/ --delete
```
