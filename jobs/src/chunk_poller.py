#!/usr/bin/env python3
"""
Chunk Job Poller - Checks for trigger blobs and processes them
"""
import os
import sys
import json
from azure.storage.blob import BlobServiceClient

def main():
    """Poll for chunk trigger blobs and process them (up to 10 in parallel)"""
    connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    if not connection_string:
        print("❌ AZURE_STORAGE_CONNECTION_STRING not set")
        sys.exit(0)
    
    blob_service = BlobServiceClient.from_connection_string(connection_string)
    container_client = blob_service.get_container_client("stories")
    
    trigger_prefix = "triggers/chunk-job-scheduled/"
    
    print(f"🔍 Checking for chunk job triggers in {trigger_prefix}...")
    
    try:
        blobs = list(container_client.list_blobs(name_starts_with=trigger_prefix))
        
        if not blobs:
            print("   └─ No triggers found. Exiting.")
            sys.exit(0)
        
        # Get replica index from environment (Azure Container Apps provides this)
        replica_index = int(os.getenv("JOB_COMPLETION_INDEX", "0"))
        
        print(f"   └─ Found {len(blobs)} trigger(s), processing replica {replica_index}")
        
        # Each replica processes its assigned trigger
        if replica_index < len(blobs):
            blob = blobs[replica_index]
            
            try:
                print(f"\n📥 Processing trigger: {blob.name}")
                
                blob_client = container_client.get_blob_client(blob.name)
                trigger_data = json.loads(blob_client.download_blob().readall())
                
                story_id = trigger_data.get("story_id")
                chunk_id = trigger_data.get("chunk_id")
                trigger_id = trigger_data.get("trigger_id")
                
                if not story_id or chunk_id is None or not trigger_id:
                    print(f"   ❌ Invalid trigger data: {trigger_data}")
                    sys.exit(1)
                
                print(f"   └─ Story ID: {story_id}")
                print(f"   └─ Chunk ID: {chunk_id}")
                
                # Set environment variables
                os.environ["STORY_ID"] = story_id
                os.environ["CHUNK_ID"] = str(chunk_id)
                os.environ["TRIGGER_ID"] = trigger_id
                
                # Run chunk job
                print(f"\n🚀 Running chunk job for chunk {chunk_id}...")
                import chunk_jobs
                chunk_jobs.main()
                
                # Delete trigger after success
                blob_client.delete_blob()
                print(f"✅ Deleted trigger blob: {blob.name}")
                
            except Exception as e:
                print(f"❌ Error processing trigger {blob.name}: {e}")
                sys.exit(1)
        else:
            print(f"   └─ No trigger for replica {replica_index}")
        
    except Exception as e:
        print(f"❌ Error listing triggers: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

