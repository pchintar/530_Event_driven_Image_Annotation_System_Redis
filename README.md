# Event-Driven Image Annotation and Retrieval System

A system that simulates image uploads, object detection, and search using Redis pub-sub. No real images or AI for now — just message passing to demonstrate the architecture.

## How It Works

1. Script starts → automatically creates 2 fake images (`cat.jpg`, `dog.png`)
2. Processor "detects" objects in each image (simulated)
3. Storage saves the results
4. You search by keyword → system returns matching fake images

## Message Flow (Redis Topics)

```
Upload → image.uploaded → Processor → embedding.done → Storage
                              ↓
Search → search.request → Search Handler → search.result → You
```

## Run It

```bash
# Terminal 1
redis-server

# Terminal 2
python3 system.py
```

## Try It

When you see `Enter search term`, type either:
- `cat` → returns the cat image
- `dog` → returns the dog image
- `sofa` → returns the cat image (because cat.jpg had 'sofa' as an object)
- `ball` → returns the dog image

## Example Output

```
[1] UPLOAD: cat.jpg
[2] PROCESSOR: Analyzing cat.jpg
[3] PROCESSOR: Found objects -> ['cat', 'sofa']
[4] STORAGE: Saved (Total: 1 images)

Search> cat
RESULT: Found 1 image(s) matching 'cat'
```

## What This Demonstrates

- Redis pub-sub messaging
- Asynchronous event-driven architecture
- Simulated AI inference and embedding
- Search by object labels
- Unit tests included (`pytest test_system.py -v`)

## Files

- `system.py` – everything in one file
- `test_system.py` – unit tests
