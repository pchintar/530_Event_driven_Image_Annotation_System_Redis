# Redis configuration
REDIS_HOST = 'localhost'
REDIS_PORT = 6379

# Topics
TOPIC_IMAGE_UPLOAD = 'image.uploaded'
TOPIC_EMBEDDING = 'embedding.done'
TOPIC_SEARCH_REQUEST = 'search.request'
TOPIC_SEARCH_RESULT = 'search.result'
TOPIC_CORRECTION = 'annotation.corrected'
TOPIC_SHUTDOWN = 'system.shutdown'

# File paths (each service owns its own files)
STORAGE_FILE = 'annotations_db.json'
VECTOR_INDEX_FILE = 'vector_index.json'
PROCESSED_EVENTS_FILE = 'processed_events.json'
FAISS_INDEX_FILE = 'faiss_index.bin'
