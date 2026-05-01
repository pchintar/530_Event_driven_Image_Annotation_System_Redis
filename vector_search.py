import faiss
import numpy as np
import json
import os
from typing import List, Tuple, Dict, Any

class VectorSearchEngine:
    def __init__(self, dimension=16, index_file="faiss_index.bin"):
        self.dimension = dimension
        self.index_file = index_file
        self.index = faiss.IndexFlatIP(dimension)
        self.image_ids = []
        self.metadata_list = []
        
        if os.path.exists(index_file):
            self.load()
    
    def add_item(self, item_id: str, vector: List[float], metadata: Dict[str, Any]):
        vec_array = np.array([vector], dtype=np.float32)
        faiss.normalize_L2(vec_array)
        
        self.index.add(vec_array)
        self.image_ids.append(item_id)
        self.metadata_list.append(metadata)
    
    def search(self, query_vector: List[float], k: int = 5) -> List[Tuple[str, float, Dict]]:
        if self.index.ntotal == 0:
            return []
        
        query_array = np.array([query_vector], dtype=np.float32)
        faiss.normalize_L2(query_array)
        
        distances, indices = self.index.search(query_array, min(k, self.index.ntotal))
        
        results = []
        for i, idx in enumerate(indices[0]):
            if idx >= 0:
                results.append((
                    self.image_ids[idx],
                    float(distances[0][i]),
                    self.metadata_list[idx]
                ))
        return results
    
    def save(self):
        faiss.write_index(self.index, self.index_file)
        with open(self.index_file + ".meta", 'w') as f:
            json.dump({
                'image_ids': self.image_ids,
                'metadata_list': self.metadata_list
            }, f)
    
    def load(self):
        if os.path.exists(self.index_file):
            self.index = faiss.read_index(self.index_file)
        if os.path.exists(self.index_file + ".meta"):
            with open(self.index_file + ".meta", 'r') as f:
                data = json.load(f)
                self.image_ids = data['image_ids']
                self.metadata_list = data['metadata_list']
