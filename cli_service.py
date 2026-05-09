#!/usr/bin/env python3
import redis
import json
import uuid
import threading
from config import *
from utils import generate_event_id, utc_now

class CLIService:
    def __init__(self):
        self.r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)
        self.pubsub = self.r.pubsub()
        self.prompt = "[upload <file>|cat|dog|vector <term>|similar <id>|correct|quit]: "
    
    def upload_image(self, image_name):
        event = {
            'event_id': generate_event_id(),
            'type': 'publish',
            'timestamp': utc_now(),
            'payload': {
                'image_id': str(uuid.uuid4()),
                'name': image_name
            }
        }
        self.r.publish(TOPIC_IMAGE_UPLOAD, json.dumps(event))
        print(f"[CLI] Uploaded {image_name}")
    
    def search(self, query, use_vector=True):
        search_id = str(uuid.uuid4())
        event = {
            'event_id': generate_event_id(),
            'type': 'search.request',
            'timestamp': utc_now(),
            'payload': {
                'search_id': search_id,
                'query': query,
                'k': 5,
                'mode': 'vector' if use_vector else 'keyword'
            }
        }
        self.r.publish(TOPIC_SEARCH_REQUEST, json.dumps(event))
    
    def correct_annotation(self, image_id, old_label, new_label, object_index):
        event = {
            'event_id': generate_event_id(),
            'type': 'correction',
            'timestamp': utc_now(),
            'payload': {
                'image_id': image_id,
                'old_label': old_label,
                'new_label': new_label,
                'object_index': object_index,
                'reviewer': 'cli_user'
            }
        }
        self.r.publish(TOPIC_CORRECTION, json.dumps(event))
        print(f"[CLI] Correction requested: {old_label} -> {new_label}")
    
    def print_prompt(self):
        print(self.prompt, end='', flush=True)
    
    def run(self):
        def listen_for_results():
            self.pubsub.subscribe(TOPIC_SEARCH_RESULT)
            for msg in self.pubsub.listen():
                if msg['type'] == 'message':
                    data = json.loads(msg['data'])
                    payload = data.get('payload', data)
                    print(f"\n{'='*50}")
                    print(f"RESULT: Found {payload['matches']} image(s)")
                    if payload['matches'] > 0:
                        print(f"Image IDs: {payload['image_ids']}")
                    print(f"{'='*50}")
                    self.print_prompt()
        
        threading.Thread(target=listen_for_results, daemon=True).start()
        
        print("\n" + "="*60)
        print("EVENT-DRIVEN IMAGE SYSTEM - CLI SERVICE")
        print("All services communicate ONLY through Redis")
        print("="*60 + "\n")
        
        self.print_prompt()
        
        while True:
            try:
                cmd = input().strip()
                
                if cmd == 'quit':
                    print("Shutting down...")
                    break
                elif cmd.startswith('upload '):
                    filename = cmd[7:]
                    self.upload_image(filename)
                    self.print_prompt()
                elif cmd == 'correct':
                    print("Enter correction details:")
                    img_id = input("  Image ID: ").strip()
                    old = input("  Old label: ").strip()
                    new = input("  New label: ").strip()
                    idx = int(input("  Object index: ").strip())
                    self.correct_annotation(img_id, old, new, idx)
                    self.print_prompt()
                elif cmd.startswith('vector '):
                    query = cmd[7:]
                    self.search(query, use_vector=True)
                    # Don't print prompt immediately - wait for async result
                elif cmd.startswith('similar '):
                    image_id = cmd[8:]
                    self.search(image_id, use_vector=True)
                elif cmd in ['cat', 'dog', 'tree', 'truck', 'vehicle', 'ball', 'sofa']:
                    self.search(cmd, use_vector=False)
                else:
                    print(f"Unknown command: {cmd}")
                    print("Commands: upload <file>, cat, dog, vector <term>, similar <id>, correct, quit")
                    self.print_prompt()
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Error: {e}")
                self.print_prompt()

if __name__ == '__main__':
    cli = CLIService()
    cli.run()
