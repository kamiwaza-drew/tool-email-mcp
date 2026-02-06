# Contributing to Kamiwaza Extensions

<!-- Template version: 0.0.16 -->

Thank you for your interest in contributing to the Kamiwaza Extensions repository! This guide focuses on the contribution workflow and process. For comprehensive technical details, see [DEVELOPERS.md](DEVELOPERS.md).

## Table of Contents
- [Overview](#overview)
- [Types of Contributions](#types-of-contributions)
- [Getting Started](#getting-started)
- [Contribution Workflow](#contribution-workflow)
- [Pull Request Process](#pull-request-process)
- [Publishing Extensions](#publishing-extensions)
- [Getting Help](#getting-help)

## Overview

This repository hosts extensions for the Kamiwaza platform:
- **Apps**: Full applications with user interfaces
- **Tools**: MCP (Model Context Protocol) servers that provide AI capabilities

All extensions must be containerized and follow our metadata and deployment standards. See [DEVELOPERS.md](DEVELOPERS.md) for technical implementation details.

## Types of Contributions

### New Extensions
- Create new apps that integrate with Kamiwaza
- Develop MCP tools that provide AI capabilities
- Port existing applications to work with Kamiwaza

### Improvements to Existing Extensions
- Bug fixes
- Performance improvements
- New features
- Documentation updates

### Repository Infrastructure
- Improvements to automation scripts
- CI/CD enhancements
- Documentation improvements
- Testing framework updates

## Getting Started

### Prerequisites
- Git
- Docker and Docker Compose
- Python 3.8+ (for automation scripts)
- Language-specific requirements for your extension

For recommended developer tools (ast-grep, ripgrep, fd, etc.), see [DEVELOPERS.md#developer-tools-setup](DEVELOPERS.md#developer-tools-setup).

### Setting Up Your Development Environment

1. Fork this repository on GitHub

2. Clone your fork locally:
   ```bash
   git clone git@github.com:YOUR_USERNAME/kamiwaza-extensions.git
   cd kamiwaza-extensions
   ```

3. Add the upstream remote:
   ```bash
   git remote add upstream git@github.com:jxstanford/kamiwaza-extensions.git
   ```

4. Create a branch for your work:
   ```bash
   git checkout -b feature/my-new-extension
   ```

## Contribution Workflow

### 1. Plan Your Extension

Before starting, consider:
- Does a similar extension already exist?
- Is this better as an app or a tool?
- What are the resource requirements?
- What environment variables are needed?

### 2. Create Your Extension

Use the Makefile to scaffold a new extension:
```bash
# For apps
make new TYPE=app NAME=my-awesome-app

# For tools
make new TYPE=tool NAME=my-useful-tool
```

For external extensions (source maintained elsewhere), see [DEVELOPERS.md#external-extensions-guide](DEVELOPERS.md#external-extensions-guide).

### 3. Implement Your Extension

Follow the technical requirements detailed in [DEVELOPERS.md](DEVELOPERS.md):

**Required Files:**
- `kamiwaza.json` - See [Metadata Requirements](DEVELOPERS.md#metadata-requirements)
- `Dockerfile` - See [Docker Requirements](DEVELOPERS.md#docker-requirements)
- `docker-compose.yml` - For local development
- `README.md` - Documentation with configuration details

**Implementation Standards:**
- Follow [Extension Structure](DEVELOPERS.md#extension-structure) patterns
- Adhere to [Docker Requirements](DEVELOPERS.md#docker-requirements) (ports, volumes, resource limits)
- Include tests when feasible - See [Testing Extensions](DEVELOPERS.md#testing-extensions)

**Code Standards:**
- Follow existing patterns in the codebase
- Keep extensions focused and single-purpose
- Use meaningful names and clear documentation
- Include error handling and logging
- Use official base images, run as non-root user
- Provide health check endpoints

### 4. Validate Your Work

Before submitting, ensure all validations pass:
```bash
# Run all validations
make validate

# Or run individual checks
make validate-metadata      # Check kamiwaza.json files
make sync-compose          # Generate App Garden compose files
make validate-compose      # Verify compose file compatibility
```

For troubleshooting validation errors, see [DEVELOPERS.md#troubleshooting](DEVELOPERS.md#troubleshooting).

### 5. Test Locally

Test your extension thoroughly:
```bash
# Build Docker images
make build TYPE=app NAME=my-awesome-app

# Run tests if you have them
make test TYPE=app NAME=my-awesome-app

# Test with docker-compose
cd apps/my-awesome-app
docker-compose up

# Test health endpoint (apps only)
curl http://localhost:8000/health
```

### 6. Test with Kamiwaza

Before submitting your PR, you can test in real environments:

```bash
# Option 1: Push to a running Kamiwaza instance (apps, services, and tools)
make kamiwaza-push TYPE=app NAME=my-awesome-app

# Option 2: Publish to dev registry (pre-PR testing)
make publish STAGE=dev

# Dry-run to see what would be published
make publish-dry-run STAGE=dev
```

**Note:** `kamiwaza-push` requires a running Kamiwaza instance and pushes the template directly to it. `make publish` publishes to the public dev registry.

## Pull Request Process

### Before Submitting

1. **Update Documentation:**
   - Ensure your extension's README.md is complete
   - Update any relevant documentation
   - Add your extension to any relevant lists

2. **Run All Checks:**
   ```bash
   make validate
   make build TYPE=your-type NAME=your-name
   make test TYPE=your-type NAME=your-name
   ```

3. **Build Registry** (for verification):
   ```bash
   make build-registry
   ```

## Publishing Extensions

Extensions can be published to different environments depending on the stage of development.

### Development Publishing (Contributors)

Contributors can publish to the **dev** stage for testing before or during PR review:

```bash
# Publish registry and multi-arch Docker images to dev
make publish STAGE=dev

# Or dry-run to see what would be published
make publish-dry-run STAGE=dev
```

This allows testing in a real environment and is safe for iterative development.

### Staging/Production Publishing (Maintainers Only)

After a PR is merged, maintainers publish to staging and production:

```bash
# Publish to staging for QA
make publish STAGE=stage

# Publish to production
make publish STAGE=prod
```

### What `make publish` Does

1. **Builds registry** - Aggregates all extension metadata into registry.json
2. **Publishes registry files** - Uploads to S3 bucket:
   - dev: `https://dev-info.kamiwaza.ai/garden/v2/`
   - stage: `https://stage-info.kamiwaza.ai/garden/v2/`
   - prod: `https://info.kamiwaza.ai/garden/v2/`
3. **Builds multi-arch images** - Creates Docker images for linux/amd64 and linux/arm64
4. **Pushes images** - Uploads to Docker registry with stage-appropriate tags:
   - dev: `version-dev` (e.g., `1.2.0-dev`)
   - stage: `version-stage` (e.g., `1.2.0-stage`)
   - prod: `version` (e.g., `1.2.0`)

### Publishing Options

```bash
# Publish only registry files (no Docker images)
make publish-registry STAGE=prod

# Publish only Docker images (no registry files)
make publish-images STAGE=prod

# Build single architecture only
make publish-images STAGE=prod PLATFORMS=linux/amd64

# Force publish specific extension to dev (development only)
make publish-registry STAGE=dev TYPE=app NAME=my-app FORCE=1

# See what would be published (dry run)
make publish-registry-dry-run STAGE=prod
make publish-images-dry-run STAGE=prod
```

### Requirements

- **AWS credentials** configured for the target environment
- **Docker Hub** credentials (for Docker image publishing)
- **Multi-arch build support** - Docker Buildx must be set up
- **Version constraints** - Registry uses version-aware upsert to prevent conflicts

**Note:** The `make publish` command handles the complete release workflow. Individual commands are provided for special cases or troubleshooting.

## Getting Help

If you need help:
1. Check existing extensions for examples
2. Review [DEVELOPERS.md](DEVELOPERS.md) for comprehensive technical details
3. Look for similar closed issues
4. Ask questions in your PR or issue

## Code of Conduct

Please note that this project is released with a Contributor Code of Conduct. By participating in this project you agree to abide by its terms.

## Recognition

Contributors will be recognized in:
- Extension metadata (author field)
- Repository contributors list
- Release notes when applicable

Thank you for contributing to Kamiwaza Extensions!
