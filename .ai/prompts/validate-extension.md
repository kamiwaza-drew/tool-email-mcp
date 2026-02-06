# Validate Extension

VARIABLES:
- TYPE: {type}
- NAME: {extension-name}
- PATH: {extension-path}

VALIDATE_ALL:
```bash
make validate
```

VALIDATE_ONE:
```bash
make validate-ext TYPE={TYPE} NAME={NAME}
```

CHECKLIST:
[ ] kamiwaza.json exists, valid JSON
[ ] name, version, source_type, risk_tier present
[ ] preview_image (if present): relative path, file exists, valid image type
[ ] kamiwaza_version (if present): valid semver constraint (e.g., ">=0.8.0")
[ ] Dockerfile exists
[ ] docker-compose.yml exists
[ ] docker-compose.appgarden.yml synced
[ ] Image tags match kamiwaza.json version ({version}, no 'v' prefix)
[ ] Services with build have corresponding image in appgarden
[ ] No host port mappings
[ ] No bind mounts
[ ] Resource limits defined
[ ] Extra hosts configured
[ ] README.md exists

TEST_LOCAL:
```bash
cd {PATH}
docker-compose up --build
curl http://localhost:8000/health  # apps only
```

FIX_APPGARDEN:
```bash
make sync-compose
```

REBUILD_REGISTRY:
```bash
make build-registry
```
