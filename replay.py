#!/usr/bin/env python3
import redis
import json
import time
import sys
import os

REDIS_HOST = 'localhost'
REDIS_PORT = 6379

def replay_events(event_file='sample_events.json', delay=0.1):
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)
    
    if not os.path.exists(event_file):
        print(f"Error: {event_file} not found")
        return False
    
    with open(event_file, 'r') as f:
        events = json.load(f)
    
    print(f"\n{'='*50}")
    print(f"REPLAYING {len(events)} EVENTS")
    print(f"{'='*50}\n")
    
    for i, event in enumerate(events):
        if event['type'] == 'publish':
            payload = json.dumps(event['payload'])
            print(f"[{i+1}] {event['topic']}")
            print(f"    Payload: {event['payload'].get('path', event['payload'].get('image_id'))}")
            r.publish(event['topic'], payload)
            time.sleep(delay)
    
    print(f"\n✅ Replay complete!")
    return True

if __name__ == '__main__':
    delay = float(sys.argv[2]) if len(sys.argv) > 2 else 0.1
    replay_events('sample_events.json', delay)
