# Refactor Service

VARIABLES:
- SERVICE_NAME: {service-name}
- REFACTORING_GOAL: {goal}

## Pre-Refactor
```bash
make test ARGS=tests/unit/services/{SERVICE_NAME}
git checkout -b refactor/{SERVICE_NAME}
```

## Structure
```
kamiwaza/services/{SERVICE_NAME}/
├── api.py          # Thin
├── services.py     # Business logic
├── models/         # SQLAlchemy
├── schemas/        # Pydantic
├── exceptions.py   # Custom errors
```

## Patterns

### Extract Logic
```python
# BEFORE (api.py)
@router.post("/endpoint")
async def endpoint(data: dict):
    # Complex logic

# AFTER
@router.post("/endpoint")
async def endpoint(data: Schema, service: Service = Depends()):
    return await service.handle_endpoint(data)
```

### Repository Pattern
```python
class ModelRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, id: UUID) -> Optional[Model]:
        return self.db.query(Model).filter(Model.id == id).first()
```

## Verify
```bash
make test ARGS=tests/unit/services/{SERVICE_NAME}
make test-cov ARGS=tests/unit/services/{SERVICE_NAME}
make check-python-lint-new-code
make check-python-types-new-code
```

## Rules
- Keep API compatibility
- Test before/after each change
- Small focused commits
- Update imports in dependent services