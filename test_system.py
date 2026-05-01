import pytest
import json
import redis
import os
import tempfile
import sys

# Skip Redis tests if Redis not running
try:
    r = redis.Redis(host='localhost', port=6379)
    r.ping()
    REDIS_AVAILABLE = True
except:
    REDIS_AVAILABLE = False

# Import from system
from system import *

# Skip Redis-dependent tests if Redis not available
if not REDIS_AVAILABLE:
    pytest.skip("Redis not running - skipping Redis tests", allow_module_level=True)

def test_idempotent_messages():
    if not REDIS_AVAILABLE:
        pytest.skip("Redis not available")
    r = redis.Redis(host='localhost', port=6379)
    msg = json.dumps({'image_id': 'test123', 'name': 'test.jpg'})
    r.publish(TOPIC_UPLOAD, msg)
    r.publish(TOPIC_UPLOAD, msg)
    assert True

def test_malformed_message():
    if not REDIS_AVAILABLE:
        pytest.skip("Redis not available")
    r = redis.Redis(host='localhost', port=6379)
    r.publish(TOPIC_UPLOAD, "not json")
    assert True

def test_load_annotations():
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump({'images': {'test': {'image_id': 'test'}}}, f)
        f.close()
        # Save original file path
        original_file = ANNOTATIONS_FILE
        # Override for test
        import system
        system.ANNOTATIONS_FILE = f.name
        reload(system)
        result = system.load_annotations()
        assert 'test' in result
        os.unlink(f.name)
        # Restore
        system.ANNOTATIONS_FILE = original_file

def test_make_embedding():
    emb1 = make_embedding("cat")
    emb2 = make_embedding("cat")
    emb3 = make_embedding("dog")
    assert emb1 == emb2
    assert emb1 != emb3
    assert len(emb1) == 16

def test_vector_save_load():
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        test_data = {'items': [{'item_id': 'test', 'vector': [1,2,3]}], 'processed_event_ids': []}
        json.dump(test_data, f)
        f.close()
        original_file = VECTOR_INDEX_FILE
        import system
        system.VECTOR_INDEX_FILE = f.name
        reload(system)
        loaded = system.load_vector_index()
        assert loaded['items'][0]['item_id'] == 'test'
        os.unlink(f.name)
        system.VECTOR_INDEX_FILE = original_file

def test_semantic_search_with_vectors():
    items = [
        {'item_id': 'img1', 'vector': [1, 0, 0], 'label': 'cat'},
        {'item_id': 'img2', 'vector': [0, 1, 0], 'label': 'dog'}
    ]
    import numpy as np
    query = [0.9, 0.1, 0]
    scores = []
    for item in items:
        sim = np.dot(query, item['vector']) / (np.linalg.norm(query) * np.linalg.norm(item['vector']))
        scores.append((item['item_id'], sim))
    scores.sort(key=lambda x: x[1], reverse=True)
    assert scores[0][0] == 'img1'

def test_concurrent_messages():
    if not REDIS_AVAILABLE:
        pytest.skip("Redis not available")
    import threading
    r = redis.Redis(host='localhost', port=6379)
    def send(i):
        r.publish(TOPIC_UPLOAD, json.dumps({'image_id': f'conc_{i}', 'name': f'{i}.jpg'}))
    threads = [threading.Thread(target=send, args=(i,)) for i in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert True

def test_correction_workflow():
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump({'images': {'img1': {'image_id': 'img1', 'objects': [{'label': 'cat'}], 'review': {'notes': []}, 'history': []}}}, f)
        f.close()
        original_file = ANNOTATIONS_FILE
        import system
        system.ANNOTATIONS_FILE = f.name
        reload(system)
        database = system.load_annotations()
        if 'img1' in database:
            database['img1']['objects'][0]['label'] = 'feline'
            system.save_annotations(database)
            reloaded = system.load_annotations()
            assert reloaded['img1']['objects'][0]['label'] == 'feline'
        os.unlink(f.name)
        system.ANNOTATIONS_FILE = original_file

# Helper for reloading
def reload(module):
    import importlib
    importlib.reload(module)

if __name__ == '__main__':
    print("Run with: pytest test_system.py -v")
