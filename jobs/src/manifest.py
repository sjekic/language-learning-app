import json
from common.utils import parse_args  # Use shared function
from common.storage import upload_json, download_text

def main():
    args = parse_args()
    story_id = args.story_id  # Note: argparse converts --story-id to story_id

    # Download raw prompt
    raw = download_text("stories", f"Users/{story_id}/prompt/raw_{story_id}.json")
    data = json.loads(raw)

    # Build manifest
    manifest = {
        "storyId": story_id,
        "userPrompt": data.get("userPrompt"),
        "genre": data.get("genre"),
        "readingLevel": data.get("readingLevel"),
        "chunks": [],
        "status": "pending"
    }

    # Upload manifest
    upload_json("stories", f"Users/{story_id}/manifest.json", manifest)
    print(f"Manifest created for story {story_id}")

if __name__ == "__main__":
    main()
