#!/usr/bin/env python3
import redis
import json
import time
import os
import sys
from config import *
from utils import make_embedding, generate_event_id, utc_now

class ProcessorService:
    def __init__(self):
        self.r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)
        self.pubsub = self.r.pubsub()
        self.processed_events = self.load_processed_events()
    
    def load_processed_events(self):
        if os.path.exists(PROCESSED_EVENTS_FILE):
            with open(PROCESSED_EVENTS_FILE, 'r') as f:
                return set(json.load(f))
        return set()
    
    def save_processed_events(self):
        with open(PROCESSED_EVENTS_FILE, 'w') as f:
            json.dump(list(self.processed_events), f)
    
    def process_image(self, event_id, data):
        if event_id in self.processed_events:
            print(f"[PROCESSOR] Skipping duplicate event {event_id}")
            return
        
        print(f"[PROCESSOR] Analyzing {data['name']}")
        time.sleep(0.5)
        
        name_lower = data['name'].lower()
        objects = []
        if 'cat' in name_lower:
            objects = [{'label': 'cat', 'conf': 0.95, 'bbox': [100,100,200,200]},
                      {'label': 'sofa', 'conf': 0.72, 'bbox': [50,300,300,250]}]
        elif 'dog' in name_lower:
            objects = [{'label': 'dog', 'conf': 0.93, 'bbox': [120,80,180,220]},
                      {'label': 'ball', 'conf': 0.88, 'bbox': [250,200,50,50]}]
        else:
            objects = [{'label': 'unknown', 'conf': 0.80, 'bbox': [0,0,100,100]}]
        
        full_objects = []
        for idx, obj in enumerate(objects):
            full_objects.append({
                'label': obj['label'],
                'bbox': obj['bbox'],
                'conf': obj['conf'],
                'embedding': make_embedding(f"{data['image_id']}_{obj['label']}"),
                'attributes': {'source_hint': data['name']}
            })
        
        image_embedding = make_embedding(data['image_id'])
        
        # Publish inference result
        inference_event = {
            'event_id': generate_event_id(),
            'type': 'inference.completed',
            'timestamp': utc_now(),
            'payload': {
                'image_id': data['image_id'],
                'name': data['name'],
                'objects': full_objects,
                'image_embedding': image_embedding
            }
        }
        
        self.r.publish(TOPIC_EMBEDDING, json.dumps(inference_event))
        self.processed_events.add(event_id)
        self.save_processed_events()
        print(f"[PROCESSOR] Found objects -> {[o['label'] for o in objects]}")
    
    def run(self):
        self.pubsub.subscribe(TOPIC_IMAGE_UPLOAD)
        print("[PROCESSOR] Service started. Listening for uploads...")
        
        for msg in self.pubsub.listen():
            if msg['type'] == 'message':
                try:
                    data = json.loads(msg['data'])
                    event_id = data.get('event_id', generate_event_id())
                    self.process_image(event_id, data.get('payload', data))
                except Exception as e:
                    print(f"[PROCESSOR] Error: {e}")

if __name__ == '__main__':
    service = ProcessorService()
    service.run()
