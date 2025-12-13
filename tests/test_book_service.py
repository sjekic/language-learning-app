"""
Unit tests for book-service
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from dotenv import load_dotenv
load_dotenv()
from datetime import datetime
import json
import sys
import os

# Set dummy env vars for tests (must be before imports)
os.environ['AZURE_STORAGE_CONNECTION_STRING'] = "DefaultEndpointsProtocol=https;AccountName=test;AccountKey=test;EndpointSuffix=core.windows.net"
os.environ['AZURE_STORAGE_ACCOUNT_NAME'] = "test-account"
os.environ['AZURE_STORAGE_CONTAINER_NAME'] = "test-container"
os.environ['AZURE_STORAGE_COVER_CONTAINER'] = "test-covers-container"
os.environ['AZURE_SUBSCRIPTION_ID'] = "test-sub-id"
os.environ['AZURE_RESOURCE_GROUP'] = "test-rg"
os.environ['AZURE_LOCATION'] = "westeurope"
os.environ['DEV_MODE'] = "false"  # Ensure we test production logic

# Mock dependencies (conditionally to avoid overwriting if shared across tests)
mocks = [
    'asyncpg', 'azure', 'azure.storage', 'azure.storage.blob', 
    'azure.identity', 'azure.mgmt', 'azure.mgmt.containerinstance', 
    'azure.mgmt.appcontainers'
]
for mod in mocks:
    if mod not in sys.modules or not isinstance(sys.modules[mod], MagicMock):
        sys.modules[mod] = MagicMock()
        if mod == 'asyncpg':
             sys.modules[mod].create_pool = AsyncMock()

# Set environment variables BEFORE importing app modules
import os
os.environ["DATABASE_URL"] = "postgresql://test:test@localhost/testdb"
os.environ["FIREBASE_SERVICE_ACCOUNT_KEY"] = '{"type": "service_account", "project_id": "test"}'

import importlib.util

# Load book-service modules in correct order
book_service_path = os.path.join(os.path.dirname(__file__), '..', 'services', 'book-service')
sys.path.insert(0, book_service_path)

# IMPORTANT: Load database.py FIRST and register it as 'database' so main.py can import it
db_spec = importlib.util.spec_from_file_location("database", os.path.join(book_service_path, "database.py"))
book_service_database = importlib.util.module_from_spec(db_spec)
sys.modules["database"] = book_service_database  # Register as 'database' so main.py can import it
sys.modules["book_service_database"] = book_service_database  # Also register with full name
db_spec.loader.exec_module(book_service_database)

# NOW load main.py (it will find 'database' in sys.modules)
spec = importlib.util.spec_from_file_location("book_service_main", os.path.join(book_service_path, "main.py"))
book_service_main = importlib.util.module_from_spec(spec)
sys.modules["book_service_main"] = book_service_main
spec.loader.exec_module(book_service_main)

from book_service_main import app
import book_service_main as main  # Alias for patch.object convenience
import book_service_database as book_database
import blob_storage
import azure_jobs
from contextlib import contextmanager

@contextmanager
def mock_db(conn):
    """
    Mock database connection. 
    Patches both main.get_db_connection (for direct main usage) 
    and database.get_db_connection (for cross-module usage).
    """
    print("DEBUG: Entering mock_db")
    with patch.object(main, 'get_db_connection', new_callable=AsyncMock) as mock_main_pool:
        mock_main_pool.return_value = conn
        with patch('database.get_db_connection', new_callable=AsyncMock) as mock_db_pool:
            mock_db_pool.return_value = conn
            print(f"DEBUG: Patched main.get_db_connection & database.get_db_connection")
            yield mock_main_pool
    print("DEBUG: Exiting mock_db")


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def mock_auth_response():
    """Mock auth service response"""
    return {
        'user': {
            'id': 1,
            'firebase_uid': 'test-firebase-uid-123',
            'email': 'test@example.com'
        }
    }


class TestBookServiceDatabase:
    """Tests for book-service database.py"""
    
    @pytest.mark.asyncio
    async def test_get_db_connection_success(self):
        """Test successful database connection"""
        with patch('asyncpg.create_pool', new_callable=AsyncMock) as mock_create_pool:
            mock_pool = AsyncMock()
            mock_create_pool.return_value = mock_pool
            with patch.dict(os.environ, {'DATABASE_URL': 'postgresql://test:test@localhost/test'}):
                book_database.pool = None
                result = await book_database.get_db_connection()
                assert result is not None
    
    @pytest.mark.asyncio
    async def test_get_db_connection_missing_url(self):
        """Test database connection with missing URL"""
        with patch.dict(os.environ, {}, clear=True):
            book_database.pool = None
            with pytest.raises(ValueError, match="DATABASE_URL"):
                await book_database.get_db_connection()
    
    @pytest.mark.asyncio
    async def test_get_db_connection_reuse_pool(self):
        """Test database connection reuses existing pool"""
        mock_pool = AsyncMock()
        book_database.pool = mock_pool
        result = await book_database.get_db_connection()
        assert result == mock_pool
        book_database.pool = None  # Reset
    
    @pytest.mark.asyncio
    async def test_close_db_connection(self):
        """Test closing database connection"""
        mock_pool = AsyncMock()
        book_database.pool = mock_pool
        await book_database.close_db_connection()
        mock_pool.close.assert_called_once()
        book_database.pool = None  # Reset
    
    @pytest.mark.asyncio
    async def test_close_db_connection_no_pool(self):
        """Test closing database connection when pool is None"""
        book_database.pool = None
        await book_database.close_db_connection()
        assert book_database.pool is None


class TestBlobStorage:
    """Tests for blob_storage.py"""
    
    @pytest.mark.asyncio
    async def test_upload_to_blob(self, mock_azure_blob_service_client):
        """Test upload to blob storage"""
        with patch('azure.storage.blob.BlobServiceClient.from_connection_string', return_value=mock_azure_blob_service_client):
            with patch.dict(os.environ, {'AZURE_STORAGE_CONNECTION_STRING': 'test-connection-string'}):
                result = await blob_storage.upload_to_blob(
                    b"test content",
                    "test.txt",
                    "text/plain"
                )
                assert result is not None
    
    @pytest.mark.asyncio
    async def test_get_blob_url(self, mock_azure_blob_service_client):
        """Test get blob URL"""
        with patch('azure.storage.blob.BlobServiceClient.from_connection_string', return_value=mock_azure_blob_service_client):
            with patch.dict(os.environ, {'AZURE_STORAGE_CONNECTION_STRING': 'test-connection-string'}):
                result = await blob_storage.get_blob_url("test/blob.txt")
                assert result is not None
    
    @pytest.mark.asyncio
    async def test_get_blob_url_already_full_url(self):
        """Test get blob URL when already a full URL"""
        result = await blob_storage.get_blob_url("https://test.blob.core.windows.net/container/blob.txt")
        assert result.startswith("http")
    
    @pytest.mark.asyncio
    async def test_delete_from_blob(self):
        """Test delete from blob storage"""
        # Create fresh mocks for each test
        mock_blob_client = MagicMock()
        mock_blob_client.delete_blob = AsyncMock()
        
        mock_service_client = MagicMock()
        mock_service_client.get_blob_client.return_value = mock_blob_client
        
        with patch.object(blob_storage, 'BlobServiceClient') as mock_bsc:
            mock_bsc.from_connection_string.return_value = mock_service_client
            with patch.dict(os.environ, {'AZURE_STORAGE_CONNECTION_STRING': 'test-connection-string'}):
                result = await blob_storage.delete_from_blob("https://test.blob.core.windows.net/container/blob.txt")
                
                assert result is True
                mock_blob_client.delete_blob.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_download_from_blob(self):
        """Test download from blob storage"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.content = b"test content"
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            
            result = await blob_storage.download_from_blob("https://test.blob.core.windows.net/container/blob.txt")
            assert result == b"test content"
    
    @pytest.mark.asyncio
    async def test_upload_book_content(self, mock_azure_blob_service_client):
        """Test upload book content"""
        with patch('azure.storage.blob.BlobServiceClient.from_connection_string', return_value=mock_azure_blob_service_client):
            with patch.dict(os.environ, {'AZURE_STORAGE_CONNECTION_STRING': 'test-connection-string'}):
                book_data = {"pages": [{"id": 1, "content": "Page 1"}]}
                result = await blob_storage.upload_book_content(book_data, 1)
                assert result is not None
    
    @pytest.mark.asyncio
    async def test_upload_book_cover(self, mock_azure_blob_service_client):
        """Test upload book cover"""
        with patch('azure.storage.blob.BlobServiceClient.from_connection_string', return_value=mock_azure_blob_service_client):
            with patch.dict(os.environ, {'AZURE_STORAGE_CONNECTION_STRING': 'test-connection-string'}):
                result = await blob_storage.upload_book_cover(b"image data", 1, "png")
                assert result is not None
    
    @pytest.mark.asyncio
    async def test_upload_to_blob_create_container(self):
        """Test upload to blob with container creation"""
        # Create fresh mocks
        mock_container_client = MagicMock()
        mock_container_client.get_container_properties = AsyncMock(side_effect=Exception("Not found"))
        mock_container_client.create_container = AsyncMock()
        
        mock_blob_client = MagicMock()
        mock_blob_client.upload_blob = AsyncMock()
        mock_blob_client.url = "https://test.blob.core.windows.net/container/file.json"
        
        mock_service_client = MagicMock()
        mock_service_client.get_container_client.return_value = mock_container_client
        mock_service_client.get_blob_client.return_value = mock_blob_client
        
        with patch.object(blob_storage, 'BlobServiceClient') as mock_bsc:
            mock_bsc.from_connection_string.return_value = mock_service_client
            with patch.dict(os.environ, {'AZURE_STORAGE_CONNECTION_STRING': 'test-connection-string'}):
                result = await blob_storage.upload_to_blob(
                    b"test content",
                    "test.txt",
                    "text/plain"
                )
                assert result is not None
                mock_container_client.create_container.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_upload_to_blob_exception(self, mock_azure_blob_service_client):
        """Test upload to blob with exception"""
        mock_azure_blob_service_client.get_blob_client = Mock(side_effect=Exception("Upload failed"))
        
        with patch('azure.storage.blob.BlobServiceClient.from_connection_string', return_value=mock_azure_blob_service_client):
            with patch.dict(os.environ, {'AZURE_STORAGE_CONNECTION_STRING': 'test-connection-string', 'AZURE_STORAGE_ACCOUNT_NAME': 'test-account'}):
                result = await blob_storage.upload_to_blob(
                    b"test content",
                    "test.txt",
                    "text/plain"
                )
                # Should return mock URL on error
                assert result is not None
    
    @pytest.mark.asyncio
    async def test_get_blob_url_exception(self, mock_azure_blob_service_client):
        """Test get blob URL with exception"""
        mock_azure_blob_service_client.get_blob_client = Mock(side_effect=Exception("Error"))
        
        with patch('azure.storage.blob.BlobServiceClient.from_connection_string', return_value=mock_azure_blob_service_client):
            with patch.dict(os.environ, {'AZURE_STORAGE_CONNECTION_STRING': 'test-connection-string', 'AZURE_STORAGE_ACCOUNT_NAME': 'test-account'}):
                result = await blob_storage.get_blob_url("test/blob.txt")
                assert result is not None
    
    @pytest.mark.asyncio
    async def test_delete_from_blob_exception(self, mock_azure_blob_service_client):
        """Test delete from blob with exception"""
        mock_azure_blob_service_client.get_blob_client = Mock(side_effect=Exception("Error"))
        
        with patch('azure.storage.blob.BlobServiceClient.from_connection_string', return_value=mock_azure_blob_service_client):
            with patch.dict(os.environ, {'AZURE_STORAGE_CONNECTION_STRING': 'test-connection-string'}):
                result = await blob_storage.delete_from_blob("https://test.blob.core.windows.net/container/blob.txt")
                assert result is False
    
    @pytest.mark.asyncio
    async def test_delete_from_blob_with_blob_name(self):
        """Test delete from blob with just blob name"""
        # Create fresh mocks
        mock_blob_client = MagicMock()
        mock_blob_client.delete_blob = AsyncMock()
        
        mock_service_client = MagicMock()
        mock_service_client.get_blob_client.return_value = mock_blob_client
        
        with patch.object(blob_storage, 'BlobServiceClient') as mock_bsc:
            mock_bsc.from_connection_string.return_value = mock_service_client
            with patch.dict(os.environ, {'AZURE_STORAGE_CONNECTION_STRING': 'test-connection-string'}):
                result = await blob_storage.delete_from_blob("blob.txt")
                assert result is True
                mock_blob_client.delete_blob.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_download_from_blob_error(self):
        """Test download from blob with error"""
        import httpx
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 404
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            
            with pytest.raises(Exception):
                await blob_storage.download_from_blob("https://test.blob.core.windows.net/container/blob.txt")
    
    @pytest.mark.asyncio
    async def test_download_from_blob_http_error(self):
        """Test download from blob with HTTP error"""
        import httpx
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=httpx.HTTPError("Connection error")
            )
            
            with pytest.raises(Exception):
                await blob_storage.download_from_blob("https://test.blob.core.windows.net/container/blob.txt")


