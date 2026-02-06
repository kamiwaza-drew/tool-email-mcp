# Environment Setup

## Configuration

The Kamiwaza Extensions project uses environment variables for configuration. You can set these in several ways:

### 1. Using .env file (Recommended)

Copy the example file and customize:
```bash
cp .env.example .env
```

Edit `.env` with your settings:
```bash
# Kamiwaza API Configuration
KAMIWAZA_API_URL=https://my-kamiwaza.example.com/api
KAMIWAZA_USERNAME=myusername
KAMIWAZA_PASSWORD=mypassword
```

### 2. Exporting Environment Variables

```bash
export KAMIWAZA_API_URL=https://my-kamiwaza.example.com/api
export KAMIWAZA_USERNAME=myusername
export KAMIWAZA_PASSWORD=mypassword
```

### 3. Inline with Make Commands

```bash
KAMIWAZA_API_URL=https://my-kamiwaza.example.com/api make templates-list
```

## Available Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `KAMIWAZA_API_URL` | `https://localhost/api` | Kamiwaza API endpoint |
| `KAMIWAZA_USERNAME` | `admin` | Username for authentication |
| `KAMIWAZA_PASSWORD` | `kamiwaza` | Password for authentication |
| `DOCKER_REGISTRY` | (none) | Docker registry for publishing images |
| `DOCKER_REGISTRY_USERNAME` | (none) | Registry username |
| `DOCKER_REGISTRY_PASSWORD` | (none) | Registry password |
| `OPENAI_API_KEY` | (none) | OpenAI API key for extensions that use it |
| `KAMIWAZA_REGISTRY_ENDPOINT` | (none) | Custom S3/R2 endpoint for registry publishing |
| `KAMIWAZA_REGISTRY_REGION` | (none) | S3 region (use `auto` for R2) |
| `KAMIWAZA_REGISTRY_BUCKET_DEV` | (none) | Registry bucket for dev stage |
| `KAMIWAZA_REGISTRY_BUCKET_STAGE` | (none) | Registry bucket for stage |
| `KAMIWAZA_REGISTRY_BUCKET_PROD` | (none) | Registry bucket for prod |
| `AWS_PROFILE_DEV` | (none) | AWS CLI profile for dev stage registry publish |
| `AWS_PROFILE_STAGE` | (none) | AWS CLI profile for stage registry publish |
| `AWS_PROFILE_PROD` | (none) | AWS CLI profile for prod registry publish |

## Registry Publishing Profiles

Registry publishing requires per-stage AWS profiles. Set these in `.env`:

```bash
AWS_PROFILE_DEV=kamiwaza-registry-dev
AWS_PROFILE_STAGE=kamiwaza-registry-stage
AWS_PROFILE_PROD=kamiwaza-registry-prod
```

Then publish with:

```bash
make publish STAGE=stage
```

## Template Management

The template management commands require a running Kamiwaza deployment. To use a different Kamiwaza instance:

1. Set environment variables as described above
2. Run template commands:
   ```bash
   make templates-list     # List available templates
   make templates-import   # Import all templates
   make templates-sync     # Sync templates with garden
   ```

The current Kamiwaza endpoint is shown in the help output:
```bash
make help | grep -A3 "Template Management"
```
