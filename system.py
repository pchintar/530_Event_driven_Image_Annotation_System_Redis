import redis
import json
import time
import uuid
import threading

# Config
REDIS_HOST = 'localhost'
REDIS_PORT = 6379
TOPIC_UPLOAD = 'image.uploaded'
TOPIC_EMBEDDING = 'embedding.done'
TOPIC_SEARCH = 'search.request'
TOPIC_RESULT = 'search.result'

r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)
database = {}

def upload_image(image_name):
    image_id = str(uuid.uuid4())
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
            objects = ['cat', 'sofa'] if 'cat' in data['name'] else ['dog', 'ball']
            r.publish(TOPIC_EMBEDDING, json.dumps({'image_id': data['image_id'], 'objects': objects}))
            print(f"[3] PROCESSOR: Found objects -> {objects}")

def storage():
    pubsub = r.pubsub()
    pubsub.subscribe(TOPIC_EMBEDDING)
    for msg in pubsub.listen():
        if msg['type'] == 'message':
            data = json.loads(msg['data'])
            database[data['image_id']] = data['objects']
            print(f"[4] STORAGE: Saved image (Total: {len(database)} images in DB)")

def search_handler():
    pubsub = r.pubsub()
    pubsub.subscribe(TOPIC_SEARCH)
    for msg in pubsub.listen():
        if msg['type'] == 'message':
            data = json.loads(msg['data'])
            query = data['query'].lower()
            matches = [img_id for img_id, objects in database.items() if query in ' '.join(objects)]
            r.publish(TOPIC_RESULT, json.dumps({'search_id': data['search_id'], 'query': query, 'matches': len(matches)}))
            print(f"[5] SEARCH: '{query}' -> {len(matches)} matching images")

def searcher():
    pubsub = r.pubsub()
    pubsub.subscribe(TOPIC_RESULT)
    def listen():
        for msg in pubsub.listen():
            if msg['type'] == 'message':
                data = json.loads(msg['data'])
                print(f"\n{'='*50}")
                print(f"RESULT: Found {data['matches']} image(s) matching '{data['query']}'")
                print(f"{'='*50}\n")
    threading.Thread(target=listen, daemon=True).start()
    
    while True:
        q = input("\nEnter search term (cat/dog/sofa/ball) or 'quit': ")
        if q == 'quit':
            break
        r.publish(TOPIC_SEARCH, json.dumps({'search_id': str(uuid.uuid4()), 'query': q}))

if __name__ == '__main__':
    print("\n" + "="*60)
    print("EVENT-DRIVEN IMAGE SYSTEM (Redis Pub-Sub)")
    print("="*60 + "\n")
    
    threading.Thread(target=processor, daemon=True).start()
    threading.Thread(target=storage, daemon=True).start()
    threading.Thread(target=search_handler, daemon=True).start()
    
    time.sleep(1)
    upload_image('cat.jpg')
    upload_image('dog.png')
    time.sleep(2)
    
    searcher()
