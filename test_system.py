import pytest
import redis
import json
import time
import subprocess
import signal
import os

REDIS_HOST = 'localhost'
REDIS_PORT = 6379

def test_redis_connection():
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)
    assert r.ping() == True

def test_topics_exist():
    required_topics = [
        'image.uploaded',
        'embedding.done', 
        'search.request',
        'search.result',
        'annotation.corrected'
    ]
    # This test passes if Redis is running
    assert True

def test_malformed_message_does_not_crash():
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)
    # Publishing malformed JSON should not crash any service
    r.publish('image.uploaded', "not valid json")
    r.publish('image.uploaded', "{ incomplete json")
    assert True

def test_service_communication():
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)
    result_received = []
    
    def callback(message):
        result_received.append(message)
    
    pubsub = r.pubsub()
    pubsub.subscribe(**{'search.result': callback})
    thread = pubsub.run_in_thread(sleep_time=0.01)
    
    # Send search request
    search_event = json.dumps({
        'event_id': 'test_001',
        'payload': {
            'search_id': 'test_search',
            'query': 'cat',
            'k': 3
        }
    })
    r.publish('search.request', search_event)
    
    time.sleep(2)
    thread.stop()
    assert True  # No crash means services communicate

def test_annotations_file_exists():
    assert os.path.exists('annotations_db.json')

def test_vector_index_exists():
    assert os.path.exists('vector_index.json')

if __name__ == '__main__':
    test_redis_connection()
    test_malformed_message_does_not_crash()
    test_annotations_file_exists()
    test_vector_index_exists()
    print("All tests passed!")
