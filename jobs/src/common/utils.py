import os
import json
import argparse

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--story-id", type=str, required=False, default=os.getenv("STORY_ID"))
    parser.add_argument("--chunk-id", type=int, required=False, default=os.getenv("CHUNK_ID"))
    args = parser.parse_args()
    
    if not args.story_id:
        raise ValueError("story-id is required (via --story-id or STORY_ID env var)")
    
    return args

def read_file(path):
    with open(path, "r") as f:
        return f.read()

def write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def write_text(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(text)
