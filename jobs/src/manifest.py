import json
import os
from openai import OpenAI
from common.storage import upload_json, download_text, list_blobs
from azure.storage.blob import BlobServiceClient

def get_story_id_from_trigger():
    """Read story_id from trigger blob"""
    connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    blob_service = BlobServiceClient.from_connection_string(connection_string)
    
    # List trigger blobs for manifest-job (check both manual and scheduled)
    container_client = blob_service.get_container_client("stories")
    blobs = list(container_client.list_blobs(name_starts_with="triggers/manifest-job-scheduled/"))
    if not blobs:
        blobs = list(container_client.list_blobs(name_starts_with="triggers/manifest-job/"))
    
    for blob in blobs:
        # Read the trigger blob
        blob_client = blob_service.get_blob_client(container="stories", blob=blob.name)
        trigger_data = json.loads(blob_client.download_blob().readall().decode("utf-8"))
        story_id = trigger_data["story_id"]
        
        # Delete the trigger blob after reading
        blob_client.delete_blob()
        print(f"✅ Read trigger blob: {blob.name}")
        print(f"   Story ID: {story_id}")
        
        return story_id
    
    raise Exception("No trigger blob found for manifest-job")

def main():
    story_id = get_story_id_from_trigger()

    # Download raw prompt
    raw = download_text("stories", f"Users/{story_id}/prompt/raw_{story_id}.json")
    data = json.loads(raw)

    # Initialize OpenAI
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    # Use OpenAI to plan the story structure
    system_prompt = """You are a language learning story planner. Create a detailed 10-chapter story outline.
    Return ONLY a JSON object with this structure:
    {
        "title": "Story Title",
        "chapters": [
            {"chapterNumber": 1, "title": "Chapter Title", "summary": "Brief summary of what happens"},
            ...
        ]
    }"""
    
    user_prompt = f"""Create a story outline for language learning:
    - Language: {data.get('language')}
    - Level: {data.get('readingLevel')}
    - Genre: {data.get('genre')}
    - User Request: {data.get('userPrompt')}
    
    The story should have exactly 10 chapters appropriate for {data.get('readingLevel')} level learners."""
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        response_format={"type": "json_object"},
        temperature=0.8
    )
    
    story_plan = json.loads(response.choices[0].message.content)
    
    # Build manifest with chapters
    manifest = {
        "storyId": story_id,
        "title": story_plan.get("title", data.get("userPrompt")),
        "userPrompt": data.get("userPrompt"),
        "genre": data.get("genre"),
        "readingLevel": data.get("readingLevel"),
        "language": data.get("language"),
        "chapters": story_plan.get("chapters", []),
        "chunks": [],
        "status": "planned"
    }

    # Upload manifest
    upload_json("stories", f"Users/{story_id}/manifest.json", manifest)
    print(f"✅ Manifest created for story {story_id}")
    print(f"   Title: {manifest['title']}")
    print(f"   Chapters: {len(manifest['chapters'])}")
    
    # Orchestration: Create trigger blobs for chunk jobs
    print(f"\n🔄 Creating trigger blobs for {len(manifest['chapters'])} chunk jobs...")
    
    connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    blob_service = BlobServiceClient.from_connection_string(connection_string)
    
    import uuid
    from datetime import datetime
    
    for i in range(1, len(manifest['chapters']) + 1):
        try:
            trigger_id = uuid.uuid4().hex[:8]
            trigger_data = {
                "story_id": story_id,
                "chunk_id": i,
                "job_name": "chunk-job",
                "timestamp": datetime.utcnow().isoformat(),
                "trigger_id": trigger_id
            }
            
            trigger_blob_name = f"triggers/chunk-job-scheduled/{trigger_id}.json"
            blob_client = blob_service.get_blob_client(container="stories", blob=trigger_blob_name)
            blob_client.upload_blob(json.dumps(trigger_data), overwrite=True)
            print(f"   ✅ Created trigger blob for chunk {i}")
        except Exception as e:
            print(f"   ⚠️  Failed to create trigger for chunk {i}: {e}")
    
    # Create trigger blob for orchestrator
    try:
        trigger_id = uuid.uuid4().hex[:8]
        trigger_data = {
            "story_id": story_id,
            "job_name": "orchestrator-job",
            "timestamp": datetime.utcnow().isoformat(),
            "trigger_id": trigger_id,
            "expected_chunks": len(manifest['chapters'])
        }
        
        trigger_blob_name = f"triggers/orchestrator-job-scheduled/{trigger_id}.json"
        blob_client = blob_service.get_blob_client(container="stories", blob=trigger_blob_name)
        blob_client.upload_blob(json.dumps(trigger_data), overwrite=True)
        print(f"\n✅ Created orchestrator trigger blob")
    except Exception as e:
        print(f"⚠️  Failed to create orchestrator trigger: {e}")
    
    print(f"\n✅ All trigger blobs created! Story generation ready...")

if __name__ == "__main__":
    main()
