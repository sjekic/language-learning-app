# services/book-service/main.py
from fastapi import FastAPI, HTTPException, Depends, Header
# services/book-service/main.py
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from azure.storage.blob import BlobServiceClient
from azure.identity import DefaultAzureCredential
from azure.mgmt.appcontainers import ContainerAppsAPIClient
from azure.storage.blob import BlobServiceClient
from azure.identity import DefaultAzureCredential
from azure.mgmt.appcontainers import ContainerAppsAPIClient
import os
import json
import uuid
import httpx
from datetime import datetime

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
STORAGE_CONTAINER = "stories"

blob_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING) if AZURE_STORAGE_CONNECTION_STRING else None

class GenerateStoryRequest(BaseModel):
    language: str
    level: str
    genre: str
    prompt: str

class StoryResponse(BaseModel):
    story_id: str
    status: str
    message: str

@app.get("/")
def health():
    return {"service": "book-service", "status": "healthy"}

@app.post("/api/books/generate", response_model=StoryResponse)
async def generate_story(request: GenerateStoryRequest):
    """Start story generation by uploading prompt and triggering manifest job"""
    try:
        # Generate unique story ID
        story_id = f"story_{uuid.uuid4().hex[:8]}"
        
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
        
        # Trigger manifest job
        await trigger_container_job("manifest-job", story_id)
        
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
    try:
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
        
        # Check manifest for progress
        try:
            manifest_blob = blob_client.get_blob_client(
                container=STORAGE_CONTAINER,
                blob=f"Users/{story_id}/manifest.json"
            )
            manifest = json.loads(manifest_blob.download_blob().readall().decode("utf-8"))
            
            # Count completed chunks
            chunks_completed = len(manifest.get("chunks", []))
            
            return {
                "story_id": story_id,
                "status": manifest.get("status", "processing"),
                "chunks_completed": chunks_completed
            }
        except:
            pass
        
        return {"story_id": story_id, "status":