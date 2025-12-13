"""
Unit tests for user-service
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import HTTPException
from datetime import datetime
import sys
import os

# Set dummy env vars for tests (must be before imports)
os.environ['DATABASE_URL'] = "postgresql://test:test@localhost/test"
os.environ['FIREBASE_SERVICE_ACCOUNT_KEY'] = '{"type": "service_account"}'

# Mock asyncpg before importing modules that use it
sys.modules['asyncpg'] = MagicMock()
sys.modules['asyncpg'].create_pool = AsyncMock()

import importlib.util

# Load user-service modules in correct order with UNIQUE names
user_service_path = os.path.join(os.path.dirname(__file__), '..', 'services', 'user-service')
sys.path.insert(0, user_service_path)

# IMPORTANT: Load database.py FIRST and register with unique name
db_spec = importlib.util.spec_from_file_location("user_service_database", os.path.join(user_service_path, "database.py"))
user_service_database = importlib.util.module_from_spec(db_spec)
sys.modules["user_service_database"] = user_service_database
db_spec.loader.exec_module(user_service_database)

# NOW load main.py with unique name  
spec = importlib.util.spec_from_file_location("user_service_main", os.path.join(user_service_path, "main.py"))
user_service_main = importlib.util.module_from_spec(spec)
sys.modules["user_service_main"] = user_service_main
spec.loader.exec_module(user_service_main)

from user_service_main import app
import user_service_main as main  # Alias for patch.object convenience
import user_service_database as user_database
from contextlib import contextmanager

@contextmanager
def mock_db(conn):
    with patch.object(main, 'get_db_connection', new_callable=AsyncMock) as mock_get:
        mock_get.return_value = conn
        yield mock_get


@pytest.fixture
def client(mock_auth_response):
    """Create test client"""
    from user_service_main import verify_token
    
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
            'email': 'test@example.com',
            'display_name': 'Test User'
        }
    }


class TestUserServiceDatabase:
    """Tests for user-service database.py"""
    
    @pytest.mark.asyncio
    async def test_get_db_connection_success(self):
        """Test successful database connection"""
        with patch('asyncpg.create_pool', new_callable=AsyncMock) as mock_create_pool:
            mock_pool = AsyncMock()
            mock_create_pool.return_value = mock_pool
            with patch.dict(os.environ, {'DATABASE_URL': 'postgresql://test:test@localhost/test'}):
                user_database.pool = None
                result = await user_database.get_db_connection()
                assert result is not None
    
    @pytest.mark.asyncio
    async def test_get_db_connection_missing_url(self):
        """Test database connection with missing URL"""
        with patch.dict(os.environ, {}, clear=True):
            user_database.pool = None
            with pytest.raises(ValueError, match="DATABASE_URL"):
                await user_database.get_db_connection()
    
    @pytest.mark.asyncio
    async def test_get_db_connection_reuse_pool(self):
        """Test database connection reuses existing pool"""
        mock_pool = AsyncMock()
        user_database.pool = mock_pool
        result = await user_database.get_db_connection()
        assert result == mock_pool
        user_database.pool = None  # Reset
    
    @pytest.mark.asyncio
    async def test_close_db_connection(self):
        """Test closing database connection"""
        mock_pool = AsyncMock()
        user_database.pool = mock_pool
        await user_database.close_db_connection()
        mock_pool.close.assert_called_once()
        user_database.pool = None  # Reset
    
    @pytest.mark.asyncio
    async def test_close_db_connection_no_pool(self):
        """Test closing database connection when pool is None"""
        user_database.pool = None
        await user_database.close_db_connection()
        assert user_database.pool is None


class TestUserServiceEndpoints:
    """Tests for user-service endpoints"""
    
    def test_root_endpoint(self, client):
        """Test root/health check endpoint"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "user-service"
        assert data["status"] == "healthy"
    
    def test_get_current_user_profile(self, client, mock_auth_response, mock_db_pool):
        """Test get current user profile"""
        pool, conn = mock_db_pool
        mock_user = {
            'id': 1,
            'email': 'test@example.com',
            'display_name': 'Test User',
            'created_at': datetime(2024, 1, 1),
            'updated_at': datetime(2024, 1, 1)
        }
        conn.fetchrow = AsyncMock(return_value=mock_user)
        
        with patch('main.verify_token', new_callable=AsyncMock, return_value=mock_auth_response):
            with mock_db(conn):
                response = client.get(
                    "/api/users/me",
                    headers={"Authorization": "Bearer test-token"}
                )
                assert response.status_code == 200
                data = response.json()
                assert data["email"] == 'test@example.com'
    
    def test_get_current_user_profile_not_found(self, client, mock_auth_response, mock_db_pool):
        """Test get current user profile when user not found"""
        pool, conn = mock_db_pool
        conn.fetchrow = AsyncMock(return_value=None)
        
        with patch('main.verify_token', new_callable=AsyncMock, return_value=mock_auth_response):
            with mock_db(conn):
                response = client.get(
                    "/api/users/me",
                    headers={"Authorization": "Bearer test-token"}
                )
                assert response.status_code == 404
    
    def test_update_user_profile(self, client, mock_auth_response, mock_db_pool):
        """Test update user profile"""
        pool, conn = mock_db_pool
        updated_user = {
            'id': 1,
            'email': 'test@example.com',
            'display_name': 'Updated Name',
            'created_at': datetime(2024, 1, 1),
            'updated_at': datetime(2024, 1, 2)
        }
        conn.fetchrow = AsyncMock(return_value=updated_user)
        conn.execute = AsyncMock()
        
        with patch.object(main, 'verify_token', new_callable=AsyncMock, return_value=mock_auth_response):
            with mock_db(conn):
                # Mock the get_current_user_profile function that's called at the end
                with patch.object(main, 'get_current_user_profile', new_callable=AsyncMock) as mock_get_profile:
                    mock_get_profile.return_value = {
                        'id': 1,
                        'email': 'test@example.com',
                        'display_name': 'Updated Name',
                        'created_at': datetime(2024, 1, 1).isoformat(),
                        'updated_at': datetime(2024, 1, 2).isoformat()
                    }
                    response = client.put(
                        "/api/users/me",
                        json={"display_name": "Updated Name"},
                        headers={"Authorization": "Bearer test-token"}
                    )
                    assert response.status_code == 200
    
    def test_update_user_profile_no_fields(self, client, mock_auth_response, mock_db_pool):
        """Test update user profile with no fields"""
        pool, conn = mock_db_pool
        with patch.object(main, 'verify_token', new_callable=AsyncMock, return_value=mock_auth_response):
            with mock_db(conn):
                response = client.put(
                    "/api/users/me",
                    json={},
                    headers={"Authorization": "Bearer test-token"}
                )
                # Should fail validation or return 400
                assert response.status_code in [400, 422]
    
    def test_get_user_stats(self, client, mock_auth_response, mock_db_pool):
        """Test get user statistics"""
        pool, conn = mock_db_pool
        conn.fetchval = AsyncMock(side_effect=[5, 2, 100])  # total_books, favorite_books, total_words
        conn.fetch = AsyncMock(return_value=[{'language_code': 'es'}, {'language_code': 'fr'}])
        
        with patch('main.verify_token', new_callable=AsyncMock, return_value=mock_auth_response):
            with mock_db(conn):
                response = client.get(
                    "/api/users/me/stats",
                    headers={"Authorization": "Bearer test-token"}
                )
                assert response.status_code == 200
                data = response.json()
                assert data["total_books"] == 5
                assert data["favorite_books"] == 2
                assert data["total_words_learned"] == 100
                assert len(data["languages_learning"]) == 2
    
    def test_delete_user_account(self, client, mock_auth_response, mock_db_pool):
        """Test delete user account"""
        pool, conn = mock_db_pool
        conn.execute = AsyncMock(return_value="DELETE 1")
        
        with patch('main.verify_token', new_callable=AsyncMock, return_value=mock_auth_response):
            with mock_db(conn):
                response = client.delete(
                    "/api/users/me",
                    headers={"Authorization": "Bearer test-token"}
                )
                assert response.status_code == 200
                data = response.json()
                assert "message" in data
    
    def test_verify_token_invalid_format(self, client):
        """Test verify token with invalid format"""
        response = client.get(
            "/api/users/me",
            headers={"Authorization": "InvalidFormat"}
        )
        assert response.status_code == 401
    
    def test_verify_token_service_unavailable(self, client, mock_db_pool):
        """Test verify token when auth service is unavailable"""
        import httpx
        from user_service_main import verify_token
        
        # Remove dependency override to test the real verify_token function
        app.dependency_overrides.pop(verify_token, None)
        
        pool, conn = mock_db_pool
        with patch('httpx.AsyncClient') as mock_client:
            # Create a mock request to pass to ConnectError
            mock_request = Mock()
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=httpx.ConnectError("Service unavailable", request=mock_request)
            )
            with mock_db(conn):
                response = client.get(
                    "/api/users/me",
                    headers={"Authorization": "Bearer test-token"}
                )
            assert response.status_code == 503
    
    def test_get_current_user_profile_exception(self, client, mock_auth_response, mock_db_pool):
        """Test get current user profile with exception"""
        pool, conn = mock_db_pool
        conn.fetchrow = AsyncMock(side_effect=Exception("Database error"))
        
        with patch('main.verify_token', new_callable=AsyncMock, return_value=mock_auth_response):
            with mock_db(conn):
                response = client.get(
                    "/api/users/me",
                    headers={"Authorization": "Bearer test-token"}
                )
                assert response.status_code == 500
    
    def test_update_user_profile_exception(self, client, mock_auth_response, mock_db_pool):
        """Test update user profile with exception"""
        pool, conn = mock_db_pool
        conn.fetchrow = AsyncMock(side_effect=Exception("Database error"))
        
        with patch('main.verify_token', new_callable=AsyncMock, return_value=mock_auth_response):
            with mock_db(conn):
                response = client.put(
                    "/api/users/me",
                    json={"display_name": "Updated Name"},
                    headers={"Authorization": "Bearer test-token"}
                )
                assert response.status_code == 500
    
    def test_update_user_profile_not_found(self, client, mock_auth_response, mock_db_pool):
        """Test update user profile when user not found"""
        pool, conn = mock_db_pool
        conn.fetchrow = AsyncMock(return_value=None)
        
        with patch('main.verify_token', new_callable=AsyncMock, return_value=mock_auth_response):
            with mock_db(conn):
                response = client.put(
                    "/api/users/me",
                    json={"display_name": "Updated Name"},
                    headers={"Authorization": "Bearer test-token"}
                )
                assert response.status_code == 404
    
    def test_get_user_stats_exception(self, client, mock_auth_response, mock_db_pool):
        """Test get user stats with exception"""
        pool, conn = mock_db_pool
        conn.fetchval = AsyncMock(side_effect=Exception("Database error"))
        
        with patch('main.verify_token', new_callable=AsyncMock, return_value=mock_auth_response):
            with mock_db(conn):
                response = client.get(
                    "/api/users/me/stats",
                    headers={"Authorization": "Bearer test-token"}
                )
                assert response.status_code == 500
    
    def test_delete_user_account_exception(self, client, mock_auth_response, mock_db_pool):
        """Test delete user account with exception"""
        pool, conn = mock_db_pool
        conn.execute = AsyncMock(side_effect=Exception("Database error"))
        
        with patch('main.verify_token', new_callable=AsyncMock, return_value=mock_auth_response):
            with mock_db(conn):
                response = client.delete(
                    "/api/users/me",
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
        import httpx
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=httpx.HTTPError("Connection error")
            )
            
            with pytest.raises(HTTPException) as exc_info:
                await verify_token("Bearer test-token")
            assert exc_info.value.status_code == 503

