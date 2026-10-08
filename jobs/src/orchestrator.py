"""Wait for every expected valid chapter before scheduling assembly."""
import json
import os
import time

from azure.core.exceptions import ResourceNotFoundError
from common.contracts import validate_chunk, validate_manifest, validate_trigger
from common.storage import download_text
from common.triggers import check_claim, enqueue


def main(trigger=None):
    if trigger is None:
        from orchestrator_poller import main as poll
        return poll()
    validate_trigger(trigger, "orchestrator-job")
    story_id = trigger["story_id"]
    manifest = json.loads(download_text("stories", f"Users/{story_id}/manifest.json"))
    chapters = validate_manifest(manifest, story_id)
    expected = trigger.get("expected_chunks", len(chapters))
    if expected != len(chapters):
        raise ValueError("Trigger expected_chunks does not match manifest")
    attempts = int(os.getenv("ORCHESTRATOR_MAX_ATTEMPTS", "60"))
    interval = float(os.getenv("ORCHESTRATOR_POLL_SECONDS", "10"))
    if attempts < 1 or interval < 0:
        raise ValueError("Invalid orchestrator polling configuration")
    for attempt in range(attempts):
        check_claim()
        try:
            for number in range(1, expected + 1):
                chunk = json.loads(download_text("stories", f"Users/{story_id}/chunks/chunk_{number}.json"))
                validate_chunk(chunk, story_id, number)
        except (ResourceNotFoundError, ValueError):
            if attempt + 1 < attempts:
                time.sleep(interval)
            continue
        enqueue("final-assembly-job", story_id, f"{story_id}-assembly")
        return
    raise TimeoutError(f"Story {story_id} is incomplete after {attempts} checks; retry required")


if __name__ == "__main__":
    main()
