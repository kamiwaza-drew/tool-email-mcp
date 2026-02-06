# App Garden Limits

## Dynamic Ports
PROBLEM: API_URL=http://backend:8000
SOLUTION: API_URL=http://backend (no port)
TEMPLATE: "PUBLIC_URL": "https://localhost:{app_port}"

## Volume Persistence
PROBLEM: Data loss between deployments
SOLUTION: Design for statelessness or use external storage

## Service Discovery
PROBLEM: Backend not ready on startup
SOLUTION:
```python
for i in range(30):
    try:
        requests.get("http://backend/health")
        break
    except:
        time.sleep(2)
```

## Resource Limits
PROBLEM: Using all CPU cores
SOLUTION: Detect container limits via cgroups or env vars

## Startup Time
LIMIT: 60 seconds
SOLUTION: Progressive initialization with health states

## File System
WRITABLE: /app/, /tmp/
READ-ONLY: /etc/, /usr/

## Signals
HANDLE: SIGTERM for graceful shutdown
```python
signal.signal(signal.SIGTERM, shutdown_handler)
```

## Provided Variables
- SERVICE_NAME, SERVICE_PORT
- KAMIWAZA_ENDPOINT, KAMIWAZA_API_URI
- KAMIWAZA_APP_PORT, KAMIWAZA_APP_URL
- KAMIWAZA_MODEL_PORT, KAMIWAZA_MODEL_URL

## Debug Commands
```bash
kubectl logs -n appgarden deployment/myapp
kubectl logs --previous -n appgarden deployment/myapp
```

## Common Errors
- CrashLoopBackOff: Check startup logs
- OOMKilled: Increase memory limit
- ImagePullBackOff: Verify image name
- Liveness probe failed: Check health endpoint
- kamiwaza platform APIs generally require trailing slashes