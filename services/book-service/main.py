# services/book-service/main.py
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import json
import uuid
import httpx
from datetime import datetime

# Azure SDK is optional for local development/testing.
try:
    from azure.storage.blob import BlobServiceClient  # type: ignore
    _AZURE_BLOB_AVAILABLE = True
except ModuleNotFoundError:
    BlobServiceClient = None  # type: ignore
    _AZURE_BLOB_AVAILABLE = False

app = FastAPI(title="Book Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Azure config
AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
AZURE_SUBSCRIPTION_ID = os.getenv("AZURE_SUBSCRIPTION_ID")
AZURE_RESOURCE_GROUP = os.getenv("AZURE_RESOURCE_GROUP")
AZURE_LOCATION = os.getenv("AZURE_LOCATION", "westeurope")
STORAGE_CONTAINER = "stories"

# Development mode - set to "true" to skip Azure authentication
DEV_MODE = os.getenv("DEV_MODE", "false").lower() == "true" or not _AZURE_BLOB_AVAILABLE or not AZURE_STORAGE_CONNECTION_STRING

blob_client = (
    BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
    if (BlobServiceClient and AZURE_STORAGE_CONNECTION_STRING and not DEV_MODE)
    else None
)

class GenerateStoryRequest(BaseModel):
    language: str
    level: str
    genre: str
    prompt: str

class StoryResponse(BaseModel):
    story_id: str
    status: str
    message: str

async def trigger_container_job(job_name: str, story_id: str, chunk_id: str = None):
    """Trigger Azure Container App Job using blob storage coordination"""
    
    # Development mode - skip Azure authentication
    if DEV_MODE:
        print(f"🔧 [DEV MODE] Simulating job trigger: {job_name} for story {story_id}")
        if chunk_id:
            print(f"   └─ Chunk ID: {chunk_id}")
        print(f"   └─ In production, this would create a trigger blob")
        return f"dev-execution-{uuid.uuid4().hex[:8]}"
    
    # Production mode - create trigger blob (scheduled jobs will process it)
    try:
        # Write trigger blob with job parameters
        trigger_id = uuid.uuid4().hex[:8]
        trigger_data = {
            "story_id": story_id,
            "chunk_id": chunk_id,
            "job_name": job_name,
            "timestamp": datetime.utcnow().isoformat(),
            "trigger_id": trigger_id
        }
        
        blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
        # Note: scheduled jobs look for triggers in "{job_name}-scheduled/" folders
        trigger_blob_name = f"triggers/{job_name}-scheduled/{trigger_id}.json"
        blob_client = blob_service_client.get_blob_client(container="stories", blob=trigger_blob_name)
        blob_client.upload_blob(json.dumps(trigger_data), overwrite=True)
        
        print(f"✅ Created trigger blob: {trigger_blob_name}")
        print(f"   └─ Story ID: {story_id}")
        if chunk_id:
            print(f"   └─ Chunk ID: {chunk_id}")
        print(f"   └─ Scheduled job will process this within 60 seconds")
        
        return trigger_id
        
    except Exception as e:
        print(f"❌ Error creating trigger blob: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create trigger: {str(e)}")

@app.get("/")
def health():
    return {"service": "book-service", "status": "healthy"}

@app.post("/api/books/generate", response_model=StoryResponse)
async def generate_story(request: GenerateStoryRequest):
    """Start story generation by uploading prompt and triggering manifest job"""
    try:
        # Generate unique story ID
        story_id = f"story_{uuid.uuid4().hex[:8]}"

        # Local/dev mode: don't require Azure SDK or Azure Blob Storage
        if DEV_MODE or blob_client is None:
            return StoryResponse(
                story_id=story_id,
                status="processing",
                message="Story generation started (DEV_MODE - Azure Blob operations skipped)"
            )
        
        # Prepare raw prompt data
        raw_prompt = {
            "userPrompt": request.prompt,
            "genre": request.genre,
            "readingLevel": request.level,
            "language": request.language,
            "createdAt": datetime.utcnow().isoformat()
        }
        
        # Upload to blob storage
        blob_path = f"Users/{story_id}/prompt/raw_{story_id}.json"
        blob = blob_client.get_blob_client(container=STORAGE_CONTAINER, blob=blob_path)
        blob.upload_blob(json.dumps(raw_prompt), overwrite=True)
        
        print(f"✅ Uploaded prompt to {blob_path}")
        
        # Create trigger blob for manifest job (scheduled job will process it)
        trigger_id = uuid.uuid4().hex[:8]
        trigger_data = {
            "story_id": story_id,
            "job_name": "manifest-job-scheduled",
            "timestamp": datetime.utcnow().isoformat(),
            "trigger_id": trigger_id
        }
        
        trigger_blob_path = f"triggers/manifest-job-scheduled/{trigger_id}.json"
        trigger_blob = blob_client.get_blob_client(container=STORAGE_CONTAINER, blob=trigger_blob_path)
        trigger_blob.upload_blob(json.dumps(trigger_data), overwrite=True)
        
        print(f"✅ Created trigger blob: {trigger_blob_path}")
        print(f"   └─ Scheduled job will process this within 60 seconds")
        
        return StoryResponse(
            story_id=story_id,
            status="processing",
            message="Story generation started"
        )
        
    except Exception as e:
        print(f"❌ Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/books/{story_id}/status")
async def get_story_status(story_id: str):
    """Check story generation status"""
    if DEV_MODE or blob_client is None:
        return {"story_id": story_id, "status": "processing", "message": "DEV_MODE - status polling simulated"}

    # Check if final story exists
    try:
        final_blob = blob_client.get_blob_client(
            container=STORAGE_CONTAINER,
            blob=f"Users/{story_id}/final/story_{story_id}.json"
        )
        final_data = json.loads(final_blob.download_blob().readall().decode("utf-8"))
        return {"story_id": story_id, "status": "completed", "story": final_data}
    except:
        pass
    
    # Count completed chunks by listing blob storage
    try:
        container_client = blob_client.get_container_client(STORAGE_CONTAINER)
        
        # List all chunk blobs
        chunk_prefix = f"Users/{story_id}/chunks/chunk_"
        chunks = list(container_client.list_blobs(name_starts_with=chunk_prefix))
        chunks_completed = len(chunks)
        
        print(f"📊 Story {story_id} progress: {chunks_completed}/10 chunks completed")
        
        return {
            "story_id": story_id,
            "status": "processing",
            "chunks_completed": chunks_completed
        }
    except Exception as e:
        print(f"⚠️  Error checking status for {story_id}: {e}")
        pass
    
    return {"story_id": story_id, "status": "processing", "chunks_completed": 0}