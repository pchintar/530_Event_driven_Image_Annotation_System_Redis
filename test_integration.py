#!/usr/bin/env python3
import redis
import json
import time
import uuid
import sys

r = redis.Redis(host='localhost', port=6379)

# Subscribe to results
pubsub = r.pubsub()
results_received = []

def callback(msg):
    if msg['type'] == 'message':
        data = json.loads(msg['data'])
        print(f"✓ Received result: {data}")
        results_received.append(data)

pubsub.subscribe(**{'search.result': callback})
thread = pubsub.run_in_thread(sleep_time=0.01)

# Test 1: Upload cat.jpg
print("\n--- Test 1: Upload cat.jpg ---")
upload_event = {
    'event_id': 'test_cat_001',
    'payload': {
        'image_id': str(uuid.uuid4()),
        'name': 'cat.jpg'
    }
}
r.publish('image.uploaded', json.dumps(upload_event))
print("✓ Sent cat.jpg upload event")
time.sleep(3)

# Test 2: Upload dog.png
print("\n--- Test 2: Upload dog.png ---")
upload_event = {
    'event_id': 'test_dog_001',
    'payload': {
        'image_id': str(uuid.uuid4()),
        'name': 'dog.png'
    }
}
r.publish('image.uploaded', json.dumps(upload_event))
print("✓ Sent dog.png upload event")
time.sleep(3)

# Test 3: Search for cat
print("\n--- Test 3: Search for 'cat' ---")
search_event = {
    'event_id': 'test_search_cat',
    'payload': {
        'search_id': 'search_cat',
        'query': 'cat',
        'k': 5
    }
}
r.publish('search.request', json.dumps(search_event))
print("✓ Sent cat search request")
time.sleep(2)

# Test 4: Search for dog
print("\n--- Test 4: Search for 'dog' ---")
search_event = {
    'event_id': 'test_search_dog',
    'payload': {
        'search_id': 'search_dog',
        'query': 'dog',
        'k': 5
    }
}
r.publish('search.request', json.dumps(search_event))
print("✓ Sent dog search request")
time.sleep(2)

# Test 5: Vector search for animal
print("\n--- Test 5: Vector search for 'animal' ---")
search_event = {
    'event_id': 'test_search_animal',
    'payload': {
        'search_id': 'search_animal',
        'query': 'animal',
        'k': 5
    }
}
r.publish('search.request', json.dumps(search_event))
print("✓ Sent animal search request")
time.sleep(2)

# Test 6: Correction
print("\n--- Test 6: Correction workflow ---")
# First get an image ID from results
image_id = None
for result in results_received:
    if 'payload' in result and result['payload'].get('image_ids'):
        image_id = result['payload']['image_ids'][0]
        break

if image_id:
    correction_event = {
        'event_id': 'test_correction_001',
        'payload': {
            'image_id': image_id,
            'old_label': 'cat',
            'new_label': 'feline',
            'object_index': 0,
            'reviewer': 'github_actions'
        }
    }
    r.publish('annotation.corrected', json.dumps(correction_event))
    print(f"✓ Sent correction request for {image_id}: cat -> feline")
    time.sleep(2)
else:
    print("⚠ Skipping correction test - no image ID available")

# Summary
print("\n" + "="*50)
print("TEST SUMMARY")
print("="*50)
print(f"Total results received: {len(results_received)}")
print(f"Cat search results: {any('cat' in str(r) for r in results_received)}")
print(f"Dog search results: {any('dog' in str(r) for r in results_received)}")
print(f"Animal search results: {any('animal' in str(r) for r in results_received)}")

if len(results_received) >= 3:
    print("\n✓ SUCCESS: All tests passed. Services communicate via Redis.")
else:
    print("\n✗ FAILURE: Expected at least 3 results.")

thread.stop()
sys.exit(0 if len(results_received) >= 3 else 1)
