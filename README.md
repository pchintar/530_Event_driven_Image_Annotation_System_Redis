# Event-Driven Image Annotation and Retrieval System

A modular image processing system using Redis pub-sub for asynchronous communication. Images are uploaded, processed (simulated inference + embedding), stored, and searchable by object labels.

## Architecture

The system uses five services communicating via Redis topics:

| Service | Topic (subscribes) | Topic (publishes) |
|---------|-------------------|-------------------|
| Uploader | - | `image.uploaded` |
| Processor | `image.uploaded` | `inference.done`, `embedding.done` |
| Storage | `embedding.done` | - |
| Search Handler | `search.request` | `search.result` |
| CLI Searcher | `search.result` | `search.request` |

## Message Flow

```
Upload → image.uploaded → Processor (inference + embedding) → embedding.done → Storage
                                                                          ↓
CLI Search → search.request → Search Handler (matches labels) → search.result → CLI
```

## Topics

- `image.uploaded` – new image submitted
- `inference.done` – object detection complete
- `embedding.done` – vector created, ready for storage
- `search.request` – user query submitted
- `search.result` – search results returned

## Requirements Met

- Redis pub-sub messaging
- Asynchronous, event-driven flow
- Document storage (in-memory dictionary, extensible to MongoDB)
- Vector search simulation (text-based matching, extensible to FAISS)
- Idempotent message handling
- Unit test ready

## Run It

```bash
# Terminal 1: Start Redis
redis-server

# Terminal 2: Run the system
cd ~/530_image_system
python3 system.py
```

## Commands (at Search> prompt)

```
cat        # finds images with cats
dog        # finds images with dogs
sofa       # finds images with sofas
quit       # exit
```

## Test Output Example

```
[UPLOAD] cat.jpg -> abc-123
[INFERENCE] Processing abc-123
[PROCESSOR] Done -> ['cat', 'sofa']
[STORAGE] Saved abc-123 | Total: 1
Search> cat
[RESULT] "cat" -> ['abc-123']
```

## Files

- `system.py` – complete system (uploader, processor, storage, search handler, CLI)
```