class TestAzureJobs:
    """Tests for azure_jobs.py"""
    
    @pytest.mark.asyncio
    async def test_trigger_story_generation_job(self):
        """Test trigger story generation job"""
        job_payload = {
            'user_id': 1,
            'title': 'Test Story',
            'language_code': 'es',
            'level': 'A1',
            'genre': 'fantasy',
            'prompt': 'A test story',
            'is_pro_book': False,
            'pages_estimate': 10
        }
        
        job_id = await azure_jobs.trigger_story_generation_job(job_payload)
        assert job_id is not None
        assert job_id in azure_jobs.job_status_store
    
    @pytest.mark.asyncio
    async def test_check_job_status_found(self):
        """Test check job status when job exists"""
        job_id = "test-job-id"
        azure_jobs.job_status_store[job_id] = {
            "job_id": job_id,
            "status": "pending",
            "progress": 0,
            "book_id": None,
            "error": None
        }
        
        status = await azure_jobs.check_job_status(job_id)
        assert status["job_id"] == job_id
        assert status["status"] == "pending"
    
    @pytest.mark.asyncio
    async def test_check_job_status_not_found(self):
        """Test check job status when job doesn't exist"""
        status = await azure_jobs.check_job_status("non-existent-job")
        assert status["status"] == "not_found"
    
    @pytest.mark.asyncio
    async def test_cancel_job(self):
        """Test cancel job"""
        job_id = "test-job-id-2"
        azure_jobs.job_status_store[job_id] = {
            "job_id": job_id,
            "status": "pending",
            "progress": 0,
            "book_id": None,
            "error": None
        }
        
        result = await azure_jobs.cancel_job(job_id)
        assert result is True
        assert azure_jobs.job_status_store[job_id]["status"] == "cancelled"
    
    @pytest.mark.asyncio
    async def test_cancel_job_not_found(self):
        """Test cancel job that doesn't exist"""
        result = await azure_jobs.cancel_job("non-existent-job")
        assert result is False
    
    @pytest.mark.asyncio
    async def test_handle_job_callback(self):
        """Test handle job callback"""
        job_id = "test-job-id-3"
        azure_jobs.job_status_store[job_id] = {
            "job_id": job_id,
            "status": "pending",
            "progress": 0,
            "book_id": None,
            "error": None
        }
        
        await azure_jobs.handle_job_callback(job_id, "completed", book_id=123)
        assert azure_jobs.job_status_store[job_id]["status"] == "completed"
        assert azure_jobs.job_status_store[job_id]["book_id"] == 123
        assert azure_jobs.job_status_store[job_id]["progress"] == 100


