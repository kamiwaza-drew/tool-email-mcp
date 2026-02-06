# Kamiwaza Data Integration Guide

A practical guide for 3rd party developers to register datasets, query the catalog, build RAG indexes, and retrieve data.

## Overview

Kamiwaza provides four key APIs for data integration:

| API | Endpoint | Purpose |
|-----|----------|---------|
| **Catalog** | `/api/catalog/datasets/` | Register and query dataset metadata |
| **Ingestion** | `/api/ingestion/` | Create data connectors and ingest sources |
| **DDE** | `/api/dde/documents/` | Index documents for RAG |
| **Retrieval** | `/api/retrieval/jobs` | Download dataset content |

**Base URL**: `https://localhost` (or your Kamiwaza host)

---

## 1. Registering Datasets

Datasets are registered in the **Catalog** service, which stores metadata about your data sources.

### Create a Dataset

```bash
curl -X POST "https://localhost/api/catalog/datasets/" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "sales_data_2024",
    "platform": "file",
    "environment": "PROD",
    "description": "Quarterly sales data for 2024",
    "tags": ["sales", "quarterly", "2024"],
    "properties": {
      "path": "/data/sales/2024_sales.csv",
      "format": "csv",
      "record_count": "15000"
    }
  }'
```

**Response**: Returns the dataset URN
```json
"urn:li:dataset:(urn:li:dataPlatform:file,sales_data_2024,PROD)"
```

### Dataset Schema

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Unique dataset identifier |
| `platform` | string | Yes | Storage platform: `file`, `s3`, `postgres`, `kafka`, etc. |
| `environment` | string | No | Default: `PROD` |
| `description` | string | No | Human-readable description |
| `tags` | array | No | Searchable tags |
| `properties` | object | No | Arbitrary metadata (path, format, etc.) |
| `dataset_schema` | object | No | Column definitions |
| `container_urn` | string | No | Parent container URN |

### Python Example

```python
import httpx

BASE_URL = "https://localhost"

def register_dataset(name: str, path: str, tags: list = None) -> str:
    """Register a dataset and return its URN."""
    payload = {
        "name": name,
        "platform": "file",
        "environment": "PROD",
        "properties": {"path": path},
        "tags": tags or []
    }

    resp = httpx.post(
        f"{BASE_URL}/api/catalog/datasets/",
        json=payload,
        verify=False
    )
    resp.raise_for_status()
    return resp.json()  # Returns URN string
```

---

## 2. Querying Datasets

### List All Datasets

```bash
curl -sk "https://localhost/api/catalog/datasets/"
```

### Search by Name

The `query` parameter performs a **case-insensitive substring match on the dataset name**:

```bash
# Find datasets with "sales" in the name
curl -sk "https://localhost/api/catalog/datasets/?query=sales"
```

### Get Dataset by URN

```bash
# Option 1: Query parameter (recommended for URNs with special characters)
curl -sk "https://localhost/api/catalog/datasets/by-urn?urn=urn:li:dataset:(urn:li:dataPlatform:file,sales_data_2024,PROD)"

# Option 2: Path parameter (for simple URNs)
curl -sk "https://localhost/api/catalog/datasets/urn:li:dataset:(urn:li:dataPlatform:file,sales_data_2024,PROD)"
```

### Query Limitations

The `query` parameter searches **name only**. It does NOT search:
- Description
- Tags
- Properties

To filter by other fields, retrieve all datasets and filter client-side, or use tags strategically for categorization.

### Python Example

```python
def search_datasets(query: str = None) -> list:
    """Search datasets by name."""
    params = {"query": query} if query else {}
    resp = httpx.get(
        f"{BASE_URL}/api/catalog/datasets/",
        params=params,
        verify=False
    )
    resp.raise_for_status()
    return resp.json()

def get_dataset(urn: str) -> dict:
    """Get a specific dataset by URN."""
    resp = httpx.get(
        f"{BASE_URL}/api/catalog/datasets/by-urn",
        params={"urn": urn},
        verify=False
    )
    resp.raise_for_status()
    return resp.json()
```

---

## 3. Generating RAG Indexes

For RAG (Retrieval-Augmented Generation), use the **DDE (Document Data Engine)** service to index documents.

### Step 1: Create a Connector

Connectors define how to access your data source:

```bash
curl -X POST "https://localhost/api/ingestion/connectors/" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "local_documents",
    "source_type": "filesystem",
    "connector_type": "local",
    "description": "Local document storage",
    "connection_config": {
      "base_path": "/data/documents"
    }
  }'
```

### Step 2: Trigger Ingestion

Start an ingestion job to process documents:

