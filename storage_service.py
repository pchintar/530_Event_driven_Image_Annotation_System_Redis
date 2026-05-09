#!/usr/bin/env python3
import redis
import json
import os
import sys
from config import *
from utils import utc_now

class StorageService:
    def __init__(self):
        self.r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)
        self.pubsub = self.r.pubsub()
        self.database = self.load_annotations()
    
    def load_annotations(self):
        if os.path.exists(STORAGE_FILE):
            with open(STORAGE_FILE, 'r') as f:
                data = json.load(f)
                return data.get('images', {})
        return {}
    
    def save_annotations(self):
        data = {'images': self.database, 'last_updated': utc_now()}
        with open(STORAGE_FILE, 'w') as f:
            json.dump(data, f, indent=2)
    
    def store_annotation(self, data):
        image_id = data['image_id']
        
        if image_id not in self.database:
            self.database[image_id] = {
                'image_id': image_id,
                'path': data['name'],
                'camera': 'cli',
                'source': 'user_upload',
                'model_version': 'sim-v1',
                'objects': [],
                'image_embedding': [],
                'review': {'status': 'pending', 'notes': []},
                'history': ['submitted']
            }
        
        self.database[image_id]['objects'] = data['objects']
        self.database[image_id]['image_embedding'] = data['image_embedding']
        self.database[image_id]['history'].append('annotated')
        self.save_annotations()
        
        print(f"[STORAGE] Saved annotation for {image_id}")
    
    def update_correction(self, data):
        image_id = data['image_id']
        idx = data['object_index']
        
        if image_id in self.database and idx < len(self.database[image_id]['objects']):
            old = self.database[image_id]['objects'][idx]['label']
            self.database[image_id]['objects'][idx]['label'] = data['new_label']
            self.database[image_id]['review']['status'] = 'corrected'
            self.database[image_id]['review']['notes'].append(
                f"{old} -> {data['new_label']} by {data.get('reviewer', 'user')}"
            )
            self.database[image_id]['history'].append('corrected')
            self.save_annotations()
            print(f"[STORAGE] Corrected {image_id}: {old} -> {data['new_label']}")
    
    def run(self):
        self.pubsub.subscribe(TOPIC_EMBEDDING, TOPIC_CORRECTION)
        print("[STORAGE] Service started. Listening for annotations and corrections...")
        
        for msg in self.pubsub.listen():
            if msg['type'] == 'message':
                try:
                    data = json.loads(msg['data'])
                    payload = data.get('payload', data)
                    
                    if 'objects' in payload:
                        self.store_annotation(payload)
                    elif 'new_label' in payload:
                        self.update_correction(payload)
                except Exception as e:
                    print(f"[STORAGE] Error: {e}")

if __name__ == '__main__':
    service = StorageService()
    service.run()
