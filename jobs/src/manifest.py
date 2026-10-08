"""Plan a story and dispatch chapter batches; retries reuse the stored plan."""
import json
import os

from openai import OpenAI
from common.contracts import validate_manifest, validate_trigger
from common.storage import download_json_if_exists, download_text, upload_json
from common.triggers import check_claim, enqueue


def main(trigger=None):
    if trigger is None:
        from manifest_poller import main as poll
        return poll()
    validate_trigger(trigger, "manifest-job")
    story_id = trigger["story_id"]
    path = f"Users/{story_id}/manifest.json"
    manifest = download_json_if_exists("stories", path)
    if manifest is None:
        data = json.loads(download_text("stories", f"Users/{story_id}/prompt/raw_{story_id}.json"))
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        check_claim()
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": (
                    'Create a detailed 10-chapter language-learning story outline. Return only a JSON object '
                    'with "title" and "chapters". Each chapter has "chapterNumber" (1 through 10), '
                    '"title", and "summary".')},
                {"role": "user", "content": (
                    f"Language: {data.get('language')}\nLevel: {data.get('readingLevel')}\n"
                    f"Genre: {data.get('genre')}\nRequest: {data.get('userPrompt')}")},
            ],
            response_format={"type": "json_object"},
            temperature=0.8,
        )
        plan = json.loads(response.choices[0].message.content)
        manifest = {
            "storyId": story_id, "title": plan.get("title", data.get("userPrompt")),
            "userPrompt": data.get("userPrompt"), "genre": data.get("genre"),
            "readingLevel": data.get("readingLevel"), "language": data.get("language"),
            "chapters": plan.get("chapters"), "chunks": [], "status": "planned",
        }
        if len(validate_manifest(manifest, story_id)) != 10:
            raise ValueError("Planner must produce exactly 10 chapters")
        upload_json("stories", path, manifest)
    chapters = validate_manifest(manifest, story_id)
    if len(chapters) != 10:
        raise ValueError("Planned story must contain exactly 10 chapters")

    for batch, (start, end) in enumerate(((1, 3), (4, 7), (8, 10)), 1):
        enqueue("chunk-job", story_id, f"{story_id}-batch-{batch}",
                batch_id=batch, chapter_start=start, chapter_end=end)
    enqueue("orchestrator-job", story_id, f"{story_id}-orchestrator", expected_chunks=len(chapters))
    return manifest


if __name__ == "__main__":
    main()
