import json
from common.utils import parse_args
from common.storage import upload_json, download_text, list_blobs

def main():
    args = parse_args()
    story_id = args.story_id

    # Download manifest
    manifest_raw = download_text("stories", f"Users/{story_id}/manifest.json")
    manifest = json.loads(manifest_raw)

    # Download cover
    cover_raw = download_text("stories", f"Users/{story_id}/cover/cover_{story_id}.json")
    cover = json.loads(cover_raw)

    # Download all chunks
    chunks = []
    chunk_id = 0
    while True:
        try:
            chunk_raw = download_text("stories", f"Users/{story_id}/chunks/chunk_{chunk_id}.json")
            chunk = json.loads(chunk_raw)
            chunks.append(chunk)
            chunk_id += 1
        except Exception:
            break  # No more chunks

    # Assemble final story
    final_story = {
        "storyId": story_id,
        "title": cover.get("title", "Untitled"),
        "coverUrl": cover.get("coverUrl"),
        "genre": manifest.get("genre"),
        "readingLevel": manifest.get("readingLevel"),
        "content": [chunk.get("content") for chunk in chunks],
        "status": "completed"
    }

    # Upload final story
    upload_json("stories", f"Users/{story_id}/final/story_{story_id}.json", final_story)
    print(f"Final story assembled for {story_id}")

if __name__ == "__main__":
    main()