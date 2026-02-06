# Debug Ray

VARIABLES:
- ISSUE_DESCRIPTION: {ray-issue}

## Check Status
```bash
ray status
ray.is_initialized()
ray.nodes()
ray.available_resources()
```

## Common Issues

### Serialization
```python
# WRONG: SQLAlchemy objects
return db.query(Model).first()

# CORRECT: Dict/Pydantic
return ModelSchema.from_orm(obj).dict()
```

### Resource Allocation
```python
@serve.deployment(ray_actor_options={"num_cpus": 1, "memory": 2*1024*1024*1024})
```

### Logs
```bash
/tmp/ray/session_latest/logs/raylet.out
/tmp/ray/session_latest/logs/monitor.log
```

### Minimal Test
```python
@ray.remote
def simple_task():
    return "Ray working"

ray.get(simple_task.remote())
```

### Dashboard
```yaml
ray-head:
  ports: ["8265:8265"]
  command: ray start --head --dashboard-host 0.0.0.0
```

## Kamiwaza-Specific
CYTHON_EXCLUSIONS: ["kamiwaza/serving/engines/", "kamiwaza/cluster/"]
ETCD_CHECK: client.get('/services/')
RAY_SERVE: manager.list_deployments()

## Diagnostics
```bash
ray stack
ray memory
ray timeline
```