class TestBookServiceEndpoints:
    """Tests for book-service endpoints"""
    
    def test_root_endpoint(self, client):
        """Test root/health check endpoint"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "book-service"
        assert data["status"] == "healthy"
    
    def test_generate_book(self, client):
        """Test generate book"""
        with patch.object(main, 'blob_client', Mock()):
            with patch.object(main, 'trigger_container_job', new_callable=AsyncMock) as mock_trigger:
                mock_trigger.return_value = "test-job-id"
                
                response = client.post(
                    "/api/books/generate",
                    json={
                        "level": "A1",
                        "genre": "fantasy",
                        "language": "Spanish",
                        "prompt": "A test story",
                    }
                )
                assert response.status_code == 200
                data = response.json()
                assert data["story_id"] is not None
                assert data["status"] == "processing"
    
    def test_get_job_status(self, client):
        """Test get job status"""
        with patch.object(main, 'blob_client') as mock_blob:
            # Mock final story blob check - returns found
            mock_blob_client = Mock()
            mock_blob.get_blob_client.return_value = mock_blob_client
            mock_blob_client.download_blob.return_value.readall.return_value.decode.return_value = json.dumps({"story_id": "test", "content": "xyz"})
            
            response = client.get(
                "/api/books/story_123/status"
            )
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "completed"
