#!/usr/bin/env python3
import redis
import json
import time
import uuid

r = redis.Redis(host='localhost', port=6379)

# Subscribe to results
pubsub = r.pubsub()
result_received = []

def callback(msg):
    if msg['type'] == 'message':
        data = json.loads(msg['data'])
        print(f"✓ Received result: {data}")
        result_received.append(data)

pubsub.subscribe(**{'search.result': callback})
thread = pubsub.run_in_thread(sleep_time=0.01)

# Send upload
upload_event = {
    'event_id': 'integration_test_001',
    'payload': {
        'image_id': str(uuid.uuid4()),
        'name': 'integration_test.jpg'
    }
}
r.publish('image.uploaded', json.dumps(upload_event))
print("✓ Sent upload event")

time.sleep(3)  # Wait for processing

# Send search
search_event = {
    'event_id': 'integration_test_002',
    'payload': {
        'search_id': 'test_search',
        'query': 'cat',
        'k': 3
    }
}
r.publish('search.request', json.dumps(search_event))
print("✓ Sent search request")

time.sleep(3)
thread.stop()

if result_received:
    print(f"\n✓ SUCCESS: Services communicate via Redis. Received {len(result_received)} results.")
else:
    print("\n✗ FAILURE: No results received. Check if services are running.")
