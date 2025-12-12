"""
Azure Blob Storage Integration
This module provides functions for uploading, downloading, and managing book content in Azure Blob Storage.
"""

import os
import uuid
from typing import Optional
import httpx

# Azure SDK is optional for local development/testing.
try:
    from azure.storage.blob import BlobServiceClient, ContentSettings  # type: ignore
    _AZURE_BLOB_AVAILABLE = True
except ModuleNotFoundError:
    BlobServiceClient = None  # type: ignore
    ContentSettings = None  # type: ignore
    _AZURE_BLOB_AVAILABLE = False

# Azure Storage Configuration
AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING", "")
AZURE_STORAGE_ACCOUNT_NAME = os.getenv("AZURE_STORAGE_ACCOUNT_NAME", "")
AZURE_STORAGE_CONTAINER_NAME = os.getenv("AZURE_STORAGE_CONTAINER_NAME", "book-content")
AZURE_STORAGE_COVER_CONTAINER = os.getenv("AZURE_STORAGE_COVER_CONTAINER", "book-covers")


async def upload_to_blob(
    content: bytes,
    filename: str,
    content_type: str = "application/json",
    container_name: Optional[str] = None
) -> str:
    """
    Upload content to Azure Blob Storage.
    
    Args:
        content: The binary content to upload
        filename: The name for the blob
        content_type: MIME type of the content
        container_name: Override default container name
    
    Returns:
        str: The public URL to the uploaded blob
    """
    
    if not container_name:
        container_name = AZURE_STORAGE_CONTAINER_NAME
    
    try:
        if not _AZURE_BLOB_AVAILABLE:
            raise RuntimeError("Azure Blob SDK not installed (azure-storage-blob). Using placeholder URL.")

        # Initialize blob service client
        blob_service_client = BlobServiceClient.from_connection_string(
            AZURE_STORAGE_CONNECTION_STRING
        )
        
        # Get container client (create if doesn't exist)
        container_client = blob_service_client.get_container_client(container_name)
        
        try:
            await container_client.get_container_properties()
        except Exception:
            # Container doesn't exist, create it
            await container_client.create_container()
        
        # Upload blob
        blob_name = f"{uuid.uuid4()}/{filename}"
        blob_client = blob_service_client.get_blob_client(
            container=container_name,
            blob=blob_name
        )
        
        content_settings = ContentSettings(content_type=content_type)
        
        await blob_client.upload_blob(
            content,
            overwrite=True,
            content_settings=content_settings
        )
        
        # Return public URL
        blob_url = blob_client.url
        
        print(f"[AZURE] Uploaded blob: {blob_url}")
        return blob_url
        
    except Exception as e:
        print(f"[ERROR] Failed to upload to blob storage: {e}")
        # PLACEHOLDER: Return a mock URL for development
        return f"https://{AZURE_STORAGE_ACCOUNT_NAME}.blob.core.windows.net/{container_name}/{filename}"


async def get_blob_url(blob_name: str, container_name: Optional[str] = None) -> str:
    """
    Get the public URL for a blob.
    
    Args:
        blob_name: The name of the blob
        container_name: Override default container name
    
    Returns:
        str: The public URL to the blob
    """
    
    if not container_name:
        container_name = AZURE_STORAGE_CONTAINER_NAME
    
    # If already a full URL, return as-is
    if blob_name.startswith("http"):
        return blob_name
    
    try:
        if not _AZURE_BLOB_AVAILABLE:
            raise RuntimeError("Azure Blob SDK not installed (azure-storage-blob). Returning placeholder URL.")

        blob_service_client = BlobServiceClient.from_connection_string(
            AZURE_STORAGE_CONNECTION_STRING
        )
        
        blob_client = blob_service_client.get_blob_client(
            container=container_name,
            blob=blob_name
        )
        
        return blob_client.url
        
    except Exception as e:
        print(f"[ERROR] Failed to get blob URL: {e}")
        return f"https://{AZURE_STORAGE_ACCOUNT_NAME}.blob.core.windows.net/{container_name}/{blob_name}"


async def delete_from_blob(blob_url: str) -> bool:
    """
    Delete a blob from Azure Blob Storage.
    
    Args:
        blob_url: The full URL or blob name
    
    Returns:
        bool: True if deleted successfully
    """
    
    try:
        if not _AZURE_BLOB_AVAILABLE:
            raise RuntimeError("Azure Blob SDK not installed (azure-storage-blob). Cannot delete blob.")

        blob_service_client = BlobServiceClient.from_connection_string(
            AZURE_STORAGE_CONNECTION_STRING
        )
        
        # Extract container and blob name from URL
        if blob_url.startswith("http"):
            # Parse URL: https://account.blob.core.windows.net/container/path/to/blob
            parts = blob_url.split("/")
            container_name = parts[3]
            blob_name = "/".join(parts[4:])
        else:
            container_name = AZURE_STORAGE_CONTAINER_NAME
            blob_name = blob_url
        
        blob_client = blob_service_client.get_blob_client(
            container=container_name,
            blob=blob_name
        )
        
        await blob_client.delete_blob()
        
        print(f"[AZURE] Deleted blob: {blob_url}")
        return True
        
    except Exception as e:
        print(f"[ERROR] Failed to delete blob: {e}")
        return False


async def download_from_blob(blob_url: str) -> bytes:
    """
    Download content from Azure Blob Storage.
    
    Args:
        blob_url: The full URL to the blob
    
    Returns:
        bytes: The blob content
    """
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(blob_url)
            
            if response.status_code == 200:
                return response.content
            else:
                raise Exception(f"Failed to download blob: HTTP {response.status_code}")
                
    except Exception as e:
        print(f"[ERROR] Failed to download from blob: {e}")
        raise


async def upload_book_content(book_data: dict, book_id: int) -> str:
    """
    Upload book content (pages) to blob storage as JSON.
    
    Args:
        book_data: Dictionary containing book pages and metadata
        book_id: The book ID for naming
    
    Returns:
        str: URL to the uploaded blob
    """
    
    import json
    
    content_json = json.dumps(book_data).encode('utf-8')
    filename = f"book_{book_id}_content.json"
    
    return await upload_to_blob(
        content=content_json,
        filename=filename,
        content_type="application/json"
    )


async def upload_book_cover(image_data: bytes, book_id: int, image_format: str = "png") -> str:
    """
    Upload book cover image to blob storage.
    
    Args:
        image_data: The image binary data
        book_id: The book ID for naming
        image_format: Image format (png, jpg, etc.)
    
    Returns:
        str: URL to the uploaded cover image
    """
    
    filename = f"book_{book_id}_cover.{image_format}"
    content_type = f"image/{image_format}"
    
    return await upload_to_blob(
        content=image_data,
        filename=filename,
        content_type=content_type,
        container_name=AZURE_STORAGE_COVER_CONTAINER
    )

