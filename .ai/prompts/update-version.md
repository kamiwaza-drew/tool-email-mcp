# Update Extension Version

VARIABLES:
- TYPE: {app|tool}
- NAME: {extension-name}
- VERSION: {new-version} (X.Y.Z format)

## Workflow

### 1. Update Version in kamiwaza.json
```bash
cd {TYPE}s/{NAME}
# Edit kamiwaza.json: "version": "{VERSION}"
```

### 2. Sync Compose Files
```bash
make sync-compose
```

### 3. Verify Changes
```bash
# Check that docker-compose.appgarden.yml has correct version
grep "image:" {TYPE}s/{NAME}/docker-compose.appgarden.yml
# Should show: kamiwazaai/{NAME}-{service}:{VERSION}
```

### 4. Build and Test
```bash
make build TYPE={TYPE} NAME={NAME}
make test TYPE={TYPE} NAME={NAME}
```

### 5. Commit Changes
```bash
git add {TYPE}s/{NAME}/kamiwaza.json {TYPE}s/{NAME}/docker-compose.appgarden.yml
git commit -m "Bump {NAME} to {VERSION}"
```

## Version Consistency

SINGLE_SOURCE: kamiwaza.json only
AUTO_UPDATE: sync-compose handles docker-compose.appgarden.yml
AUTO_TAG: build script handles Docker image tags

## Example

```bash
# Update kaizen to 1.0.2
cd apps/kaizen
# Edit kamiwaza.json: "version": "1.0.2"

make sync-compose

# Verify
grep "image:" apps/kaizen/docker-compose.appgarden.yml
# Output:
# image: postgres:16
# image: kamiwazaai/kaizen-backend:1.0.2
# image: kamiwazaai/kaizen-frontend:1.0.2

make build TYPE=app NAME=kaizen
make test TYPE=app NAME=kaizen

git add apps/kaizen/kamiwaza.json apps/kaizen/docker-compose.appgarden.yml
git commit -m "Bump kaizen to 1.0.2"
```

## Notes

- Only edit version in kamiwaza.json, never in compose files
- sync-compose auto-updates image tags
- External images (postgres, redis) are never modified
- Build script reads version from kamiwaza.json for Docker tags
