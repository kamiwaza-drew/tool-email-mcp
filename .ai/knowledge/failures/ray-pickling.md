# Ray Pickling

UNPICKLABLE: SQLAlchemy ORM, Sessions, File handles, C extensions

## Common Errors
```
TypeError: cannot pickle 'sqlalchemy.orm.session.Session' object
TypeError: cannot pickle '_thread.lock' object
ray.exceptions.RaySystemError: Failed to unpickle serialized exception
```

## Solutions

### Convert to Dict/Pydantic
```python
# WRONG
@ray.remote
def process_model(model: DBModel):
    return model.name

# CORRECT
@ray.remote
def process_model(model_dict: dict):
    return model_dict['name']

# Usage
model_schema = ModelSchema.from_orm(model)
result = ray.get(process_model.remote(model_schema.dict()))
```

### Pass IDs Not Objects
```python
@ray.remote
def process_model(model_id: str):
    db = SessionLocal()
    model = db.query(DBModel).filter(DBModel.id == model_id).first()
    result = process(model)
    db.close()
    return result
```

### Cython Exclusions
```python
CYTHON_EXCLUSIONS = [
    "kamiwaza/serving/engines/",
    "kamiwaza/serving/ray_deployments/",
    "kamiwaza/cluster/",
    "kamiwaza/scheduler/",
]
```

## Prevention
- Type hints: `def remote(data: dict) -> dict:`
- Test pickling: `pickle.dumps(schema.dict())`
- Log types before Ray calls
- Use Ray Serve for stateful services