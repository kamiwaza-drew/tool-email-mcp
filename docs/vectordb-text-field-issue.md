# VectorDB Text Field Issue

**Date:** 2024-12-04
**Status:** Workaround Required
**Affects:** Apps using `/api/vectordb/search_vectors` that need to retrieve original text

---

## Summary

The Kamiwaza VectorDB API currently does not store or return the original text content that was embedded. Apps attempting to retrieve a `text` field from search results will receive a **501 error**.

---

## Problem

### Symptoms
- `POST /api/vectordb/search_vectors` returns **501 Not Implemented**
- Error in logs: `MilvusException: (code=65535, message=field text not exist)`

### Root Cause
When vectors are inserted via the Kamiwaza API, **only metadata fields are stored** - the original text content is not persisted:

```
Current fields in odin_s1_docs collection:
├── id              (INT64)
├── embedding       (FLOAT_VECTOR - 2560 dims)
├── model_name      (VARCHAR) - empty
├── source          (VARCHAR) - empty
├── catalog_urn     (VARCHAR) - empty
├── offset          (INT64)
├── filename        (VARCHAR) - empty
├── scenario        (VARCHAR)
├── source_file     (VARCHAR)
├── classification  (VARCHAR)
├── rebac_tags      (VARCHAR)
├── chunk_index     (INT64)
└── dataset_name    (VARCHAR)

❌ NO text/content field exists
```

When search requests ask for `output_fields=["text"]`, Milvus returns an error because that field doesn't exist.

---

## Workaround: Use Milvus Directly

Until the Kamiwaza VectorDB API is updated to support text storage, apps should interact with Milvus directly.

### Connection Details
```python
from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType

# Connect to Milvus
connections.connect(
    alias='default',
    host='localhost',  # or 'milvus' from within Docker
    port='19530'
)
```

### Creating a Collection WITH Text Field
```python
from pymilvus import Collection, FieldSchema, CollectionSchema, DataType, utility

COLLECTION_NAME = "my_app_docs"
EMBEDDING_DIM = 2560  # Match your embedding model

# Define schema WITH text field
fields = [
    FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
    FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=EMBEDDING_DIM),
    FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65535),  # THE KEY FIELD
    FieldSchema(name="source_file", dtype=DataType.VARCHAR, max_length=512),
    FieldSchema(name="chunk_index", dtype=DataType.INT64),
    # Add other metadata fields as needed
]

schema = CollectionSchema(fields=fields, description="Documents with text")

# Create collection (drop if exists for fresh start)
if utility.has_collection(COLLECTION_NAME):
    utility.drop_collection(COLLECTION_NAME)

collection = Collection(name=COLLECTION_NAME, schema=schema)

# Create index on embedding field
collection.create_index(
    field_name="embedding",
    index_params={
        "metric_type": "IP",  # Inner Product for normalized embeddings
        "index_type": "IVF_FLAT",
        "params": {"nlist": 128}
    }
)
```

### Inserting Vectors WITH Text
```python
def insert_documents(collection_name: str, texts: list[str], embeddings: list[list[float]], metadata: list[dict]):
    """Insert documents with text content preserved."""
    collection = Collection(collection_name)

    data = [
        embeddings,                                    # embedding field
        texts,                                         # text field - PRESERVED!
        [m.get("source_file", "") for m in metadata], # source_file
        [m.get("chunk_index", 0) for m in metadata],  # chunk_index
    ]

    collection.insert(data)
    collection.flush()

# Example usage
texts = ["This is document 1 content", "This is document 2 content"]
embeddings = [[0.1] * 2560, [0.2] * 2560]  # Your actual embeddings
metadata = [{"source_file": "doc1.pdf", "chunk_index": 0}, {"source_file": "doc2.pdf", "chunk_index": 0}]

insert_documents("my_app_docs", texts, embeddings, metadata)
```

### Searching and Retrieving Text
```python
def search_with_text(collection_name: str, query_embedding: list[float], limit: int = 10) -> list[dict]:
    """Search and return results WITH original text."""
    collection = Collection(collection_name)
    collection.load()

    results = collection.search(
        data=[query_embedding],
        anns_field="embedding",
        param={"metric_type": "IP", "params": {"nprobe": 10}},
        limit=limit,
        output_fields=["text", "source_file", "chunk_index"]  # Include text!
    )

    documents = []
    for hits in results:
        for hit in hits:
            documents.append({
                "id": hit.id,
                "score": hit.score,
                "text": hit.entity.get("text"),         # Original text returned!
                "source_file": hit.entity.get("source_file"),
                "chunk_index": hit.entity.get("chunk_index"),
            })

    return documents

# Example usage
query_embedding = [0.15] * 2560  # Your actual query embedding
results = search_with_text("my_app_docs", query_embedding)

for r in results:
    print(f"Score: {r['score']:.4f}")
    print(f"Text: {r['text'][:100]}...")
    print(f"Source: {r['source_file']}")
    print()
```

---

## Generating Embeddings

You can still use the Kamiwaza Embedding API to generate embeddings:

```python
import httpx

def generate_embedding(text: str, base_url: str = "https://localhost") -> list[float]:
    """Generate embedding using Kamiwaza API."""
    response = httpx.post(
        f"{base_url}/api/embedding/generate",
        json={
            "text": text,
            "usecase": "qa",
            "mode": "passage"  # or "query" for search queries
        },
        verify=False  # For local dev with self-signed certs
    )
    response.raise_for_status()
    return response.json()["embedding"]
```

---

## Complete Example: Ingest and Search

```python
from pymilvus import connections, Collection
import httpx

# Setup
MILVUS_HOST = "localhost"
MILVUS_PORT = "19530"
KAMIWAZA_URL = "https://localhost"
COLLECTION_NAME = "my_app_docs"

connections.connect('default', host=MILVUS_HOST, port=MILVUS_PORT)

def ingest_document(text: str, source_file: str, chunk_index: int):
    """Ingest a document chunk with text preserved."""
    # Generate embedding via Kamiwaza
    embedding = generate_embedding(text)

    # Store in Milvus directly (with text!)
    collection = Collection(COLLECTION_NAME)
    collection.insert([
        [embedding],      # embeddings
        [text],           # text - PRESERVED
        [source_file],    # source_file
        [chunk_index],    # chunk_index
    ])
    collection.flush()

def search_documents(query: str, limit: int = 5) -> list[dict]:
    """Search for relevant documents."""
    # Generate query embedding
    query_embedding = generate_embedding(query)

    # Search Milvus directly
    collection = Collection(COLLECTION_NAME)
    collection.load()

    results = collection.search(
        data=[query_embedding],
        anns_field="embedding",
        param={"metric_type": "IP", "params": {"nprobe": 10}},
        limit=limit,
        output_fields=["text", "source_file", "chunk_index"]
    )

    return [
        {
            "text": hit.entity.get("text"),
            "source": hit.entity.get("source_file"),
            "score": hit.score
        }
        for hits in results for hit in hits
    ]
```

---

## Network Access from Docker Containers

If your app runs in Docker:

| From | Milvus Host | Port |
|------|-------------|------|
| Host machine | `localhost` | `19530` |
| Docker container | `host.docker.internal` | `19530` |
| Docker container (same network) | `milvus` | `19530` |

---

## Future Fix

The Kamiwaza VectorDB API will be updated to:
1. Accept a `text` or `content` field in insert requests
2. Store text content alongside embeddings
3. Return text in search results when requested

Until then, use the direct Milvus approach documented above.

---

## Questions?

Contact the platform team for assistance.
