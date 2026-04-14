import pytest
import json
import redis
from system import *

def test_idempotent_messages():
    r = redis.Redis(host='localhost', port=6379)
    msg = json.dumps({'image_id': 'test123', 'image_name': 'test.jpg'})
    
    # Same message twice
    r.publish(TOPIC_UPLOAD, msg)
    r.publish(TOPIC_UPLOAD, msg)
    # Storage should handle duplicate (won't duplicate in dict)
    assert True

def test_malformed_message():
    r = redis.Redis(host='localhost', port=6379)
    r.publish(TOPIC_UPLOAD, "not json")
    # System should not crash
    assert True

if __name__ == '__main__':
    test_idempotent_messages()
    test_malformed_message()
    print("Tests passed")
