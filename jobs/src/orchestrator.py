import json
import os
import time
import subprocess
from common.storage import download_text, list_blobs, upload_json
from azure.storage.blob import BlobServiceClient

def get_params_from_trigger():
    """Read story_id and expected_chunks from trigger blob"""
    connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    blob_service = BlobServiceClient.from_connection_string(connection_string)
    
    # List trigger blobs for orchestrator-job (check both manual and scheduled)
    container_client = blob_service.get_container_client("stories")
    blobs = list(container_client.list_blobs(name_starts_with="triggers/orchestrator-job-scheduled/"))
    if not blobs:
        blobs = list(container_client.list_blobs(name_starts_with="triggers/orchestrator-job/"))
    
    if not blobs:
        print("⏳ No trigger blobs found, waiting...")
        return None, None
    
    # Process the first trigger blob
    blob = blobs[0]
    blob_client = blob_service.get_blob_client(container="stories", blob=blob.name)
    trigger_data = json.loads(blob_client.download_blob().readall().decode("utf-8"))
    story_id = trigger_data["story_id"]
    expected_chunks = trigger_data.get("expected_chunks", 10)
    
    # Delete the trigger blob after reading
    blob_client.delete_blob()
    print(f"✅ Read orchestrator trigger: {blob.name}")
    print(f"   Story ID: {story_id}, Expected chunks: {expected_chunks}")
    
    return story_id, expected_chunks

def main():
    story_id, expected_chunks = get_params_from_trigger()
    
    if not story_id:
        print("No work to do, exiting...")
        return
    
    print(f"🔄 Orchestrator started for story {story_id}")
    print(f"   Expected chunks: {expected_chunks}")
    
    # Poll for chunk completion (max 10 minutes)
    max_attempts = 60  # 60 attempts * 10 seconds = 10 minutes
    attempt = 0
    
    while attempt < max_attempts:
        try:
            # List all chunks
            chunks = list_blobs("stories", f"Users/{story_id}/chunks/")
            chunk_count = len([b for b in chunks if b.startswith(f"Users/{story_id}/chunks/chunk_")])
            
            print(f"   Progress: {chunk_count}/{expected_chunks} chunks completed")
            
            if chunk_count >= expected_chunks:
                print(f"\n✅ All chunks completed! Creating final assembly trigger...")
                
                # Create trigger blob for final-assembly-job
                connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
                blob_service = BlobServiceClient.from_connection_string(connection_string)
                
                import uuid
                from datetime import datetime
                
                trigger_id = uuid.uuid4().hex[:8]
                trigger_data = {
                    "story_id": story_id,
                    "job_name": "final-assembly-job",
                    "timestamp": datetime.utcnow().isoformat(),
                    "trigger_id": trigger_id
                }
                
                trigger_blob_name = f"triggers/final-assembly-job-scheduled/{trigger_id}.json"
                blob_client = blob_service.get_blob_client(container="stories", blob=trigger_blob_name)
                blob_client.upload_blob(json.dumps(trigger_data), overwrite=True)
                print(f"✅ Final assembly trigger created: {trigger_blob_name}")
                print(f"\n🎉 Story {story_id} orchestration complete!")
                return
                
        except Exception as e:
            print(f"   ⚠️  Error checking chunks: {e}")
        
        attempt += 1
        time.sleep(10)  # Wait 10 seconds before next check
    
    print(f"\n⏰ Timeout: Not all chunks completed after {max_attempts * 10} seconds")
    print(f"   Completed: {chunk_count}/{expected_chunks}")

if __name__ == "__main__":
    main()

