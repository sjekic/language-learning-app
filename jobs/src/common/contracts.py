"""Validation shared by trigger consumers and story completion checks."""
import re


def positive_integer(value, field):
    if type(value) is not int or value < 1:
        raise ValueError(f"{field} must be a positive integer")
    return value


def validate_trigger(payload, job):
    if not isinstance(payload, dict):
        raise ValueError("Trigger must be a JSON object")
    story_id = payload.get("story_id")
    if not isinstance(story_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", story_id):
        raise ValueError("Trigger must contain a safe nonempty story_id")
    if job == "chunk-job":
        batch = "chapter_start" in payload or "chapter_end" in payload
        if batch:
            start = positive_integer(payload.get("chapter_start"), "chapter_start")
            end = positive_integer(payload.get("chapter_end"), "chapter_end")
            positive_integer(payload.get("batch_id"), "batch_id")
            if start > end:
                raise ValueError("chapter_start must not exceed chapter_end")
            if "chunk_id" in payload:
                raise ValueError("Trigger cannot mix batch and single-chapter formats")
        else:
            positive_integer(payload.get("chunk_id"), "chunk_id")
    if job == "orchestrator-job" and "expected_chunks" in payload:
        positive_integer(payload["expected_chunks"], "expected_chunks")
    return payload


def validate_manifest(manifest, story_id):
    if not isinstance(manifest, dict) or manifest.get("storyId") != story_id:
        raise ValueError("Manifest story identity does not match")
    chapters = manifest.get("chapters")
    if not isinstance(chapters, list) or not chapters:
        raise ValueError("Manifest must contain chapters")
    for number, chapter in enumerate(chapters, 1):
        if not isinstance(chapter, dict) or type(chapter.get("chapterNumber")) is not int or chapter["chapterNumber"] != number:
            raise ValueError("Manifest chapter numbers must be consecutive starting at 1")
        for field in ("title", "summary"):
            if not isinstance(chapter.get(field), str) or not chapter[field].strip():
                raise ValueError(f"Chapter {number} requires {field}")
    return chapters


def validate_chunk(chunk, story_id, number):
    if not isinstance(chunk, dict) or chunk.get("storyId") != story_id:
        raise ValueError(f"Chapter {number} story identity does not match")
    if type(chunk.get("chunkId")) is not int or chunk["chunkId"] != number:
        raise ValueError(f"Chapter {number} identity does not match")
    if chunk.get("status") != "completed":
        raise ValueError(f"Chapter {number} is not completed")
    if not isinstance(chunk.get("content"), str) or not chunk["content"].strip():
        raise ValueError(f"Chapter {number} has no content")
    return chunk
