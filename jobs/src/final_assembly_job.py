import json
from common.storage import upload_json, download_text, list_blobs
from azure.storage.blob import BlobServiceClient
import os

def get_story_id_from_trigger():
    """Read story_id from trigger blob"""
    connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    blob_service = BlobServiceClient.from_connection_string(connection_string)
    
    # List trigger blobs for final-assembly-job (check both manual and scheduled)
    container_client = blob_service.get_container_client("stories")
    blobs = list(container_client.list_blobs(name_starts_with="triggers/final-assembly-job-scheduled/"))
    if not blobs:
        blobs = list(container_client.list_blobs(name_starts_with="triggers/final-assembly-job/"))
    
    if not blobs:
        print("⏳ No trigger blobs found, waiting...")
        return None
    
    # Process the first trigger blob
    blob = blobs[0]
    blob_client = blob_service.get_blob_client(container="stories", blob=blob.name)
    trigger_data = json.loads(blob_client.download_blob().readall().decode("utf-8"))
    story_id = trigger_data["story_id"]
    
    # Delete the trigger blob after reading
    blob_client.delete_blob()
    print(f"✅ Read trigger blob: {blob.name}")
    print(f"   Story ID: {story_id}")
    
    return story_id

def main():
    story_id = get_story_id_from_trigger()
    
    if not story_id:
        print("No work to do, exiting...")
        return

    # Download manifest
    manifest_raw = download_text("stories", f"Users/{story_id}/manifest.json")
    manifest = json.loads(manifest_raw)

    # Download all chunks (1-indexed)
    chunks = []
    num_chapters = len(manifest.get("chapters", []))
    
    for chunk_id in range(1, num_chapters + 1):
        try:
            chunk_raw = download_text("stories", f"Users/{story_id}/chunks/chunk_{chunk_id}.json")
            chunk = json.loads(chunk_raw)
            chunks.append(chunk)
        except Exception as e:
            print(f"Warning: Could not load chunk {chunk_id}: {e}")

    if not chunks:
        raise Exception("No chunks found to assemble")

    # Assemble final story
    final_story = {
        "storyId": story_id,
        "title": manifest.get("title", "Untitled Story"),
        "coverUrl": None,  # No cover generation (using frontend gradients)
        "language": manifest.get("language"),
        "genre": manifest.get("genre"),
        "readingLevel": manifest.get("readingLevel"),
        "chapters": [
            {
                "chapterNumber": chunk.get("chunkId"),
                "title": chunk.get("chapterTitle", f"Chapter {chunk.get('chunkId')}"),
                "content": chunk.get("content")
            }
            for chunk in sorted(chunks, key=lambda x: x.get("chunkId", 0))
        ],
        "content": [chunk.get("content") for chunk in sorted(chunks, key=lambda x: x.get("chunkId", 0))],
        "status": "completed",
        "totalChapters": len(chunks)
    }

    # Upload final story
    upload_json("stories", f"Users/{story_id}/final/story_{story_id}.json", final_story)
    print(f"✅ Final story assembled for {story_id}")
    print(f"   Title: {final_story['title']}")
    print(f"   Chapters: {final_story['totalChapters']}")

if __name__ == "__main__":
    main()