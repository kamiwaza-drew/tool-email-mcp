# Developer Guide: Embedding and Querying with Kamiwaza

This guide covers how to generate embeddings and perform semantic search using Kamiwaza's APIs and Milvus vector database.

## Overview

Kamiwaza provides:
- **Embedding API** (`/api/embedding/batch`) - Generate vector embeddings from text
- **VectorDB API** (`/api/vectordb/`) - Insert and manage vectors in Milvus
- **Milvus** - Vector database for similarity search (port 19530)

### Why Direct Milvus for Search?

The Kamiwaza VectorDB API supports search via `POST /api/vectordb/search_vectors`, but this guide uses the Milvus client directly for querying. Here's why:

1. **No metadata filtering** - The current `SearchVectorsRequest` schema doesn't expose Milvus's `filter` parameter. For access control and scoped searches (e.g., `classification == "RESTRICTED"`), direct Milvus access is required.

2. **Pre-embedded vectors only** - The API requires `query_vectors` (already-embedded vectors), not raw text. This means two API calls (embed → search) vs. a single workflow with direct access.

3. **Full Milvus capabilities** - Direct access provides the complete Milvus feature set including hybrid search, expression filtering, and advanced search parameters.

**Recommendation**: Use the Kamiwaza API for vector insertion (handles collection creation, schema management) and direct Milvus client for search operations requiring filtering or advanced features.

## Prerequisites

```bash
pip install httpx pymilvus
```

## Authentication

All API calls require a bearer token from Keycloak:

```python
import httpx

def get_auth_token(api_base: str, username: str = "admin", password: str = "kamiwaza") -> str:
    """Acquire bearer token from Keycloak."""
    token_resp = httpx.post(
        f"{api_base}/realms/kamiwaza/protocol/openid-connect/token",
        data={
            "grant_type": "password",
            "username": username,
            "password": password,
            "client_id": "kamiwaza-platform",
        },
        verify=False,
        timeout=30.0,
    )
    token_resp.raise_for_status()
    return token_resp.json()["access_token"]

# Usage
api_base = "https://localhost"  # or your Kamiwaza hostname
token = get_auth_token(api_base)
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
```

## Generating Embeddings

### Single Text

```python
def embed_text(api_base: str, token: str, text: str, model: str = "Qwen/Qwen3-Embedding-4B") -> list[float]:
    """Generate embedding for a single text."""
    resp = httpx.post(
        f"{api_base}/api/embedding/batch",
        params={
            "model": model,
            "provider_type": "huggingface_embedding",
            "batch_size": 1,
        },
        json=[text],
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        verify=False,
        timeout=120.0,
    )
    resp.raise_for_status()
    return resp.json()[0]

# Usage
embedding = embed_text(api_base, token, "What are the risks to energy infrastructure?")
print(f"Embedding dimension: {len(embedding)}")  # 2560 for Qwen3-Embedding-4B
```

### Batch Embeddings

```python
def embed_batch(api_base: str, token: str, texts: list[str], batch_size: int = 32) -> list[list[float]]:
    """Generate embeddings for multiple texts."""
    all_embeddings = []

    for i in range(0, len(texts), batch_size):
        chunk = texts[i:i + batch_size]
        resp = httpx.post(
            f"{api_base}/api/embedding/batch",
            params={
                "model": "Qwen/Qwen3-Embedding-4B",
                "provider_type": "huggingface_embedding",
                "batch_size": batch_size,
            },
            json=chunk,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            verify=False,
            timeout=120.0,
        )
        resp.raise_for_status()
        all_embeddings.extend(resp.json())

    return all_embeddings
```

## Storing Vectors in Milvus

### Via Kamiwaza API

```python
def insert_vectors(
    api_base: str,
    token: str,
    collection: str,
    vectors: list[list[float]],
    metadata: list[dict],
    field_list: list[tuple] = None,
) -> None:
    """Insert vectors with metadata into Milvus via Kamiwaza API."""
    field_list = field_list or [
        ("source_file", "str"),
        ("classification", "str"),
        ("chunk_index", "int"),
    ]

    resp = httpx.post(
        f"{api_base}/api/vectordb/insert_vectors",
        json={
            "collection_name": collection,
            "vectors": vectors,
            "metadata": metadata,
            "dimensions": len(vectors[0]),
            "field_list": field_list,
        },
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        verify=False,
        timeout=60.0,
    )
    resp.raise_for_status()
```

### Direct Milvus Access

```python
from pymilvus import MilvusClient

client = MilvusClient(uri="http://localhost:19530")

# Create collection (auto-creates if using insert)
client.create_collection(
    collection_name="my_docs",
    dimension=2560,
    metric_type="IP",  # Inner Product for normalized embeddings
)

# Insert with metadata
client.insert(
    collection_name="my_docs",
    data=[
        {"embedding": vector, "source_file": "doc.pdf", "chunk_index": 0}
        for vector in vectors
    ],
)
```

## Semantic Search

### Basic Search

