---
name: kamiwaza-logs
description: Analyze Kamiwaza platform logs including core services, apps, tools, and containers. Use when the user asks about errors, debugging issues, checking service status, or investigating problems in Kamiwaza. Always looks for the most recent logs unless told otherwise.
---

# Kamiwaza Log Analyzer

This skill helps analyze logs from the Kamiwaza platform, including core services, deployed apps, tools, and Docker containers.

## Initial Setup

### Step 1: Locate KAMIWAZA_ROOT

Check for the Kamiwaza root directory:

```bash
# Check environment variable
echo $KAMIWAZA_ROOT

# Common locations if not set
ls -d ~/kamiwaza /opt/kamiwaza /var/kamiwaza 2>/dev/null
```

**If KAMIWAZA_ROOT is not found, ASK THE USER for the path.**

### Step 2: Clarify Log Type

Before diving into logs, clarify with the user what they're looking for:

| Log Type | Description | Location |
|----------|-------------|----------|
| **Core Platform** | Kamiwaza core services (API, scheduler, etc.) | `$KAMIWAZA_ROOT/logs/` |
| **App Logs** | Deployed application logs | Container logs + `$KAMIWAZA_ROOT/logs/apps/` |
| **Tool Logs** | MCP tool server logs | Container logs + `$KAMIWAZA_ROOT/logs/tools/` |
| **Model Logs** | Model serving logs | Container logs |

## Log Locations

### Core Platform Logs

```bash
# Main log directory
ls -lt $KAMIWAZA_ROOT/logs/

# Common core log files
ls -lt $KAMIWAZA_ROOT/logs/*.log

# Service-specific logs
ls -lt $KAMIWAZA_ROOT/logs/api/
ls -lt $KAMIWAZA_ROOT/logs/scheduler/
ls -lt $KAMIWAZA_ROOT/logs/worker/
```

### Container Logs

**IMPORTANT:** Container IDs and names change frequently due to redeployments and version updates. Always discover current containers fresh - never assume IDs from previous requests.

```bash
# List all Kamiwaza-related containers (running and stopped)
docker ps -a --filter "name=kamiwaza" --format "table {{.ID}}\t{{.Names}}\t{{.Status}}\t{{.CreatedAt}}"

# List app containers
docker ps -a --filter "name=appgarden" --format "table {{.ID}}\t{{.Names}}\t{{.Status}}"

# List by label if available
docker ps -a --filter "label=kamiwaza" --format "table {{.ID}}\t{{.Names}}\t{{.Status}}"
```

### Getting Container Logs

```bash
# Get logs for a specific container (use name, not ID for stability)
docker logs <container_name> 2>&1 | tail -100

# Get logs with timestamps
docker logs --timestamps <container_name> 2>&1 | tail -100

# Get logs from last hour
docker logs --since 1h <container_name> 2>&1

# Follow logs in real-time
docker logs -f <container_name>

# Get logs around a specific time
docker logs --since "2024-01-15T10:00:00" --until "2024-01-15T11:00:00" <container_name>
```

## Common Analysis Tasks

### Finding Recent Errors

```bash
# Core logs - recent errors
tail -500 $KAMIWAZA_ROOT/logs/*.log | grep -i -E "(error|exception|failed|fatal)" | tail -50

# Container logs - recent errors
docker logs --tail 500 <container_name> 2>&1 | grep -i -E "(error|exception|failed|fatal)"

# All container errors in last hour
for c in $(docker ps --filter "name=kamiwaza" -q); do
  echo "=== $(docker inspect --format '{{.Name}}' $c) ==="
  docker logs --since 1h $c 2>&1 | grep -i error | tail -10
done
```

### Checking Service Health

```bash
# Check running Kamiwaza services
docker ps --filter "name=kamiwaza" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Check for crashed/restarting containers
docker ps -a --filter "name=kamiwaza" --filter "status=exited" --format "table {{.Names}}\t{{.Status}}"
docker ps --filter "name=kamiwaza" --format "{{.Names}}\t{{.Status}}" | grep -i restarting
```

### Investigating a Specific App/Tool

```bash
# Find containers for a specific app (name may have random suffix)
docker ps -a | grep -i "<app-name>"

# Get deployment info
docker inspect <container_name> | jq '.[0].Config.Labels'

# Check resource usage
docker stats --no-stream <container_name>

# Check for OOM kills
docker inspect <container_name> | jq '.[0].State.OOMKilled'
```

### Model-Related Issues

```bash
# Find model containers
docker ps -a | grep -E "(model|llm|vllm|ollama)"

# Check model loading logs
docker logs <model_container> 2>&1 | grep -i -E "(loading|loaded|error|cuda|memory)"

# Check GPU allocation
docker inspect <model_container> | jq '.[0].HostConfig.DeviceRequests'
```

## Log Patterns to Look For

### Common Error Patterns

| Pattern | Likely Cause |
|---------|--------------|
| `Connection refused` | Service not running or wrong port |
| `OOMKilled` | Container ran out of memory |
| `CUDA out of memory` | GPU memory exhausted |
| `Permission denied` | File/directory permissions |
| `No such file or directory` | Missing config or data |
| `timeout` | Network or service latency |
| `401/403` | Authentication/authorization issue |
| `Connection reset by peer` | Network interruption |

### Startup Issues

```bash
# Check container startup logs
docker logs <container_name> 2>&1 | head -100

# Look for initialization errors
docker logs <container_name> 2>&1 | grep -i -E "(init|start|boot|ready)" | head -20
```

## Working with Log Files

### Tail Recent Logs

```bash
# Most recent entries from all logs
tail -f $KAMIWAZA_ROOT/logs/*.log

# Specific log file
tail -100 $KAMIWAZA_ROOT/logs/api.log
```

### Search Historical Logs

```bash
# Search for pattern in all logs
grep -r "pattern" $KAMIWAZA_ROOT/logs/

# Search with context
grep -B5 -A5 "error" $KAMIWAZA_ROOT/logs/api.log

# Search by time (if logs have timestamps)
grep "2024-01-15 10:" $KAMIWAZA_ROOT/logs/api.log
```

### Log Rotation

```bash
# Check for rotated logs
ls -la $KAMIWAZA_ROOT/logs/*.log*
ls -la $KAMIWAZA_ROOT/logs/*.gz

# Read compressed logs
zcat $KAMIWAZA_ROOT/logs/api.log.1.gz | tail -100
```

## Key Reminders

1. **Always use fresh container discovery** - IDs and names change with redeployments
2. **Default to most recent logs** - unless user asks for historical data
3. **Check both file logs AND container logs** - they may have different information
4. **Correlate timestamps** - when tracking an issue across services
5. **Note deployment IDs** - they link related containers/services together

## Troubleshooting Workflow

1. **Clarify the problem** - What error/symptom is the user seeing?
2. **Identify the component** - Core platform, app, tool, or model?
3. **Find relevant containers/logs** - Use fresh discovery
4. **Check recent logs first** - Last hour or last 100 lines
5. **Look for error patterns** - grep for errors, exceptions, failed
6. **Check service health** - Is the container running? Restarting?
7. **Correlate across services** - Follow the request path
8. **Report findings** - Summarize errors and potential causes
