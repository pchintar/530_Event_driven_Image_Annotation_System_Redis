import redis
import json
import time
import uuid
import threading
import os
import hashlib
import numpy as np
from vector_search import VectorSearchEngine

# Config
REDIS_HOST = 'localhost'
REDIS_PORT = 6379

# Topics
TOPIC_UPLOAD = 'image.uploaded'
TOPIC_EMBEDDING = 'embedding.done'
TOPIC_SEARCH = 'search.request'
TOPIC_RESULT = 'search.result'
TOPIC_CORRECTION = 'annotation.corrected'

# JSON file paths
ANNOTATIONS_FILE = 'annotations_db.json'
VECTOR_INDEX_FILE = 'vector_index.json'
PROCESSED_EVENTS_FILE = 'processed_events.json'

r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)

def load_annotations():
    if os.path.exists(ANNOTATIONS_FILE):
        with open(ANNOTATIONS_FILE, 'r') as f:
            data = json.load(f)
            return data.get('images', {})
    return {}

def save_annotations(images_dict):
    data = {'images': images_dict, 'processed_event_ids': []}
    with open(ANNOTATIONS_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def load_vector_index():
    if os.path.exists(VECTOR_INDEX_FILE):
        with open(VECTOR_INDEX_FILE, 'r') as f:
            return json.load(f)
    return {'items': [], 'processed_event_ids': []}

def save_vector_index(index_data):
    with open(VECTOR_INDEX_FILE, 'w') as f:
        json.dump(index_data, f, indent=2)

def load_processed_events():
    if os.path.exists(PROCESSED_EVENTS_FILE):
        with open(PROCESSED_EVENTS_FILE, 'r') as f:
            return set(json.load(f))
    return set()

def save_processed_events():
    with open(PROCESSED_EVENTS_FILE, 'w') as f:
        json.dump(list(processed_events), f)

def make_embedding(text, dim=16):
    """Deterministic embedding generator"""
    hash_val = hashlib.md5(text.encode()).digest()
    return [((hash_val[i % len(hash_val)]) / 128.0) - 1.0 for i in range(dim)]

# Load data
database = load_annotations()
vector_index = load_vector_index()
processed_events = load_processed_events()

# Initialize FAISS vector search
vector_search = VectorSearchEngine(dimension=16)

# Rebuild FAISS index from vector_index on startup
for item in vector_index.get('items', []):
    vector_search.add_item(
        item['item_id'],
        item['vector'],
        {'item_type': item['item_type'], 'label': item.get('label', ''), 'image_id': item['image_id']}
    )

def upload_image(image_name):
    image_id = str(uuid.uuid4())
    if image_id not in database:
        database[image_id] = {
            'image_id': image_id,
            'path': image_name,
            'camera': 'cli',
            'source': 'user_upload',
            'model_version': 'sim-v1',
            'objects': [],
            'image_embedding': [],
            'review': {'status': 'pending', 'notes': []},
            'history': ['submitted']
        }
        save_annotations(database)
    r.publish(TOPIC_UPLOAD, json.dumps({'image_id': image_id, 'name': image_name}))
    print(f"\n[1] UPLOAD: {image_name} (ID: {image_id[:8]}...)")

def processor():
    pubsub = r.pubsub()
    pubsub.subscribe(TOPIC_UPLOAD)
    for msg in pubsub.listen():
        if msg['type'] == 'message':
            event_id = msg.get('pattern', str(uuid.uuid4()))
            if event_id in processed_events:
                print(f"[SKIP] Duplicate event {event_id}")
                continue
            
            data = json.loads(msg['data'])
            print(f"\n[2] PROCESSOR: Analyzing {data['name']}")
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
            
            if data['image_id'] in database:
                database[data['image_id']]['objects'] = full_objects
                database[data['image_id']]['image_embedding'] = image_embedding
                database[data['image_id']]['history'].append('annotated')
                save_annotations(database)
            
            for idx, obj in enumerate(full_objects):
                item_id = f"object::{data['image_id']}::{idx}"
                if not any(i['item_id'] == item_id for i in vector_index['items']):
                    vector_index['items'].append({
                        'item_id': item_id,
                        'item_type': 'object',
                        'image_id': data['image_id'],
                        'label': obj['label'],
                        'bbox': obj['bbox'],
                        'conf': obj['conf'],
                        'vector': obj['embedding']
                    })
                    vector_search.add_item(item_id, obj['embedding'], {'item_type': 'object', 'label': obj['label'], 'image_id': data['image_id']})
            
            image_item_id = f"image::{data['image_id']}"
            if not any(i['item_id'] == image_item_id for i in vector_index['items']):
                vector_index['items'].append({
                    'item_id': image_item_id,
                    'item_type': 'image',
                    'image_id': data['image_id'],
                    'label': data['image_id'],
                    'vector': image_embedding
                })
                vector_search.add_item(image_item_id, image_embedding, {'item_type': 'image', 'label': data['image_id'], 'image_id': data['image_id']})
            
            save_vector_index(vector_index)
            vector_search.save()
            
            processed_events.add(event_id)
            save_processed_events()
            
            r.publish(TOPIC_EMBEDDING, json.dumps({'image_id': data['image_id'], 'objects': [o['label'] for o in objects]}))
            print(f"[3] PROCESSOR: Found objects -> {[o['label'] for o in objects]}")

def storage():
    pubsub = r.pubsub()
    pubsub.subscribe(TOPIC_EMBEDDING)
    for msg in pubsub.listen():
        if msg['type'] == 'message':
            print(f"[4] STORAGE: Updated {ANNOTATIONS_FILE}, {VECTOR_INDEX_FILE}, and FAISS index")

def search_by_image(image_id: str, k: int = 5):
    """Find images similar to a given image"""
    # Get the image's vector from vector_index
    image_vector = None
    for item in vector_index.get('items', []):
        if item['item_id'] == f"image::{image_id}":
            image_vector = item['vector']
            break
    
    if image_vector is None:
        print(f"  Image {image_id} has no embedding in vector index")
        return []
    
    # Search using FAISS
    results = vector_search.search(image_vector, k + 1)
    similar_images = []
    for item_id, score, metadata in results:
        if metadata.get('item_type') == 'image' and metadata.get('image_id') != image_id:
            similar_images.append((metadata.get('image_id'), score))
    
    return similar_images[:k]

def search_handler():
    pubsub = r.pubsub()
    pubsub.subscribe(TOPIC_SEARCH)
    for msg in pubsub.listen():
        if msg['type'] == 'message':
            data = json.loads(msg['data'])
            query = data['query'].lower()
            mode = data.get('mode', 'keyword')
            
            if mode == 'vector' or data.get('use_vector', False):
                query_vector = make_embedding(query)
                results = vector_search.search(query_vector, k=data.get('k', 5))
                matches = []
                for item_id, score, metadata in results:
                    if metadata.get('item_type') == 'image':
                        matches.append(metadata.get('image_id', item_id))
                matches = list(dict.fromkeys(matches))
                print(f"[5] VECTOR SEARCH: '{query}' -> {len(matches)} matches")
                r.publish(TOPIC_RESULT, json.dumps({
                    'search_id': data['search_id'],
                    'query': query,
                    'matches': len(matches),
                    'image_ids': matches[:data.get('k', 5)],
                    'search_type': 'vector'
                }))
            else:
                matches = []
                for img_id, img_data in database.items():
                    object_labels = [obj['label'].lower() for obj in img_data.get('objects', [])]
                    if query in ' '.join(object_labels):
                        matches.append(img_id)
                r.publish(TOPIC_RESULT, json.dumps({
                    'search_id': data['search_id'],
                    'query': query,
                    'matches': len(matches),
                    'image_ids': matches,
                    'search_type': 'keyword'
                }))
                print(f"[5] KEYWORD SEARCH: '{query}' -> {len(matches)} matches")


def correction_handler():
    pubsub = r.pubsub()
    pubsub.subscribe(TOPIC_CORRECTION)
    for msg in pubsub.listen():
        if msg['type'] == 'message':
            data = json.loads(msg['data'])
            image_id = data['image_id']
            if image_id in database:
                objects = database[image_id].get('objects', [])
                idx = data['object_index']
                if idx < len(objects):
                    old = objects[idx]['label']
                    objects[idx]['label'] = data['new_label']
                    database[image_id]['objects'] = objects
                    database[image_id]['review']['status'] = 'corrected'
                    database[image_id]['review']['notes'].append(f"{old} -> {data['new_label']} by {data.get('reviewer', 'user')}")
                    database[image_id]['history'].append('corrected')
                    save_annotations(database)
                    
                    for item in vector_index['items']:
                        if item['item_id'] == f"object::{image_id}::{idx}":
                            item['label'] = data['new_label']
                            item['vector'] = make_embedding(f"{image_id}_{data['new_label']}")
                            break
                    
                    # Update FAISS index - remove old and add new
                    old_item_id = f"object::{image_id}::{idx}"
                    new_vector = make_embedding(f"{image_id}_{data['new_label']}")
                    
                    # Find and update in FAISS by rebuilding (simpler approach)
                    # Since FAISS doesn't support direct update, we'll rebuild the index
                    global vector_search
                    new_search = VectorSearchEngine(dimension=16)
                    for item in vector_index['items']:
                        new_search.add_item(
                            item['item_id'],
                            item['vector'],
                            {'item_type': item['item_type'], 'label': item.get('label', ''), 'image_id': item['image_id']}
                        )
                    vector_search = new_search
                    vector_search.save()
                    
                    save_vector_index(vector_index)
                    print(f"\n[6] CORRECTED: {image_id} - '{old}' → '{data['new_label']}'\n")


def searcher():
    pubsub = r.pubsub()
    pubsub.subscribe(TOPIC_RESULT)
    
    def listen():
        for msg in pubsub.listen():
            if msg['type'] == 'message':
                data = json.loads(msg['data'])
                print(f"\n{'='*50}")
                print(f"RESULT ({data.get('search_type', 'keyword')}): Found {data['matches']} image(s) matching '{data['query']}'")
                if data['matches'] > 0:
                    print(f"Image IDs: {data['image_ids']}")
                print(f"{'='*50}")
                print("\n[search] term | [vector] term | [similar] image_id | [correct] | [quit]: ", end='', flush=True)
    
    threading.Thread(target=listen, daemon=True).start()
    
    print("[search] term | [vector] term | [similar] image_id | [correct] | [quit]: ", end='', flush=True)
    
    while True:
        try:
            cmd = input().strip()
            if cmd == 'quit':
                break
            elif cmd == 'correct':
                print("Enter correction details:")
                img_id = input("  Image ID: ").strip()
                old = input("  Old label: ").strip()
                new = input("  New label: ").strip()
                idx = int(input("  Object index: ").strip())
                r.publish(TOPIC_CORRECTION, json.dumps({
                    'image_id': img_id, 
                    'old_label': old, 
                    'new_label': new, 
                    'object_index': idx, 
                    'reviewer': 'cli_user'
                }))
                print("[search] term | [vector] term | [similar] image_id | [correct] | [quit]: ", end='', flush=True)
            elif cmd.startswith('vector '):
                query_text = cmd[7:]
                r.publish(TOPIC_SEARCH, json.dumps({
                    'search_id': str(uuid.uuid4()), 
                    'query': query_text,
                    'mode': 'vector',
                    'use_vector': True,
                    'k': 5
                }))
            elif cmd.startswith('similar '):
                image_id = cmd[8:]
                results = search_by_image(image_id, 5)
                print(f"\n{'='*50}")
                print(f"IMAGES SIMILAR TO {image_id}:")
                if results:
                    for img_id, score in results:
                        print(f"  {img_id} (similarity: {score:.4f})")
                else:
                    print(f"  No similar images found for {image_id}")
                print(f"{'='*50}")
                print("[search] term | [vector] term | [similar] image_id | [correct] | [quit]: ", end='', flush=True)
            elif cmd:
                r.publish(TOPIC_SEARCH, json.dumps({
                    'search_id': str(uuid.uuid4()), 
                    'query': cmd,
                    'mode': 'keyword'
                }))
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")

def replay_events(event_file='sample_events.json'):
    if not os.path.exists(event_file):
        print(f"No {event_file} found")
        return
    with open(event_file, 'r') as f:
        events = json.load(f)
    print(f"\n[REPLAY] Playing {len(events)} events")
    for event in events:
        if event['type'] == 'publish':
            print(f"  -> {event['topic']}: {event['payload'].get('path', event['payload'].get('image_id', ''))}")
            r.publish(event['topic'], json.dumps(event['payload']))
            time.sleep(0.1)
    print("[REPLAY] Done\n")

if __name__ == '__main__':
    print("\n" + "="*60)
    print("EVENT-DRIVEN IMAGE SYSTEM WITH FAISS VECTOR SEARCH")
    print(f"DB: {len(database)} images | Vectors: {len(vector_index['items'])}")
    print("="*60 + "\n")
    
    threading.Thread(target=processor, daemon=True).start()
    threading.Thread(target=storage, daemon=True).start()
    threading.Thread(target=search_handler, daemon=True).start()
    threading.Thread(target=correction_handler, daemon=True).start()
    
    time.sleep(1)
    
    if len(database) == 0:
        replay_events('sample_events.json')
        time.sleep(2)
    
    upload_image('cat.jpg')
    upload_image('dog.png')
    time.sleep(2)
    
    searcher()
