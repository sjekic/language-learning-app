#!/usr/bin/env python3
"""
Orchestrator Job Poller - Checks for trigger blobs and processes them
"""
import os
import sys
import json
from azure.storage.blob import BlobServiceClient

def main():
    """Poll for orchestrator trigger blobs and process them"""
    connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    if not connection_string:
        print("❌ AZURE_STORAGE_CONNECTION_STRING not set")
        sys.exit(0)
    
    blob_service = BlobServiceClient.from_connection_string(connection_string)
    container_client = blob_service.get_container_client("stories")
    
    trigger_prefix = "triggers/orchestrator-job-scheduled/"
    
    print(f"🔍 Checking for orchestrator job triggers in {trigger_prefix}...")
    
    try:
        blobs = list(container_client.list_blobs(name_starts_with=trigger_prefix))
        
        if not blobs:
            print("   └─ No triggers found. Exiting.")
            sys.exit(0)
        
        print(f"   └─ Found {len(blobs)} trigger(s)")
        
        for blob in blobs:
            try:
                print(f"\n📥 Processing trigger: {blob.name}")
                
                blob_client = container_client.get_blob_client(blob.name)
                trigger_data = json.loads(blob_client.download_blob().readall())
                
                story_id = trigger_data.get("story_id")
                trigger_id = trigger_data.get("trigger_id")
                
                if not story_id or not trigger_id:
                    print(f"   ❌ Invalid trigger data: {trigger_data}")
                    continue
                
                print(f"   └─ Story ID: {story_id}")
                
                # Set environment variables
                os.environ["STORY_ID"] = story_id
                os.environ["TRIGGER_ID"] = trigger_id
                
                # Run orchestrator job
                print(f"\n🚀 Running orchestrator job for story {story_id}...")
                import orchestrator
                orchestrator.main()
                
                # Delete trigger after success
                blob_client.delete_blob()
                print(f"✅ Deleted trigger blob: {blob.name}")
                
            except Exception as e:
                print(f"❌ Error processing trigger {blob.name}: {e}")
                continue
        
    except Exception as e:
        print(f"❌ Error listing triggers: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

