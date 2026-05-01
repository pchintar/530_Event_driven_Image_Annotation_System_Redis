import redis
import json
import time
import uuid
import threading
import os
import hashlib

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

def make_embedding(text, dim=16):
    """Deterministic embedding generator"""
    hash_val = hashlib.md5(text.encode()).digest()
    return [((hash_val[i % len(hash_val)]) / 128.0) - 1.0 for i in range(dim)]

database = load_annotations()
vector_index = load_vector_index()

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
            if not any(i['item_id'] == f"image::{data['image_id']}" for i in vector_index['items']):
                vector_index['items'].append({
                    'item_id': f"image::{data['image_id']}",
                    'item_type': 'image',
                    'image_id': data['image_id'],
                    'label': data['image_id'],
                    'vector': image_embedding
                })
            save_vector_index(vector_index)
            
            r.publish(TOPIC_EMBEDDING, json.dumps({'image_id': data['image_id'], 'objects': [o['label'] for o in objects]}))
            print(f"[3] PROCESSOR: Found objects -> {[o['label'] for o in objects]}")

def storage():
    pubsub = r.pubsub()
    pubsub.subscribe(TOPIC_EMBEDDING)
    for msg in pubsub.listen():
        if msg['type'] == 'message':
            print(f"[4] STORAGE: Updated {ANNOTATIONS_FILE} and {VECTOR_INDEX_FILE}")

def search_handler():
    pubsub = r.pubsub()
    pubsub.subscribe(TOPIC_SEARCH)
    for msg in pubsub.listen():
        if msg['type'] == 'message':
            data = json.loads(msg['data'])
            query = data['query'].lower()
            matches = []
            for img_id, img_data in database.items():
                object_labels = [obj['label'].lower() for obj in img_data.get('objects', [])]
                if query in ' '.join(object_labels):
                    matches.append(img_id)
            r.publish(TOPIC_RESULT, json.dumps({
                'search_id': data['search_id'], 
                'query': query, 
                'matches': len(matches), 
                'image_ids': matches
            }))

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
                print(f"RESULT: Found {data['matches']} image(s) matching '{data['query']}'")
                if data['matches'] > 0:
                    print(f"Image IDs: {data['image_ids']}")
                print(f"{'='*50}")
                print("\n[search] Enter term | [correct] fix label | [quit]: ", end='', flush=True)
    
    threading.Thread(target=listen, daemon=True).start()
    
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
                print("\n[search] Enter term | [correct] fix label | [quit]: ", end='', flush=True)
            elif cmd:
                r.publish(TOPIC_SEARCH, json.dumps({'search_id': str(uuid.uuid4()), 'query': cmd}))
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
    print("EVENT-DRIVEN IMAGE SYSTEM")
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
    
    print("[search] Enter term | [correct] fix label | [quit]: ", end='', flush=True)
    searcher()