```bash
curl -X POST "https://localhost/api/ingestion/connectors/{connector_id}/trigger_ingest"
```

### Step 3: Index Documents

Index individual documents for RAG:

```bash
curl -X POST "https://localhost/api/dde/documents/" \
  -H "Content-Type: application/json" \
  -d '{
    "source_id": "connector-uuid-here",
    "source_ref": "/data/documents/report.pdf",
    "item_type": "document",
    "metadata": {
      "title": "Q4 Report",
      "category": "reports"
    }
  }'
```

### List Indexed Documents

```bash
curl -sk "https://localhost/api/dde/documents/?limit=50&offset=0"
```

### Python Example

```python
def create_connector(name: str, base_path: str) -> dict:
    """Create a filesystem connector."""
    payload = {
        "name": name,
        "source_type": "filesystem",
        "connector_type": "local",
        "connection_config": {"base_path": base_path}
    }
    resp = httpx.post(
        f"{BASE_URL}/api/ingestion/connectors/",
        json=payload,
        verify=False
    )
    resp.raise_for_status()
    return resp.json()

def trigger_ingestion(connector_id: str) -> dict:
    """Start ingestion for a connector."""
    resp = httpx.post(
        f"{BASE_URL}/api/ingestion/connectors/{connector_id}/trigger_ingest",
        verify=False
    )
    resp.raise_for_status()
    return resp.json()
```

---

## 4. Retrieving Data

The **Retrieval** service downloads actual content from datasets registered in the catalog.

### Transport Types

| Transport | Use Case | Behavior |
|-----------|----------|----------|
| `inline` | Small datasets (<1MB) | Data returned in response (synchronous) |
| `sse` | Medium datasets | Server-Sent Events streaming |
| `grpc` | Large datasets | gRPC streaming (best performance) |
| `auto` | Default | Service selects based on size |

### Synchronous Retrieval (inline)

For small datasets, get data in a single request:

```bash
curl -X POST "https://localhost/api/retrieval/jobs" \
  -H "Content-Type: application/json" \
  -d '{
    "dataset_urn": "urn:li:dataset:(urn:li:dataPlatform:file,sales_data_2024,PROD)",
    "transport": "inline",
    "limit_rows": 100
  }'
```

**Response** (data included):
```json
{
  "job_id": "abc-123",
  "transport": "inline",
  "status": "completed",
  "dataset": {
    "urn": "urn:li:dataset:(...)",
    "platform": "file",
    "path": "/data/sales/2024_sales.csv",
    "format": "csv"
  },
  "inline": {
    "media_type": "application/json",
    "data": [...],
    "row_count": 100
  }
}
```

### Streaming Retrieval (SSE)

For larger datasets, use Server-Sent Events:

```bash
# Step 1: Create job
JOB=$(curl -s -X POST "https://localhost/api/retrieval/jobs" \
  -H "Content-Type: application/json" \
  -d '{"dataset_urn": "urn:...", "transport": "sse"}')

JOB_ID=$(echo $JOB | jq -r '.job_id')

# Step 2: Stream data
curl -N "https://localhost/api/retrieval/jobs/${JOB_ID}/stream"
```

### Request Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `dataset_urn` | string | Required. Catalog URN |
| `transport` | string | `auto`, `inline`, `sse`, `grpc` |
| `limit_rows` | int | Max rows to return |
| `offset` | int | Skip N rows |
| `columns` | array | Select specific columns |
| `format_hint` | string | `csv`, `parquet`, `json`, `binary` |
| `batch_size` | int | Chunk size for streaming |

### Python Example

```python
import json

async def retrieve_inline(dataset_urn: str, limit_rows: int = 100) -> dict:
    """Retrieve small dataset synchronously."""
    async with httpx.AsyncClient(verify=False) as client:
        resp = await client.post(
            f"{BASE_URL}/api/retrieval/jobs",
            json={
                "dataset_urn": dataset_urn,
                "transport": "inline",
                "limit_rows": limit_rows
            }
        )
        resp.raise_for_status()
        job = resp.json()

        if job.get("inline"):
            return job["inline"]["data"]
        return None

async def retrieve_streaming(dataset_urn: str):
    """Stream larger dataset via SSE."""
    async with httpx.AsyncClient(verify=False, timeout=None) as client:
        # Create job
        resp = await client.post(
            f"{BASE_URL}/api/retrieval/jobs",
            json={"dataset_urn": dataset_urn, "transport": "sse"}
        )
        job = resp.json()
        job_id = job["job_id"]

        # Stream data
        async with client.stream("GET", f"{BASE_URL}/api/retrieval/jobs/{job_id}/stream") as stream:
            async for line in stream.aiter_lines():
                if line.startswith("data: "):
                    chunk = json.loads(line[6:])
                    yield chunk
```

