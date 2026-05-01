# Event-Driven Image Annotation and Retrieval System

A complete event-driven system for image annotation, vector indexing, and semantic search using Redis pub-sub architecture with persistent JSON storage and FAISS vector search.

## Architecture

The system implements an event-driven pipeline with Redis pub-sub for asynchronous message passing, JSON-based document storage, and FAISS vector indexing for similarity search.

Message flow:
- image.uploaded -> Processor -> embedding.done -> Storage
- search.request -> Search Handler -> search.result -> CLI
- annotation.corrected -> Correction Handler -> Update JSON stores and FAISS index

## Features

- Event-driven architecture with Redis pub-sub
- Persistent JSON document storage with nested annotations
- FAISS vector index for embedding storage and similarity search
- Deterministic simulated AI inference
- Event replay from JSON files
- Annotation correction with history tracking
- Idempotent message processing with event ID tracking
- Malformed message rejection
- Vector similarity search by topic
- Image similarity search

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

Terminal 2 - Run application:
```bash
python3 system.py
```

## Usage

Search commands:
- `cat` - Keyword search for exact label matches
- `vector cat` - Vector similarity search using FAISS embeddings
- `similar img_1004` - Find images visually similar to a given image
- `correct` - Fix annotation labels with history tracking
- `quit` - Exit application

Replay sample events:
```bash
python3 replay.py
```

## Data Models

The annotation document stores image metadata, detected objects with bounding boxes and confidence scores, embeddings, review status, correction notes, and version history.

The vector index stores both image-level and object-level embeddings for semantic search using FAISS (Facebook AI Similarity Search).

## Sample Output

```
============================================================
EVENT-DRIVEN IMAGE SYSTEM WITH FAISS VECTOR SEARCH
DB: 13 images | Vectors: 35
============================================================

[1] UPLOAD: cat.jpg
[2] PROCESSOR: Analyzing cat.jpg
[3] PROCESSOR: Found objects -> ['cat', 'sofa']
[4] STORAGE: Updated annotations_db.json, vector_index.json, and FAISS index

[search] term | [vector] term | [similar] image_id | [correct] | [quit]: vector cat

==================================================
RESULT (vector): Found 2 image(s) matching 'cat'
Image IDs: ['ddb93803...', 'f6217bda...']
==================================================
```

## Testing

Run unit tests:
```bash
pytest test_system.py -v
```

Tests cover event contract validation, idempotent and malformed message handling, embedding generation, FAISS vector search, concurrent processing, correction workflow persistence, and processed event tracking.

## Files

- system.py - Main application with all services and FAISS integration
- vector_search.py - FAISS vector search engine wrapper
- test_system.py - Unit tests
- replay.py - Event replay utility
- sample_events.json - Sample image submissions
- annotations_db.json - Persistent annotation store
- vector_index.json - Vector embedding index
- processed_events.json - Tracked processed event IDs
- faiss_index.bin - FAISS binary index file
- requirements.txt - Python dependencies
