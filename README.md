# Event-Driven Image Annotation and Retrieval System

A complete event-driven system for image annotation, vector indexing, and semantic search using Redis pub-sub architecture with persistent JSON storage and FAISS vector search.

## Architecture

The system implements an event-driven pipeline where services communicate exclusively through Redis pub-sub topics. Each service runs as a separate process and owns its data store.

### Message Flow

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   CLI       │     │  Processor  │     │   Storage   │     │  Embedding  │     │   Search    │
│  Service    │     │  Service    │     │  Service    │     │  Service    │     │  Service    │
└──────┬──────┘     └──────┬──────┘     └──────┬──────┘     └──────┬──────┘     └──────┬──────┘
       │                   │                   │                   │                   │
       └───────────────────┴───────────────────┴───────────────────┴───────────────────┘
                                              │
                                        ┌─────▼─────┐
                                        │   Redis   │
                                        │  Pub-Sub  │
                                        └───────────┘
                                              │
                          ┌───────────────────┼───────────────────┐
                          │                   │                   │
                  ┌───────▼───────┐   ┌───────▼───────┐   ┌───────▼───────┐
                  │ annotations   │   │   FAISS      │   │  processed    │
                  │ .db.json      │   │   index      │   │  events.json  │
                  │ (Storage owns)│   │(Embedding owns)│  │ (Processor owns)│
                  └───────────────┘   └───────────────┘   └───────────────┘
```

### Service Ownership

| Service | Owns | Subscribes To | Publishes To |
|---------|------|---------------|--------------|
| Processor | processed_events.json | image.uploaded | embedding.done |
| Storage | annotations_db.json | embedding.done, annotation.corrected | none |
| Embedding | vector_index.json, faiss_index.bin | embedding.done | none |
| Search | none (read-only) | search.request | search.result |
| CLI | none | search.result | image.uploaded, search.request, annotation.corrected |

## Features

- Event-driven architecture with Redis pub-sub
- Separate process-based services with clear ownership boundaries
- Persistent JSON document storage with nested annotations
- FAISS vector index for embedding storage and similarity search
- Deterministic simulated AI inference
- Annotation correction with history tracking
- Idempotent message processing with event ID tracking
- Malformed message rejection
- Vector similarity search by topic
- Image similarity search
- GitHub Actions CI/CD pipeline

## Document Model Justification

JSON document storage was chosen over relational tables because annotations contain varying numbers of nested objects including bounding boxes, confidence scores, embeddings, and correction history that evolve over time. A document model avoids premature normalization and empty columns while accommodating variable-length object lists per image.

## Quick Start

Install dependencies:
```bash
pip install -r requirements.txt
```

Terminal 1 - Start Redis:
```bash
redis-server
```

Terminal 2 - Run all services:
```bash
./run_all_services.sh
```

## Usage

| Command | Description |
|---------|-------------|
| `upload cat.jpg` | Upload an image for processing |
| `cat` | Keyword search for exact label matches |
| `vector cat` | Vector similarity search using FAISS embeddings |
| `similar img_1004` | Find images visually similar to a given image |
| `correct` | Fix annotation labels with history tracking |
| `quit` | Exit application |

## Service Commands (for development)

Run services individually for debugging:
```bash
python3 processor_service.py
python3 storage_service.py
python3 embedding_service.py
python3 search_service.py
python3 cli_service.py
```

## Sample Output

```
============================================================
EVENT-DRIVEN IMAGE SYSTEM - CLI SERVICE
All services communicate ONLY through Redis
============================================================

[upload <file>|cat|dog|vector <term>|similar <id>|correct|quit]: upload cat.jpg
[CLI] Uploaded cat.jpg
[PROCESSOR] Analyzing cat.jpg
[PROCESSOR] Found objects -> ['cat', 'sofa']
[STORAGE] Saved annotation for 4f249447-a8c4-4857-bdd2-79425b7242a0
[EMBEDDING] Indexed 2 objects + 1 image for 4f249447-a8c4-4857-bdd2-79425b7242a0

[upload <file>|cat|dog|vector <term>|similar <id>|correct|quit]: cat
[CLI] Searching for: cat

==================================================
RESULT: Found 1 image(s)
Image IDs: ['4f249447-a8c4-4857-bdd2-79425b7242a0']
==================================================
```

## Testing

Run unit tests:
```bash
pytest test_system.py -v
```

Run integration test:
```bash
python3 test_integration.py
```

Tests cover event contract validation, idempotent and malformed message handling, embedding generation, FAISS vector search, concurrent processing, correction workflow persistence, and Redis communication.

## Continuous Integration

GitHub Actions runs on every push to main branch:

- Starts Redis container and Installs dependencies
- Launches all five services (CLI, processor, storage, embedding, search)
- Runs integration tests: upload cat.jpg and dog.png, search by keyword and vector, verify correction workflow

All tests must pass to confirm services communicate exclusively through Redis pub-sub.

## Files

| File | Description |
|------|-------------|
| config.py | Shared Redis topics and file paths |
| utils.py | Embedding generation and helpers |
| processor_service.py | Simulated AI detection service |
| storage_service.py | JSON document store service |
| embedding_service.py | FAISS vector indexing service |
| search_service.py | Vector similarity search service |
| cli_service.py | User interface service |
| run_all_services.sh | Launch all services |
| test_system.py | Unit tests |
| test_integration.py | End-to-end integration test |
| sample_events.json | Sample image submissions |
| annotations_db.json | Persistent annotation store |
| vector_index.json | Vector embedding index |
| processed_events.json | Tracked processed event IDs |
| faiss_index.bin | FAISS binary index |
| requirements.txt | Python dependencies |
| .github/workflows/test.yml | GitHub Actions CI pipeline |