---

## Complete Workflow Example

Here's a complete example that registers a dataset, queries it, and retrieves content:

```python
import httpx
import asyncio

BASE_URL = "https://localhost"

class KamiwazaClient:
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.client = httpx.Client(verify=False)

    # === Catalog Operations ===

    def register_dataset(self, name: str, path: str, **kwargs) -> str:
        """Register a dataset, return URN."""
        payload = {
            "name": name,
            "platform": kwargs.get("platform", "file"),
            "environment": kwargs.get("environment", "PROD"),
            "description": kwargs.get("description"),
            "tags": kwargs.get("tags", []),
            "properties": {"path": path, **kwargs.get("properties", {})}
        }
        resp = self.client.post(f"{self.base_url}/api/catalog/datasets/", json=payload)
        resp.raise_for_status()
        return resp.json()

    def search_datasets(self, query: str = None) -> list:
        """Search datasets by name."""
        params = {"query": query} if query else {}
        resp = self.client.get(f"{self.base_url}/api/catalog/datasets/", params=params)
        resp.raise_for_status()
        return resp.json()

    def get_dataset(self, urn: str) -> dict:
        """Get dataset by URN."""
        resp = self.client.get(f"{self.base_url}/api/catalog/datasets/by-urn", params={"urn": urn})
        resp.raise_for_status()
        return resp.json()

    # === Retrieval Operations ===

    def retrieve_data(self, dataset_urn: str, limit_rows: int = None) -> dict:
        """Retrieve dataset content (inline for small datasets)."""
        payload = {
            "dataset_urn": dataset_urn,
            "transport": "inline"
        }
        if limit_rows:
            payload["limit_rows"] = limit_rows

        resp = self.client.post(f"{self.base_url}/api/retrieval/jobs", json=payload)
        resp.raise_for_status()
        job = resp.json()

        if job.get("inline"):
            return job["inline"]["data"]
        return job


# Usage
if __name__ == "__main__":
    client = KamiwazaClient()

    # Register a dataset
    urn = client.register_dataset(
        name="quarterly_sales",
        path="/data/sales/q4_2024.csv",
        tags=["sales", "q4", "2024"],
        description="Q4 2024 sales data"
    )
    print(f"Registered: {urn}")

    # Search for it
    datasets = client.search_datasets("sales")
    print(f"Found {len(datasets)} datasets")

    # Retrieve content
    data = client.retrieve_data(urn, limit_rows=10)
    print(f"Retrieved {len(data)} rows")
```

---

## Error Handling

### Common HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 201 | Created |
| 400 | Bad request (invalid parameters) |
| 404 | Dataset/resource not found |
| 422 | Validation error |
| 503 | Service unavailable |

### Error Response Format

```json
{
  "detail": {
    "error": "not_found",
    "message": "Dataset not found"
  }
}
```

---

## Authentication

When authentication is enabled (`KAMIWAZA_USE_AUTH=true`), include a bearer token:

```bash
# Get token
TOKEN=$(curl -s -X POST "https://localhost/auth/realms/kamiwaza/protocol/openid-connect/token" \
  -d "grant_type=password&username=admin&password=kamiwaza&client_id=kamiwaza-platform" \
  | jq -r '.access_token')

# Use token
curl -H "Authorization: Bearer $TOKEN" \
  "https://localhost/api/catalog/datasets/"
```

When auth is disabled (`KAMIWAZA_USE_AUTH=false`), no token is required.

---

## API Reference Summary

### Catalog API

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/catalog/datasets/` | Create dataset |
| GET | `/api/catalog/datasets/` | List/search datasets |
| GET | `/api/catalog/datasets/by-urn?urn=` | Get by URN |
| PATCH | `/api/catalog/datasets/by-urn?urn=` | Update dataset |
| DELETE | `/api/catalog/datasets/by-urn?urn=` | Delete dataset |

### Retrieval API

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/retrieval/jobs` | Create retrieval job |
| GET | `/api/retrieval/jobs/{job_id}` | Get job status |
| GET | `/api/retrieval/jobs/{job_id}/stream` | Stream data (SSE) |

### Ingestion API

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/ingestion/connectors/` | Create connector |
| GET | `/api/ingestion/connectors/` | List connectors |
| POST | `/api/ingestion/connectors/{id}/trigger_ingest` | Start ingestion |

### DDE API

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/dde/documents/` | Index document |
| GET | `/api/dde/documents/` | List documents |
| GET | `/api/dde/documents/{id}` | Get document |
