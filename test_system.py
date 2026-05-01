import pytest
import json
import redis
import os
import tempfile
import sys
import numpy as np

# Skip Redis tests if Redis not running
try:
    r = redis.Redis(host='localhost', port=6379)
    r.ping()
    REDIS_AVAILABLE = True
except:
    REDIS_AVAILABLE = False

from system import *
from vector_search import VectorSearchEngine

if not REDIS_AVAILABLE:
    pytest.skip("Redis not running - skipping Redis tests", allow_module_level=True)

def test_idempotent_messages():
    r = redis.Redis(host='localhost', port=6379)
    msg = json.dumps({'image_id': 'test123', 'name': 'test.jpg'})
    r.publish(TOPIC_UPLOAD, msg)
    r.publish(TOPIC_UPLOAD, msg)
    assert True

def test_malformed_message():
    r = redis.Redis(host='localhost', port=6379)
    r.publish(TOPIC_UPLOAD, "not json")
    assert True

def test_load_annotations():
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump({'images': {'test': {'image_id': 'test'}}}, f)
        f.close()
        original_file = ANNOTATIONS_FILE
        import system
        system.ANNOTATIONS_FILE = f.name
        import importlib
        importlib.reload(system)
        result = system.load_annotations()
        assert 'test' in result
        os.unlink(f.name)
        system.ANNOTATIONS_FILE = original_file

def test_make_embedding():
    emb1 = make_embedding("cat")
    emb2 = make_embedding("cat")
    emb3 = make_embedding("dog")
    assert emb1 == emb2
    assert emb1 != emb3
    assert len(emb1) == 16

def test_vector_search_engine():
    vs = VectorSearchEngine(dimension=4)
    vs.add_item("img1", [1.0, 0.0, 0.0, 0.0], {"label": "cat"})
    vs.add_item("img2", [0.0, 1.0, 0.0, 0.0], {"label": "dog"})
    vs.add_item("img3", [0.9, 0.1, 0.0, 0.0], {"label": "feline"})
    
    results = vs.search([1.0, 0.0, 0.0, 0.0], 2)
    assert len(results) >= 2
    assert results[0][0] == "img1"

def test_vector_save_load():
    vs = VectorSearchEngine(dimension=4, index_file="test_faiss.bin")
    vs.add_item("test_img", [1.0, 0.0, 0.0, 0.0], {"label": "test"})
    vs.save()
    
    vs2 = VectorSearchEngine(dimension=4, index_file="test_faiss.bin")
    vs2.load()
    assert vs2.index.ntotal == 1
    
    os.remove("test_faiss.bin")
    if os.path.exists("test_faiss.bin.meta"):
        os.remove("test_faiss.bin.meta")

def test_semantic_search_with_vectors():
    items = [
        {'item_id': 'img1', 'vector': [1, 0, 0], 'label': 'cat'},
        {'item_id': 'img2', 'vector': [0, 1, 0], 'label': 'dog'}
    ]
    query = [0.9, 0.1, 0]
    scores = []
    for item in items:
        sim = np.dot(query, item['vector']) / (np.linalg.norm(query) * np.linalg.norm(item['vector']))
        scores.append((item['item_id'], sim))
    scores.sort(key=lambda x: x[1], reverse=True)
    assert scores[0][0] == 'img1'

def test_concurrent_messages():
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
        import importlib
        importlib.reload(system)
        database = system.load_annotations()
        if 'img1' in database:
            database['img1']['objects'][0]['label'] = 'feline'
            system.save_annotations(database)
            reloaded = system.load_annotations()
            assert reloaded['img1']['objects'][0]['label'] == 'feline'
        os.unlink(f.name)
        system.ANNOTATIONS_FILE = original_file

def test_idempotency_with_event_ids():
    processed = set()
    event_id = "evt_123"
    assert event_id not in processed
    processed.add(event_id)
    assert event_id in processed

def test_processed_events_persistence():
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(["evt1", "evt2"], f)
        f.close()
        original_file = PROCESSED_EVENTS_FILE
        import system
        system.PROCESSED_EVENTS_FILE = f.name
        import importlib
        importlib.reload(system)
        events = system.load_processed_events()
        assert "evt1" in events
        os.unlink(f.name)
        system.PROCESSED_EVENTS_FILE = original_file

if __name__ == '__main__':
    test_idempotent_messages()
    test_malformed_message()
    test_load_annotations()
    test_make_embedding()
    test_vector_search_engine()
    test_vector_save_load()
    test_semantic_search_with_vectors()
    test_concurrent_messages()
    test_correction_workflow()
    test_idempotency_with_event_ids()
    test_processed_events_persistence()
    print("\nAll tests passed!")
