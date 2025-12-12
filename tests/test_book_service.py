"""
Unit tests for book-service
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from datetime import datetime
import sys
import os

# Mock dependencies before importing modules that use them
sys.modules['asyncpg'] = MagicMock()
sys.modules['azure'] = MagicMock()
sys.modules['azure.storage'] = MagicMock()
sys.modules['azure.storage.blob'] = MagicMock()
sys.modules['azure.identity'] = MagicMock()
sys.modules['azure.mgmt'] = MagicMock()
sys.modules['azure.mgmt.containerinstance'] = MagicMock()

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'services', 'book-service'))

from main import app
import database as book_database
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
    with patch('main.get_db_connection', new_callable=AsyncMock) as mock_main_pool:
        mock_main_pool.return_value = conn
        with patch('database.get_db_connection', new_callable=AsyncMock) as mock_db_pool:
            mock_db_pool.return_value = conn
            print(f"DEBUG: Patched main.get_db_connection & database.get_db_connection")
            yield mock_main_pool
    print("DEBUG: Exiting mock_db")


@pytest.fixture
def client(mock_auth_response):
    """Create test client"""
    from main import verify_token
    
    # Override the verify_token dependency for all tests
    async def mock_verify_token_override(authorization: str = None):
        return mock_auth_response
    
    app.dependency_overrides = {}
    app.dependency_overrides[verify_token] = mock_verify_token_override
    
    yield TestClient(app)
    
    # Clean up
    app.dependency_overrides.clear()


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
    async def test_delete_from_blob(self, mock_azure_blob_service_client):
        """Test delete from blob storage"""
        with patch('azure.storage.blob.BlobServiceClient.from_connection_string', return_value=mock_azure_blob_service_client):
            with patch.dict(os.environ, {'AZURE_STORAGE_CONNECTION_STRING': 'test-connection-string'}):
                result = await blob_storage.delete_from_blob("https://test.blob.core.windows.net/container/blob.txt")
                assert result is True
    
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
    async def test_upload_to_blob_create_container(self, mock_azure_blob_service_client, mock_azure_container_client):
        """Test upload to blob with container creation"""
        mock_azure_container_client.get_container_properties = AsyncMock(side_effect=Exception("Not found"))
        mock_azure_container_client.create_container = AsyncMock()
        
        with patch('azure.storage.blob.BlobServiceClient.from_connection_string', return_value=mock_azure_blob_service_client):
            with patch.dict(os.environ, {'AZURE_STORAGE_CONNECTION_STRING': 'test-connection-string'}):
                result = await blob_storage.upload_to_blob(
                    b"test content",
                    "test.txt",
                    "text/plain"
                )
                assert result is not None
                mock_azure_container_client.create_container.assert_called_once()
    
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
    async def test_delete_from_blob_with_blob_name(self, mock_azure_blob_service_client):
        """Test delete from blob with just blob name"""
        with patch('azure.storage.blob.BlobServiceClient.from_connection_string', return_value=mock_azure_blob_service_client):
            with patch.dict(os.environ, {'AZURE_STORAGE_CONNECTION_STRING': 'test-connection-string'}):
                result = await blob_storage.delete_from_blob("blob.txt")
                assert result is True
    
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
    
    def test_generate_book(self, client, mock_auth_response):
        """Test generate book"""
        with patch('main.verify_token', new_callable=AsyncMock, return_value=mock_auth_response):
            with patch('main.trigger_story_generation_job', new_callable=AsyncMock) as mock_trigger:
                mock_trigger.return_value = "test-job-id"
                
                response = client.post(
                    "/api/books/generate",
                    json={
                        "level": "A1",
                        "genre": "fantasy",
                        "language": "Spanish",
                        "prompt": "A test story",
                        "is_pro": False
                    },
                    headers={"Authorization": "Bearer test-token"}
                )
                assert response.status_code == 200
                data = response.json()
                assert data["job_id"] == "test-job-id"
                assert data["status"] == "pending"
    
    def test_get_job_status(self, client, mock_auth_response):
        """Test get job status"""
        with patch('main.verify_token', new_callable=AsyncMock, return_value=mock_auth_response):
            with patch('main.check_job_status', new_callable=AsyncMock) as mock_check:
                mock_check.return_value = {
                    "job_id": "test-job-id",
                    "status": "completed",
                    "progress": 100,
                    "book_id": 1,
                    "error": None
                }
                
                response = client.get(
                    "/api/books/jobs/test-job-id",
                    headers={"Authorization": "Bearer test-token"}
                )
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "completed"
    
    def test_get_user_books(self, client, mock_auth_response, mock_db_pool):
        """Test get user books"""
        pool, conn = mock_db_pool
        mock_books = [
            {
                'id': 1,
                'title': 'Test Book',
                'description': 'A test book',
                'text_blob_url': 'https://test.blob.core.windows.net/book.json',
                'cover_image_url': 'https://test.blob.core.windows.net/cover.png',
                'language_code': 'es',
                'level': 'A1',
                'genre': 'fantasy',
                'is_pro_book': False,
                'pages_estimate': 10,
                'created_at': datetime(2024, 1, 1),
                'updated_at': datetime(2024, 1, 1),
                'is_owner': True,
                'is_favorite': False,
                'last_opened_at': None,
                'progress_percent': None
            }
        ]
        conn.fetch = AsyncMock(return_value=mock_books)
        
        with patch('main.verify_token', new_callable=AsyncMock, return_value=mock_auth_response):
            with mock_db(conn):
                response = client.get(
                    "/api/books",
                    headers={"Authorization": "Bearer test-token"}
                )
                assert response.status_code == 200
                data = response.json()
                assert len(data) == 1
                assert data[0]["title"] == "Test Book"
    
    def test_get_book_details(self, client, mock_auth_response, mock_db_pool):
        """Test get book details"""
        pool, conn = mock_db_pool
        mock_book = {
            'id': 1,
            'title': 'Test Book',
            'description': 'A test book',
            'text_blob_url': 'https://test.blob.core.windows.net/book.json',
            'cover_image_url': 'https://test.blob.core.windows.net/cover.png',
            'language_code': 'es',
            'level': 'A1',
            'genre': 'fantasy',
            'is_pro_book': False,
            'pages_estimate': 10,
            'created_at': datetime(2024, 1, 1),
            'updated_at': datetime(2024, 1, 1),
            'is_owner': True,
            'is_favorite': False,
            'last_opened_at': None,
            'progress_percent': None
        }
        conn.fetchrow = AsyncMock(return_value=mock_book)
        conn.execute = AsyncMock()
        
        with patch('main.verify_token', new_callable=AsyncMock, return_value=mock_auth_response):
            with mock_db(conn):
                response = client.get(
                    "/api/books/1",
                    headers={"Authorization": "Bearer test-token"}
                )
                assert response.status_code == 200
                data = response.json()
                assert data["title"] == "Test Book"
    
    def test_get_book_content(self, client, mock_auth_response, mock_db_pool):
        """Test get book content"""
        pool, conn = mock_db_pool
        mock_book = {
            'id': 1,
            'title': 'Test Book',
            'text_blob_url': 'https://test.blob.core.windows.net/book.json'
        }
        conn.fetchrow = AsyncMock(return_value=mock_book)
        
        mock_content = {
            'pages': [
                {'id': 1, 'content': 'Page 1 content'},
                {'id': 2, 'content': 'Page 2 content'}
            ]
        }
        
        with patch('main.verify_token', new_callable=AsyncMock, return_value=mock_auth_response):
            with mock_db(conn):
                with patch('httpx.AsyncClient') as mock_client:
                    mock_response = Mock()
                    mock_response.status_code = 200
                    mock_response.json.return_value = mock_content
                    mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
                    
                    response = client.get(
                        "/api/books/1/content",
                        headers={"Authorization": "Bearer test-token"}
                    )
                    assert response.status_code == 200
                    data = response.json()
                    assert data["book_id"] == 1
                    assert len(data["pages"]) == 2
    
    def test_update_user_book(self, client, mock_auth_response, mock_db_pool):
        """Test update user book"""
        pool, conn = mock_db_pool
        conn.execute = AsyncMock()
        
        # Mock get_book_details call
        mock_book = {
            'id': 1,
            'title': 'Test Book',
            'description': 'A test book',
            'text_blob_url': 'https://test.blob.core.windows.net/book.json',
            'cover_image_url': None,
            'language_code': 'es',
            'level': 'A1',
            'genre': 'fantasy',
            'is_pro_book': False,
            'pages_estimate': 10,
            'created_at': datetime(2024, 1, 1).isoformat(),
            'updated_at': datetime(2024, 1, 1).isoformat(),
            'is_owner': True,
            'is_favorite': True,
            'last_opened_at': datetime(2024, 1, 1).isoformat(),
            'progress_percent': 50.0
        }
        
        with patch('main.verify_token', new_callable=AsyncMock, return_value=mock_auth_response):
            with mock_db(conn):
                with patch('main.get_book_details', new_callable=AsyncMock) as mock_get_details:
                    mock_get_details.return_value = mock_book
                    response = client.put(
                        "/api/books/1",
                        json={"is_favorite": True, "progress_percent": 50.0},
                        headers={"Authorization": "Bearer test-token"}
                    )
                    assert response.status_code == 200
    
    def test_delete_book(self, client, mock_auth_response, mock_db_pool):
        """Test delete book"""
        pool, conn = mock_db_pool
        mock_user_book = {
            'is_owner': True,
            'text_blob_url': 'https://test.blob.core.windows.net/book.json',
            'cover_image_url': None
        }
        conn.fetchrow = AsyncMock(return_value=mock_user_book)
        conn.execute = AsyncMock()
        
        with patch('main.verify_token', new_callable=AsyncMock, return_value=mock_auth_response):
            with mock_db(conn):
                with patch('main.delete_from_blob', new_callable=AsyncMock) as mock_delete:
                    mock_delete.return_value = True
                    response = client.delete(
                        "/api/books/1",
                        headers={"Authorization": "Bearer test-token"}
                    )
                    assert response.status_code == 200
    
    def test_delete_book_not_owner(self, client, mock_auth_response, mock_db_pool):
        """Test delete book when user is not owner"""
        pool, conn = mock_db_pool
        mock_user_book = {
            'is_owner': False,
            'text_blob_url': None,
            'cover_image_url': None
        }
        conn.fetchrow = AsyncMock(return_value=mock_user_book)
        
        with patch('main.verify_token', new_callable=AsyncMock, return_value=mock_auth_response):
            with mock_db(conn):
                response = client.delete(
                    "/api/books/1",
                    headers={"Authorization": "Bearer test-token"}
                )
                assert response.status_code == 403
    
    def test_get_user_books_with_filters(self, client, mock_auth_response, mock_db_pool):
        """Test get user books with all filters"""
        pool, conn = mock_db_pool
        conn.fetch = AsyncMock(return_value=[])
        
        with patch('main.verify_token', new_callable=AsyncMock, return_value=mock_auth_response):
            with mock_db(conn):
                response = client.get(
                    "/api/books?language=es&level=A1&genre=fantasy&favorites_only=true",
                    headers={"Authorization": "Bearer test-token"}
                )
                assert response.status_code == 200
    
    def test_get_book_details_not_found(self, client, mock_auth_response, mock_db_pool):
        """Test get book details when book not found"""
        pool, conn = mock_db_pool
        conn.fetchrow = AsyncMock(return_value=None)
        
        with patch('main.verify_token', new_callable=AsyncMock, return_value=mock_auth_response):
            with mock_db(conn):
                response = client.get(
                    "/api/books/999",
                    headers={"Authorization": "Bearer test-token"}
                )
                assert response.status_code == 404
    
    def test_get_book_content_not_found(self, client, mock_auth_response, mock_db_pool):
        """Test get book content when book not found"""
        pool, conn = mock_db_pool
        conn.fetchrow = AsyncMock(return_value=None)
        
        with patch('main.verify_token', new_callable=AsyncMock, return_value=mock_auth_response):
            with mock_db(conn):
                response = client.get(
                    "/api/books/999/content",
                    headers={"Authorization": "Bearer test-token"}
                )
                assert response.status_code == 404
    
    def test_get_book_content_blob_error(self, client, mock_auth_response, mock_db_pool):
        """Test get book content when blob fetch fails"""
        pool, conn = mock_db_pool
        mock_book = {
            'id': 1,
            'title': 'Test Book',
            'text_blob_url': 'https://test.blob.core.windows.net/book.json'
        }
        conn.fetchrow = AsyncMock(return_value=mock_book)
        
        with patch('main.verify_token', new_callable=AsyncMock, return_value=mock_auth_response):
            with mock_db(conn):
                with patch('httpx.AsyncClient') as mock_client:
                    mock_response = Mock()
                    mock_response.status_code = 500
                    mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
                    
                    response = client.get(
                        "/api/books/1/content",
                        headers={"Authorization": "Bearer test-token"}
                    )
                    assert response.status_code == 500
    
    def test_update_user_book_no_fields(self, client, mock_auth_response, mock_db_pool):
        """Test update user book with no fields"""
        pool, conn = mock_db_pool
        with patch('main.verify_token', new_callable=AsyncMock, return_value=mock_auth_response):
            with mock_db(conn):
                response = client.put(
                    "/api/books/1",
                    json={},
                    headers={"Authorization": "Bearer test-token"}
                )
                assert response.status_code == 400
    
    def test_delete_book_not_found(self, client, mock_auth_response, mock_db_pool):
        """Test delete book when book not found"""
        pool, conn = mock_db_pool
        conn.fetchrow = AsyncMock(return_value=None)
        
        with patch('main.verify_token', new_callable=AsyncMock, return_value=mock_auth_response):
            with mock_db(conn):
                response = client.delete(
                    "/api/books/999",
                    headers={"Authorization": "Bearer test-token"}
                )
                assert response.status_code == 404
    
    def test_generate_book_exception(self, client, mock_auth_response):
        """Test generate book with exception"""
        with patch('main.verify_token', new_callable=AsyncMock, return_value=mock_auth_response):
            with patch('main.trigger_story_generation_job', new_callable=AsyncMock, side_effect=Exception("Error")):
                response = client.post(
                    "/api/books/generate",
                    json={
                        "level": "A1",
                        "genre": "fantasy",
                        "language": "Spanish",
                        "prompt": "A test story",
                        "is_pro": False
                    },
                    headers={"Authorization": "Bearer test-token"}
                )
                assert response.status_code == 500
    
    def test_get_job_status_exception(self, client, mock_auth_response):
        """Test get job status with exception"""
        with patch('main.verify_token', new_callable=AsyncMock, return_value=mock_auth_response):
            with patch('main.check_job_status', new_callable=AsyncMock, side_effect=Exception("Error")):
                response = client.get(
                    "/api/books/jobs/test-job-id",
                    headers={"Authorization": "Bearer test-token"}
                )
                assert response.status_code == 500
    
    @pytest.mark.asyncio
    async def test_verify_token_invalid_format(self):
        """Test verify token with invalid format"""
        from main import verify_token
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await verify_token("InvalidFormat")
        assert exc_info.value.status_code == 401
    
    @pytest.mark.asyncio
    async def test_verify_token_service_error(self):
        """Test verify token when auth service returns error"""
        from main import verify_token
        from fastapi import HTTPException
        import httpx
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 401
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            
            with pytest.raises(HTTPException) as exc_info:
                await verify_token("Bearer test-token")
            assert exc_info.value.status_code == 401
    
    @pytest.mark.asyncio
    async def test_verify_token_http_error(self):
        """Test verify token when HTTP error occurs"""
        from main import verify_token
        from fastapi import HTTPException
        import httpx
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=httpx.HTTPError("Connection error")
            )
            
            with pytest.raises(HTTPException) as exc_info:
                await verify_token("Bearer test-token")
            assert exc_info.value.status_code == 503

