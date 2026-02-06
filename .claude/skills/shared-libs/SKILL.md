---
name: shared-libs
description: Package and install Kamiwaza shared libraries (Python wheel and TypeScript packages) to apps and tools in this repository. Use when the user wants to build shared libs, install libs, update dependencies, or sync shared code to extensions.
---

# Shared Libraries Management

This skill helps package and install Kamiwaza shared libraries to apps and tools.

## Available Shared Libraries

**Python:**
- `kamiwaza_auth` - Authentication utilities for FastAPI backends

**TypeScript:**
- `@kamiwaza/auth` - Authentication components for Next.js frontends
- `@kamiwaza/client` - Kamiwaza SDK client for TypeScript

## Workflow

### Step 1: Package the Libraries

Build all shared library packages:
```bash
make package-libs
```

To rebuild from scratch:
```bash
make package-libs CLEAN=1
```

Build only specific types:
```bash
make package-libs PYTHON_ONLY=1   # Only Python wheel
make package-libs TS_ONLY=1       # Only TypeScript packages
```

### Step 2: Discover Extensions

Find apps and tools in the repository:
```bash
# List all extensions
make list

# Or manually check
ls -d apps/*/ tools/*/ 2>/dev/null
```

### Step 3: Determine Library Needs

For each extension, check what libraries it needs:

**Python backends** - Look for:
- `requirements.txt` or `pyproject.toml` in backend directory
- Imports of `kamiwaza_auth` in Python files

**TypeScript frontends** - Look for:
- `package.json` in frontend directory
- Imports of `@kamiwaza/auth` or `@kamiwaza/client`

### Step 4: Install Libraries

Install to a specific extension:
```bash
# Install all libs to an app (frontend + backend)
make install-libs TYPE=app NAME=my-app

# Install all libs to a tool
make install-libs TYPE=tool NAME=my-tool

# Install only Python
make install-libs TYPE=app NAME=my-app PYTHON_ONLY=1

# Install only TypeScript
make install-libs TYPE=app NAME=my-app TS_ONLY=1

# Install specific packages
make install-libs TYPE=app NAME=my-app LIBS=auth
make install-libs TYPE=app NAME=my-app LIBS=auth,client
```

### Step 5: Update Extension Dependencies

After installing, update the extension's dependency files:

**Python (requirements.txt):**
Add at the top of the file:
```
# Kamiwaza shared library (bundled wheel)
./kamiwaza_auth-X.Y.Z-py3-none-any.whl
```

**TypeScript (package.json):**
Add to dependencies:
```json
{
  "dependencies": {
    "@kamiwaza/auth": "file:./kamiwaza-auth-X.Y.Z.tgz",
    "@kamiwaza/client": "file:./kamiwaza-client-X.Y.Z.tgz"
  }
}
```

Then run:
```bash
cd apps/my-app/frontend && npm install
```

## Batch Installation

To install libs to all extensions that need them:

1. List extensions:
   ```bash
   make list
   ```

2. For each app with a frontend, install TypeScript libs:
   ```bash
   make install-libs TYPE=app NAME=app1 TS_ONLY=1
   make install-libs TYPE=app NAME=app2 TS_ONLY=1
   ```

3. For each app/tool with a backend, install Python libs:
   ```bash
   make install-libs TYPE=app NAME=app1 PYTHON_ONLY=1
   make install-libs TYPE=tool NAME=tool1 PYTHON_ONLY=1
   ```

## Default Install Paths

| Type | Python | TypeScript |
|------|--------|------------|
| app | `apps/{name}/backend/` | `apps/{name}/frontend/` |
| tool | `tools/{name}/` | `tools/{name}/` |

Override with custom paths:
```bash
make install-libs TYPE=app NAME=my-app PY_PATH=src/ TS_PATH=web/
```

## Verification

After installation, verify the packages are in place:
```bash
# Check Python wheel
ls apps/my-app/backend/*.whl

# Check TypeScript packages
ls apps/my-app/frontend/*.tgz
```

## Troubleshooting

### "Install path does not exist"
The target directory must exist. Check that your extension has the expected structure:
- Apps: `apps/{name}/backend/` and `apps/{name}/frontend/`
- Tools: `tools/{name}/`

### "No wheel/tgz files found"
Run `make package-libs` first to build the packages.

### Import errors after installation
Ensure you've updated the dependency files (requirements.txt or package.json) and reinstalled dependencies.
