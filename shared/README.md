# Shared Libraries

This directory contains reusable utilities for Kamiwaza App Garden extensions.

## Packages

### Python (`python/kamiwaza_auth/`)

Authentication utilities for FastAPI backends:
- Identity extraction from forward auth headers
- Session management endpoints (`/session`, `/auth/login-url`, `/auth/logout`)
- JWT utilities for token parsing and session expiry
- KamiwazaClient for API calls with auth forwarding
- FastAPI dependencies for authentication

[Read more](./python/kamiwaza_auth/README.md)

### TypeScript (`typescript/kamiwaza-auth/`)

Authentication utilities for Next.js frontends:
- Session context and `useSession` hook
- Auth middleware for protected routes
- API proxy route handlers
- Base path handling for App Garden
- AuthGuard component for protected content

[Read more](./typescript/kamiwaza-auth/README.md)

### TypeScript (`typescript/kamiwaza-client/`)

TypeScript client for Kamiwaza API:
- Type-safe API client for Kamiwaza services
- Model management and inference
- App and tool deployment management

[Read more](./typescript/kamiwaza-client/README.md)

## Building Packages

Use `make package-libs` to build distributable packages:

```bash
# Build all packages
make package-libs

# Build only Python wheel
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
| TypeScript auth | `shared/typescript/kamiwaza-auth/kamiwaza-auth-{version}.tgz` |
| TypeScript client | `shared/typescript/kamiwaza-client/kamiwaza-client-{version}.tgz` |

## Installing in Your Extension

### Python (FastAPI Backends)

1. Copy the wheel to your app's backend directory:
   ```bash
   cp shared/python/dist/kamiwaza_auth-*.whl apps/my-app/backend/
   ```

2. Add to `requirements.txt` (at the top):
   ```txt
   # Kamiwaza auth shared library (bundled wheel)
   ./kamiwaza_auth-0.1.0-py3-none-any.whl
   ```

### TypeScript (Next.js Frontends)

1. Copy the package to your app's frontend directory:
   ```bash
   cp shared/typescript/kamiwaza-auth/kamiwaza-auth-*.tgz apps/my-app/frontend/
   ```

2. Add to `package.json` dependencies:
   ```json
   "@kamiwaza/auth": "file:./kamiwaza-auth-0.2.0.tgz"
   ```

3. Run `npm install` to link the package.

## Documentation

See the [Extension Developer Guide](../docs/extension-developer-guide.md#shared-libraries) for complete integration documentation including usage examples.
