import hashlib
import json
import uuid
from datetime import datetime

def make_embedding(text, dim=16):
    """Deterministic embedding generator"""
    hash_val = hashlib.md5(text.encode()).digest()
    return [((hash_val[i % len(hash_val)]) / 128.0) - 1.0 for i in range(dim)]

def utc_now():
    return datetime.utcnow().isoformat()

def generate_event_id():
    return f"evt_{uuid.uuid4().hex[:12]}"
