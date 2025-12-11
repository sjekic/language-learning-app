import json
from common.utils import parse_args
from common.storage import upload_json, download_text

def main():
    args = parse_args()
    story_id = args.story_id
    chunk_id = args.chunk_id

    # Download manifest
    manifest_raw = download_text("stories", f"Users/{story_id}/manifest.json")
    manifest = json.loads(manifest_raw)

    # Generate chunk content (placeholder logic)
    chunk_content = {
        "storyId": story_id,
        "chunkId": chunk_id,
        "content": f"Generated content for chunk {chunk_id}",
        "status": "completed"
    }

    # Upload chunk
    upload_json("stories", f"Users/{story_id}/chunks/chunk_{chunk_id}.json", chunk_content)
    print(f"Chunk {chunk_id} created for story {story_id}")

if __name__ == "__main__":
    main()