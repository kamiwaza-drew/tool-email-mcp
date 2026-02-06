# Service Patterns

## Structure
```
kamiwaza/services/{service_name}/
├── api.py          # FastAPI routes (thin)
├── services.py     # Business logic (thick)
├── models/         # SQLAlchemy
├── schemas/        # Pydantic
├── config.py       # Configuration
├── exceptions.py   # Custom errors
└── setup.py        # DB init
```

## Dependency Injection
```python
# services.py
class ModelService:
    def __init__(self, db: Session = Depends(get_db)):
        self.db = db

    async def get_model(self, model_id: UUID) -> ModelSchema:
        model = self.db.query(DBModel).filter(DBModel.id == str(model_id)).first()
        if not model:
            raise ModelNotFoundException(f"Model {model_id} not found")
        return ModelSchema.from_orm(model)

# api.py
@router.get("/models/{model_id}")
async def get_model(model_id: UUID, service: ModelService = Depends()) -> ModelSchema:
    return await service.get_model(model_id)
```

## Schema Conversion
RULE: Always convert ORM to Pydantic before returning
```python
def list_models(self) -> List[ModelSchema]:
    models = self.db.query(DBModel).all()
    return [ModelSchema.from_orm(m) for m in models]  # Convert here
```

## Error Handling
```python
class ServiceException(Exception): pass
class ModelNotFoundException(ServiceException): pass

# Usage
if not model:
    raise ModelNotFoundException(f"Model {model_id} not found")
```

## Async External Calls
```python
async def download_model(self, url: str) -> bytes:
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status != 200:
                raise DownloadException(f"Failed: {response.status}")
            return await response.read()
```

## Configuration
```python
class ServiceConfig(BaseSettings):
    database_pool_size: int = 20
    max_model_size: int = 10 * 1024 * 1024 * 1024
    class Config:
        env_prefix = "MODEL_SERVICE_"
```

## Testing Pattern
```python
@pytest.fixture
def service(mock_db):
    return ModelService(db=mock_db)

def test_get_model_success(service, mock_db):
    mock_db.query.return_value.filter.return_value.first.return_value = mock_model
    result = service.get_model(model_id)
    assert isinstance(result, ModelSchema)
```

## Key Rules
- Thin API layer, thick service layer
- Convert to Pydantic at boundaries
- Explicit error handling
- Async for external I/O
- Mock dependencies in tests