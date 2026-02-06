# Template Management

This document describes how to manage Kamiwaza templates using the integrated Makefile commands.

## Prerequisites

1. **Kamiwaza must be running** on localhost (default) or configured via environment variable
2. **Authentication** is handled via environment variables or defaults:
   - `KAMIWAZA_API_URI` - API endpoint (default: http://localhost:7777/api)
   - `KAMIWAZA_USERNAME` - Username (default: admin)
   - `KAMIWAZA_PASSWORD` - Password (default: kamiwaza)

## Available Commands

### List Templates and Deployments

```bash
# List all available templates (apps, services, and tools)
make templates-list

# List only app templates
make templates-list-apps

# List only service templates
make templates-list-services

# List only tool templates
make templates-list-tools

# List current deployments
make templates-list-deployments
```

### Import Templates from Garden

```bash
# Import all templates from Kamiwaza garden
make templates-import

# Import only app templates
make templates-import-apps

# Import only tool templates
make templates-import-tools

# Sync all templates (alias for import all)
make templates-sync
```

## Output Formats

The template management script supports two output formats:

### Table Format (Default)
```bash
make templates-list
```

### JSON Format
For programmatic access, you can get JSON output by calling the script directly:
```bash
python3 scripts/manage-templates.py --format json list all
```

## Environment Variables

Configure the connection to Kamiwaza:
```bash
# Use a different Kamiwaza instance
export KAMIWAZA_API_URI=http://your-kamiwaza:7777/api
export KAMIWAZA_USERNAME=your-username
export KAMIWAZA_PASSWORD=your-password

# Then run commands as normal
make templates-list
```

## Example Workflow

1. **Check available templates**:
   ```bash
   make templates-list
   ```

2. **Import missing templates**:
   ```bash
   make templates-sync
   ```

3. **Verify import**:
   ```bash
   make templates-list
   ```

4. **Check deployments**:
   ```bash
   make templates-list-deployments
   ```

## Troubleshooting

### Authentication Errors
If you get authentication errors, ensure:
1. Kamiwaza is running
2. Credentials are correct
3. Try with explicit credentials:
   ```bash
   python3 scripts/manage-templates.py --username admin --password kamiwaza list all
   ```

### Connection Errors
If you can't connect:
1. Verify Kamiwaza is running: `curl http://localhost:7777/api/health`
2. Check the API URL is correct
3. Ensure no firewall is blocking the connection

### Import Failures
If template imports fail:
1. Check you have appropriate permissions
2. Verify the garden registry is accessible
3. Check for any specific error messages in the output
