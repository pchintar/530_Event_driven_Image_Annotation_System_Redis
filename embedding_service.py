#!/usr/bin/env python3
import redis
import json
import os
import sys
import numpy as np
import faiss
from config import *
from utils import generate_event_id, utc_now

class EmbeddingService:
    def __init__(self, dimension=16):
        self.r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)
        self.pubsub = self.r.pubsub()
        self.dimension = dimension
        self.index = faiss.IndexFlatIP(dimension)
        self.image_ids = []
        self.metadata_list = []
        self.vector_index = self.load_vector_index()
        self.load_faiss()
    
    def load_vector_index(self):
        if os.path.exists(VECTOR_INDEX_FILE):
            with open(VECTOR_INDEX_FILE, 'r') as f:
                return json.load(f)
        return {'items': [], 'processed_event_ids': []}
    
    def save_vector_index(self):
        with open(VECTOR_INDEX_FILE, 'w') as f:
            json.dump(self.vector_index, f, indent=2)
    
    def load_faiss(self):
        if os.path.exists(FAISS_INDEX_FILE):
            self.index = faiss.read_index(FAISS_INDEX_FILE)
        if os.path.exists(FAISS_INDEX_FILE + ".meta"):
            with open(FAISS_INDEX_FILE + ".meta", 'r') as f:
                data = json.load(f)
                self.image_ids = data['image_ids']
                self.metadata_list = data['metadata_list']
    
    def save_faiss(self):
        faiss.write_index(self.index, FAISS_INDEX_FILE)
        with open(FAISS_INDEX_FILE + ".meta", 'w') as f:
            json.dump({
                'image_ids': self.image_ids,
                'metadata_list': self.metadata_list
            }, f)
    
    def add_to_index(self, item_id, vector, metadata):
        vec_array = np.array([vector], dtype=np.float32)
        faiss.normalize_L2(vec_array)
        self.index.add(vec_array)
        self.image_ids.append(item_id)
        self.metadata_list.append(metadata)
        
        # Update vector_index.json
        self.vector_index['items'].append({
            'item_id': item_id,
            'vector': vector,
            **metadata
        })
        self.save_vector_index()
        self.save_faiss()
    
    def process_embedding(self, data):
        image_id = data['image_id']
        
        # Add image embedding
        image_item_id = f"image::{image_id}"
        self.add_to_index(image_item_id, data['image_embedding'], {
            'item_type': 'image',
            'image_id': image_id,
            'label': image_id
        })
        
        # Add object embeddings
        for idx, obj in enumerate(data['objects']):
            object_item_id = f"object::{image_id}::{idx}"
            self.add_to_index(object_item_id, obj['embedding'], {
                'item_type': 'object',
                'image_id': image_id,
                'label': obj['label'],
                'bbox': obj['bbox'],
                'conf': obj['conf']
            })
        
        print(f"[EMBEDDING] Indexed {len(data['objects'])} objects + 1 image for {image_id}")
    
    def run(self):
        self.pubsub.subscribe(TOPIC_EMBEDDING)
        print("[EMBEDDING] Service started. Listening for embeddings to index...")
        
        for msg in self.pubsub.listen():
            if msg['type'] == 'message':
                try:
                    data = json.loads(msg['data'])
                    payload = data.get('payload', data)
                    self.process_embedding(payload)
                except Exception as e:
                    print(f"[EMBEDDING] Error: {e}")

if __name__ == '__main__':
    service = EmbeddingService()
    service.run()