```python
from pymilvus import MilvusClient

def semantic_search(
    query: str,
    api_base: str,
    token: str,
    collection: str = "odin_s1_docs",
    top_k: int = 5,
) -> list[dict]:
    """Perform semantic search: embed query and search Milvus."""

    # 1. Embed the query
    query_vector = embed_text(api_base, token, query)

    # 2. Search Milvus
    client = MilvusClient(uri="http://localhost:19530")
    client.load_collection(collection)

    results = client.search(
        collection_name=collection,
        data=[query_vector],
        limit=top_k,
        output_fields=["source_file", "classification", "chunk_index"],
        search_params={"metric_type": "IP", "params": {"nprobe": 128}},
    )

    return [
        {
            "score": hit["distance"],
            "source_file": hit["entity"].get("source_file"),
            "classification": hit["entity"].get("classification"),
            "chunk_index": hit["entity"].get("chunk_index"),
        }
        for hit in results[0]
    ]

# Usage
results = semantic_search(
    "What are the risks to energy infrastructure in Bagansait?",
    api_base,
    token,
)
for r in results:
    print(f"{r['score']:.4f} - {r['source_file']}")
```

### Filtered Search

```python
# Search only RESTRICTED documents
results = client.search(
    collection_name="odin_s1_docs",
    data=[query_vector],
    limit=5,
    filter='classification == "RESTRICTED"',
    output_fields=["source_file", "classification"],
    search_params={"metric_type": "IP", "params": {"nprobe": 128}},
)

# Search by multiple classifications
results = client.search(
    collection_name="odin_s1_docs",
    data=[query_vector],
    limit=5,
    filter='classification in ["RESTRICTED", "UNMARKED"]',
    output_fields=["source_file", "classification"],
    search_params={"metric_type": "IP", "params": {"nprobe": 128}},
)
```

## Collection Management

```python
from pymilvus import MilvusClient

client = MilvusClient(uri="http://localhost:19530")

# List collections
collections = client.list_collections()

# Get collection stats
stats = client.get_collection_stats("odin_s1_docs")
print(f"Row count: {stats['row_count']}")

# Load collection (required before search)
client.load_collection("odin_s1_docs")

# Drop collection
client.drop_collection("odin_s1_docs")
```

## Complete Example: Document Ingestion Pipeline

```python
import httpx
from pymilvus import MilvusClient
from pathlib import Path

def ingest_document(
    api_base: str,
    token: str,
    text: str,
    source_file: str,
    collection: str = "my_docs",
    chunk_size: int = 350,
    chunk_overlap: int = 40,
) -> int:
    """Chunk, embed, and store a document."""

    # 1. Chunk the text
    words = text.split()
    chunks = []
    step = chunk_size - chunk_overlap
    for i in range(0, len(words), step):
        chunk = " ".join(words[i:i + chunk_size])
        if chunk:
            chunks.append(chunk)

    if not chunks:
        return 0

    # 2. Generate embeddings
    embeddings = embed_batch(api_base, token, chunks)

    # 3. Prepare metadata
    metadata = [
        {
            "source_file": source_file,
            "chunk_index": i,
            "classification": "UNMARKED",
        }
        for i in range(len(chunks))
    ]

    # 4. Insert into Milvus
    insert_vectors(api_base, token, collection, embeddings, metadata)

    return len(chunks)

# Usage
token = get_auth_token(api_base)
text = Path("document.txt").read_text()
count = ingest_document(api_base, token, text, "document.txt")
print(f"Ingested {count} chunks")
```

## Troubleshooting

### Common Issues

1. **401 Unauthorized on embedding API**
   - Ensure you're using the correct API hostname (not just `localhost`)
   - Token may have expired - re-acquire token

2. **Milvus search hangs**
   - Collection may not be loaded: `client.load_collection("collection_name")`
   - Check Milvus container health: `docker ps --filter "name=milvus"`
   - Check logs: `docker logs default_milvus-standalone`

3. **Empty search results**
   - Verify collection has data: `client.get_collection_stats("collection_name")`
   - Ensure collection is loaded before searching

4. **Dimension mismatch**
   - Qwen3-Embedding-4B produces 2560-dimensional vectors
   - Collection dimension must match embedding model output

### Health Checks

```bash
# Check Milvus containers
docker ps -a --filter "name=milvus"

# Check Milvus REST API
curl -s http://localhost:19530/v2/vectordb/collections/list -d '{}'

# Check collection exists
curl -s http://localhost:19530/v2/vectordb/collections/describe \
  -H "Content-Type: application/json" \
  -d '{"collectionName": "odin_s1_docs"}'
```

## Reference

- **Embedding API**: `POST /api/embedding/batch`
- **VectorDB Insert**: `POST /api/vectordb/insert_vectors`
- **Milvus Port**: 19530
- **Default Model**: `Qwen/Qwen3-Embedding-4B` (2560 dimensions)
- **Metric Type**: Inner Product (IP) for similarity search
