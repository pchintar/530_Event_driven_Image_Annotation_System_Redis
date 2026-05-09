#!/usr/bin/env python3
import redis
import json
import os
import sys
import numpy as np
import faiss
from config import *
from utils import make_embedding, generate_event_id, utc_now

class SearchService:
    def __init__(self, dimension=16):
        self.r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)
        self.pubsub = self.r.pubsub()
        self.dimension = dimension
        self.reload_faiss()
    
    def reload_faiss(self):
        """Reload FAISS index from disk on each search"""
        if os.path.exists(FAISS_INDEX_FILE):
            self.index = faiss.read_index(FAISS_INDEX_FILE)
        else:
            self.index = faiss.IndexFlatIP(self.dimension)
        
        self.image_ids = []
        self.metadata_list = []
        
        if os.path.exists(FAISS_INDEX_FILE + ".meta"):
            with open(FAISS_INDEX_FILE + ".meta", 'r') as f:
                data = json.load(f)
                self.image_ids = data.get('image_ids', [])
                self.metadata_list = data.get('metadata_list', [])
    
    def vector_search(self, query_vector, k=5):
        self.reload_faiss()  # Reload to get latest embeddings
        
        if self.index.ntotal == 0:
            return []
        
        query_array = np.array([query_vector], dtype=np.float32)
        faiss.normalize_L2(query_array)
        
        distances, indices = self.index.search(query_array, min(k, self.index.ntotal))
        
        results = []
        for i, idx in enumerate(indices[0]):
            if idx >= 0 and idx < len(self.image_ids):
                results.append({
                    'item_id': self.image_ids[idx],
                    'score': float(distances[0][i]),
                    'metadata': self.metadata_list[idx] if idx < len(self.metadata_list) else {}
                })
        return results
    
    def handle_search(self, search_id, query, k=5):
        query_vector = make_embedding(query)
        results = self.vector_search(query_vector, k)
        
        # Filter to image-level results only
        image_matches = []
        for r in results:
            if r['metadata'].get('item_type') == 'image':
                image_matches.append(r['metadata'].get('image_id', r['item_id']))
        
        image_matches = list(dict.fromkeys(image_matches))
        
        response = {
            'event_id': generate_event_id(),
            'type': 'search.completed',
            'timestamp': utc_now(),
            'payload': {
                'search_id': search_id,
                'query': query,
                'matches': len(image_matches),
                'image_ids': image_matches[:k],
                'search_type': 'vector'
            }
        }
        
        self.r.publish(TOPIC_SEARCH_RESULT, json.dumps(response))
        print(f"[SEARCH] '{query}' -> {len(image_matches)} matches (total index size: {self.index.ntotal})")
    
    def run(self):
        self.pubsub.subscribe(TOPIC_SEARCH_REQUEST)
        print("[SEARCH] Service started. Listening for search requests...")
        
        for msg in self.pubsub.listen():
            if msg['type'] == 'message':
                try:
                    data = json.loads(msg['data'])
                    payload = data.get('payload', data)
                    self.handle_search(
                        payload['search_id'],
                        payload['query'],
                        payload.get('k', 5)
                    )
                except Exception as e:
                    print(f"[SEARCH] Error: {e}")

if __name__ == '__main__':
    service = SearchService()
    service.run()
