"""Publish only complete, validated stories in manifest order."""
import json
from common.contracts import validate_chunk, validate_manifest, validate_trigger
from common.storage import download_text, upload_json


def main(trigger=None):
    if trigger is None:
        from final_assembly_poller import main as poll
        return poll()
    validate_trigger(trigger, "final-assembly-job")
    story_id = trigger["story_id"]
    manifest = json.loads(download_text("stories", f"Users/{story_id}/manifest.json"))
    chapters = validate_manifest(manifest, story_id)
    chunks = []
    for number in range(1, len(chapters) + 1):
        chunk = json.loads(download_text("stories", f"Users/{story_id}/chunks/chunk_{number}.json"))
        chunks.append(validate_chunk(chunk, story_id, number))
    final_story = {
        "storyId": story_id, "title": manifest.get("title", "Untitled Story"),
        "coverUrl": manifest.get("coverUrl", ""), "language": manifest.get("language"),
        "genre": manifest.get("genre"), "readingLevel": manifest.get("readingLevel"),
        "chapters": [{"chapterNumber": number, "title": chapters[number - 1]["title"],
                      "content": chunk["content"]} for number, chunk in enumerate(chunks, 1)],
        "content": [chunk["content"] for chunk in chunks],
        "status": "completed", "totalChapters": len(chapters),
    }
    upload_json("stories", f"Users/{story_id}/final/story_{story_id}.json", final_story)
    return final_story


if __name__ == "__main__":
    main()
