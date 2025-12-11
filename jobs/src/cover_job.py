import json
from common.utils import parse_args
from common.storage import upload_json, download_text

def main():
    args = parse_args()
    story_id = args.story_id

    # Download manifest
    manifest_raw = download_text("stories", f"Users/{story_id}/manifest.json")
    manifest = json.loads(manifest_raw)

    # Generate cover (placeholder logic)
    cover = {
        "storyId": story_id,
        "title": manifest.get("userPrompt", "Untitled"),
        "coverUrl": f"https://placeholder.com/cover_{story_id}.png",
        "status": "completed"
    }

    # Upload cover
    upload_json("stories", f"Users/{story_id}/cover/cover_{story_id}.json", cover)
    print(f"Cover created for story {story_id}")

if __name__ == "__main__":
    main()