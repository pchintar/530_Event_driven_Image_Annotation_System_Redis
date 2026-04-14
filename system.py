import redis
import json
import time
import uuid
import threading

# Config
REDIS_HOST = 'localhost'
REDIS_PORT = 6379
TOPIC_UPLOAD = 'image.uploaded'
TOPIC_INFERENCE = 'inference.done'
TOPIC_EMBEDDING = 'embedding.done'
TOPIC_SEARCH = 'search.request'
TOPIC_RESULT = 'search.result'

r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)
database = {}

# Service 1: Uploader (simulates user)
def upload_image(image_name):
    msg = {'image_id': str(uuid.uuid4()), 'image_name': image_name, 'timestamp': time.time()}
    r.publish(TOPIC_UPLOAD, json.dumps(msg))
    print(f'[UPLOAD] {image_name} -> {msg["image_id"]}')

# Service 2: Processor (inference + embedding)
def processor():
    pubsub = r.pubsub()
    pubsub.subscribe(TOPIC_UPLOAD)
    for msg in pubsub.listen():
        if msg['type'] == 'message':
            data = json.loads(msg['data'])
            print(f'[INFERENCE] Processing {data["image_id"]}')
            time.sleep(0.5)
            objects = ['cat', 'sofa'] if 'cat' in data['image_name'] else ['dog', 'ball']
            r.publish(TOPIC_INFERENCE, json.dumps({'image_id': data['image_id'], 'objects': objects}))
            time.sleep(0.3)
            r.publish(TOPIC_EMBEDDING, json.dumps({'image_id': data['image_id'], 'vector': [0.1,0.5,0.3], 'objects': objects}))
            print(f'[PROCESSOR] Done -> {objects}')

# Service 3: Storage
def storage():
    pubsub = r.pubsub()
    pubsub.subscribe(TOPIC_EMBEDDING)
    for msg in pubsub.listen():
        if msg['type'] == 'message':
            data = json.loads(msg['data'])
            database[data['image_id']] = data
            print(f'[STORAGE] Saved {data["image_id"]} | Total: {len(database)}')

# Service 4: Search handler
def search_handler():
    pubsub = r.pubsub()
    pubsub.subscribe(TOPIC_SEARCH)
    for msg in pubsub.listen():
        if msg['type'] == 'message':
            data = json.loads(msg['data'])
            query = data['query'].lower()
            matches = [img_id for img_id, info in database.items() if any(query in obj for obj in info.get('objects', []))]
            r.publish(TOPIC_RESULT, json.dumps({'search_id': data['search_id'], 'query': query, 'matches': matches[:5]}))

# Service 5: CLI Searcher
def searcher():
    pubsub = r.pubsub()
    pubsub.subscribe(TOPIC_RESULT)
    def listen():
        for msg in pubsub.listen():
            if msg['type'] == 'message':
                data = json.loads(msg['data'])
                print(f'\n[RESULT] "{data["query"]}" -> {data["matches"]}')
    threading.Thread(target=listen, daemon=True).start()
    
    while True:
        q = input('Search> ')
        if q == 'quit':
            break
        search_id = str(uuid.uuid4())
        r.publish(TOPIC_SEARCH, json.dumps({'search_id': search_id, 'query': q}))

# Run everything
if __name__ == '__main__':
    # Start background services
    threading.Thread(target=processor, daemon=True).start()
    threading.Thread(target=storage, daemon=True).start()
    threading.Thread(target=search_handler, daemon=True).start()
    
    time.sleep(1)  # Let services start
    
    # Upload some test images
    upload_image('cat.jpg')
    upload_image('dog.png')
    
    time.sleep(2)  # Wait for processing
    
    # Start search CLI
    searcher()
