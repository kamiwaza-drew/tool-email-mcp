# Database Gotchas

DATABASE_MODES: PostgreSQL/CockroachDB (Enterprise), SQLite (KAMIWAZA_LITE)

## UUID Issues
PROBLEM: PostgreSQL UUID type vs SQLite string
```python
# WRONG
from sqlalchemy import UUID
id = Column(UUID(as_uuid=True), primary_key=True)
db.execute(text("SELECT * WHERE id = :id"), {'id': uuid_object})

# CORRECT
from kamiwaza.lib.util import get_uuid_column_type
DBUUID = get_uuid_column_type()
id = Column(DBUUID, primary_key=True, default=uuid.uuid4)
db.execute(text("SELECT * WHERE id = :id"), {'id': str(uuid_object)})
```

## SQL Functions
POSTGRES_ONLY: NOW(), INTERVAL, EXTRACT, ARRAY
```python
# COMPATIBLE
if get_kamiwaza_lite_setting():
    query = "SELECT * FROM models WHERE created_at > ?"
    params = [datetime.utcnow().isoformat()]
else:
    query = "SELECT * FROM models WHERE created_at > NOW() - INTERVAL '1 hour'"
    params = []
```

## JSON Handling
SQLITE_JSON: text storage, no operators
```python
# POSTGRES: config->>'version' = '1.0'
# SQLITE: json_extract(config, '$.version') = '1.0'
# BEST: model.config.get('version') == '1.0'
```

## Type Differences
BOOLEAN: PostgreSQL native, SQLite INTEGER (0/1)
AUTOINCREMENT: Let SQLAlchemy handle
TRANSACTIONS: SQLite file-lock, no concurrent writes

## Checklist
[ ] Use get_uuid_column_type()
[ ] Stringify UUIDs in raw SQL
[ ] Check get_kamiwaza_lite_setting()
[ ] Test both backends
[ ] Avoid PostgreSQL-specific SQL
[ ] Use ORM over raw SQL