# Event-Driven Image Annotation and Retrieval System

A complete event-driven system for image annotation, vector indexing, and semantic search using Redis pub-sub architecture with persistent JSON storage.

## Architecture

The system implements an event-driven pipeline with Redis pub-sub for asynchronous message passing, JSON-based document storage, and vector indexing for similarity search.

Message flow:
- image.uploaded -> Processor -> embedding.done -> Storage
- search.request -> Search Handler -> search.result -> CLI
- annotation.corrected -> Correction Handler -> Update JSON stores

## Features

- Event-driven architecture with Redis pub-sub
- Persistent JSON document storage with nested annotations
- Vector index for embedding storage and similarity search
- Deterministic simulated AI inference
- Event replay from JSON files
- Annotation correction with history tracking
- Idempotent message processing
- Malformed message rejection

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

Search by entering object labels when prompted: cat, dog, truck, tree, or vehicle.

Correct annotations by typing 'correct' and providing the image ID, old label, new label, and object index. The system updates both annotation and vector index files with correction history.

Replay sample events:
```bash
python3 replay.py
```

## Data Models

The annotation document stores image metadata, detected objects with bounding boxes and confidence scores, embeddings, review status, correction notes, and history.

The vector index stores both image-level and object-level embeddings for semantic search.

## Sample Output

```
============================================================
EVENT-DRIVEN IMAGE SYSTEM
DB: 9 images | Vectors: 26
============================================================

[1] UPLOAD: cat.jpg
[2] PROCESSOR: Analyzing cat.jpg
[3] PROCESSOR: Found objects -> ['cat', 'sofa']
[4] STORAGE: Updated annotations_db.json and vector_index.json

[search] Enter term | [correct] fix label | [quit]: cat

==================================================
RESULT: Found 3 image(s) matching 'cat'
Image IDs: ['img_1004', 'f6217bda...', 'c972ed3b...']
==================================================
```

## Testing

Run unit tests:
```bash
pytest test_system.py -v
```

Tests cover event contract validation, idempotent and malformed message handling, embedding generation, concurrent processing, and correction workflow persistence.

## Files

- system.py - Main application with all services
- test_system.py - Unit tests
- replay.py - Event replay utility
- sample_events.json - Sample image submissions
- annotations_db.json - Persistent annotation store
- vector_index.json - Vector embedding index
- requirements.txt - Python dependencies
