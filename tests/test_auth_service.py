"""
Unit tests for auth-service
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

# Mock dependencies (conditionally to avoid overwriting if shared across tests)
for mod in ['asyncpg', 'firebase_admin', 'firebase_admin.credentials', 'firebase_admin.auth']:
    if mod not in sys.modules or not isinstance(sys.modules[mod], MagicMock):
        sys.modules[mod] = MagicMock()
        if mod == 'asyncpg':
             sys.modules[mod].create_pool = AsyncMock()

# Set environment variables BEFORE importing app modules ensures they pass validation
import os
os.environ["DATABASE_URL"] = "postgresql://test:test@localhost/testdb"
os.environ["FIREBASE_SERVICE_ACCOUNT_KEY"] = '{"type": "service_account", "project_id": "test"}'

import importlib.util

# Load auth-service modules in correct order
auth_service_path = os.path.join(os.path.dirname(__file__), '..', 'services', 'auth-service')
sys.path.insert(0, auth_service_path)

# IMPORTANT: Load database.py FIRST and register it as 'database' so main.py can import it
db_spec = importlib.util.spec_from_file_location("database", os.path.join(auth_service_path, "database.py"))
auth_service_database = importlib.util.module_from_spec(db_spec)
sys.modules["database"] = auth_service_database  # Register as 'database' so main.py can import it
sys.modules["auth_service_database"] = auth_service_database  # Also register with full name
db_spec.loader.exec_module(auth_service_database)

# NOW load main.py (it will find 'database' in sys.modules)
spec = importlib.util.spec_from_file_location("auth_service_main", os.path.join(auth_service_path, "main.py"))
auth_service_main = importlib.util.module_from_spec(spec)
sys.modules["auth_service_main"] = auth_service_main
spec.loader.exec_module(auth_service_main)

# Import from the loaded module
from auth_service_main import app, get_or_create_user, verify_auth_header
import auth_service_main as main  # Alias for patch.object convenience
import auth_service_database as auth_database  # Alias for test usage
import firebase_config
from contextlib import contextmanager

from dotenv import load_dotenv
load_dotenv()

@contextmanager
def mock_db(conn):
    # main.py calls `conn = await get_db_connection()` and then `conn.fetchrow(...)` directly
    # So get_db_connection should return the connection object (not a pool that needs acquire)
    with patch.object(main, 'get_db_connection', new_callable=AsyncMock) as mock_get:
        mock_get.return_value = conn
        yield mock_get


@pytest.fixture
def client():
    """Create test client"""
    # Simply set the env var to satisfy validation. 
    # Global asyncpg mock handles the actual connection creation.
    os.environ["DATABASE_URL"] = "postgresql://test:test@localhost/test"
    
    with TestClient(app) as c:
        yield c


@pytest.fixture
def mock_db_connection(mock_db_pool):
    """Mock database connection"""
    pool, conn = mock_db_pool
    with patch('services.auth-service.database.get_db_connection', return_value=pool):
        with patch.object(main, 'get_db_connection', return_value=pool):
            yield pool, conn


class TestDatabase:
    """Tests for database.py"""
    
    @pytest.mark.asyncio
    async def test_get_db_connection_success(self):
        """Test successful database connection"""
        with patch('asyncpg.create_pool', new_callable=AsyncMock) as mock_create_pool:
            mock_pool = AsyncMock()
            mock_create_pool.return_value = mock_pool
            with patch.dict(os.environ, {'DATABASE_URL': 'postgresql://test:test@localhost/test'}):
                # Reset the pool to None before testing
                auth_database.pool = None
                result = await auth_database.get_db_connection()
                assert result is not None
    
    @pytest.mark.asyncio
    async def test_get_db_connection_missing_url(self):
        """Test database connection with missing URL"""
        with patch.dict(os.environ, {}, clear=True):
            auth_database.pool = None
            with pytest.raises(ValueError, match="DATABASE_URL"):
                await auth_database.get_db_connection()
    
    @pytest.mark.asyncio
    async def test_get_db_connection_reuse_pool(self):
        """Test database connection reuses existing pool"""
        mock_pool = AsyncMock()
        auth_database.pool = mock_pool
        result = await auth_database.get_db_connection()
        assert result == mock_pool
        auth_database.pool = None  # Reset
    
    @pytest.mark.asyncio
    async def test_close_db_connection(self):
        """Test closing database connection"""
        mock_pool = AsyncMock()
        auth_database.pool = mock_pool
        await auth_database.close_db_connection()
        mock_pool.close.assert_called_once()
        auth_database.pool = None  # Reset
    
    @pytest.mark.asyncio
    async def test_close_db_connection_no_pool(self):
        """Test closing database connection when pool is None"""
        auth_database.pool = None
        await auth_database.close_db_connection()
        assert auth_database.pool is None


class TestFirebaseConfig:
    """Tests for firebase_config.py"""
    
    def test_initialize_firebase_with_env_key(self):
        """Test Firebase initialization with environment key"""
        mock_cred = Mock()
        mock_app = Mock()
        
        with patch('firebase_admin.credentials.Certificate', return_value=mock_cred):
            with patch('firebase_admin.initialize_app', return_value=mock_app):
                with patch.dict(os.environ, {'FIREBASE_SERVICE_ACCOUNT_KEY': '{"type": "service_account"}'}):
                    firebase_config._firebase_app = None
                    result = firebase_config.initialize_firebase()
                    assert result == mock_app
                    firebase_config._firebase_app = None  # Reset
    
    def test_initialize_firebase_with_file_path(self):
        """Test Firebase initialization with file path"""
        mock_cred = Mock()
        mock_app = Mock()
        
        with patch('firebase_admin.credentials.Certificate', return_value=mock_cred):
            with patch('firebase_admin.initialize_app', return_value=mock_app):
                with patch.dict(os.environ, {'FIREBASE_SERVICE_ACCOUNT_PATH': '/path/to/key.json'}):
                    firebase_config._firebase_app = None
                    result = firebase_config.initialize_firebase()
                    assert result == mock_app
                    firebase_config._firebase_app = None  # Reset
    
    def test_initialize_firebase_no_credentials(self):
        """Test Firebase initialization without credentials"""
        with patch.dict(os.environ, {}, clear=True):
            firebase_config._firebase_app = None
            result = firebase_config.initialize_firebase()
            assert result is None
    
    def test_verify_firebase_token_success(self, mock_firebase_token):
        """Test successful Firebase token verification"""
        with patch('firebase_config.auth.verify_id_token', return_value=mock_firebase_token):
            result = firebase_config.verify_firebase_token('valid-token')
            assert result == mock_firebase_token
    
    def test_verify_firebase_token_invalid(self):
        """Test Firebase token verification with invalid token"""
        with patch('firebase_config.auth.verify_id_token', side_effect=ValueError('Invalid token')):
            with pytest.raises(ValueError, match="Invalid Firebase token"):
                firebase_config.verify_firebase_token('invalid-token')
    
    def test_get_firebase_user_success(self):
        """Test getting Firebase user"""
        mock_user = Mock()
        mock_user.uid = 'test-uid'
        mock_user.email = 'test@example.com'
        mock_user.email_verified = True
        mock_user.display_name = 'Test User'
        mock_user.photo_url = None
        mock_user.disabled = False
        
        with patch('firebase_config.auth.get_user', return_value=mock_user):
            result = firebase_config.get_firebase_user('test-uid')
            assert result['uid'] == 'test-uid'
            assert result['email'] == 'test@example.com'
    
    def test_get_firebase_user_not_found(self):
        """Test getting Firebase user that doesn't exist"""
        with patch('firebase_config.auth.get_user', side_effect=Exception('User not found')):
            with pytest.raises(ValueError, match="Failed to get Firebase user"):
                firebase_config.get_firebase_user('non-existent-uid')
    
    def test_initialize_firebase_already_initialized(self):
        """Test Firebase initialization when already initialized"""
        mock_app = Mock()
        firebase_config._firebase_app = mock_app
        result = firebase_config.initialize_firebase()
        assert result == mock_app
        firebase_config._firebase_app = None  # Reset
    
    def test_create_custom_token_success(self):
        """Test create custom token successfully"""
        mock_token = b"custom-token-string"
        with patch('firebase_config.auth.create_custom_token', return_value=mock_token):
            result = firebase_config.create_custom_token('test-uid')
            assert result == "custom-token-string"
    
    def test_create_custom_token_error(self):
        """Test create custom token with error"""
        with patch('firebase_config.auth.create_custom_token', side_effect=Exception('Error')):
            with pytest.raises(ValueError, match="Failed to create custom token"):
                firebase_config.create_custom_token('test-uid')


class TestAuthServiceEndpoints:
    """Tests for auth-service endpoints"""
    
    def test_root_endpoint(self, client):
        """Test root/health check endpoint"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "auth-service (Firebase)"
        assert data["status"] == "healthy"
    
    @pytest.mark.asyncio
    async def test_verify_and_sync_user_new_user(self, mock_db_pool, mock_firebase_token):
        """Test verifying and syncing a new user"""
        pool, conn = mock_db_pool
        
        # Mock user doesn't exist initially
        new_user = {
            'id': 1,
            'firebase_uid': mock_firebase_token['uid'],
            'email': mock_firebase_token['email'],
            'display_name': 'Test User',
            'created_at': datetime(2024, 1, 1),
            'updated_at': datetime(2024, 1, 1)
        }
        conn.fetchrow = AsyncMock(side_effect=[None, new_user])
        
        with mock_db(conn):
            result = await get_or_create_user(
                mock_firebase_token['uid'],
                mock_firebase_token['email'],
                'Test User'
            )
            assert result['id'] == 1
            assert result['email'] == mock_firebase_token['email']
    
    @pytest.mark.asyncio
    async def test_verify_and_sync_user_existing(self, mock_db_pool, mock_firebase_token):
        """Test verifying and syncing an existing user"""
        pool, conn = mock_db_pool
        
        existing_user = {
            'id': 1,
            'firebase_uid': mock_firebase_token['uid'],
            'email': mock_firebase_token['email'],
            'display_name': 'Existing User',
            'created_at': datetime(2024, 1, 1),
            'updated_at': datetime(2024, 1, 1)
        }
        conn.fetchrow = AsyncMock(return_value=existing_user)
        
        with mock_db(conn):
            result = await get_or_create_user(
                mock_firebase_token['uid'],
                mock_firebase_token['email']
            )
            assert result['id'] == 1
            assert result['email'] == mock_firebase_token['email']
    
    @pytest.mark.asyncio
    async def test_verify_auth_header_success(self, mock_firebase_token):
        """Test successful auth header verification"""
        with patch.object(main, 'verify_firebase_token', return_value=mock_firebase_token):
            result = await verify_auth_header("Bearer valid-token")
            assert result == mock_firebase_token
    
    @pytest.mark.asyncio
    async def test_verify_auth_header_invalid_format(self):
        """Test auth header with invalid format"""
        with pytest.raises(HTTPException) as exc_info:
            await verify_auth_header("InvalidFormat")
        assert exc_info.value.status_code == 401
    
    @pytest.mark.asyncio
    async def test_verify_auth_header_invalid_token(self):
        """Test auth header with invalid token"""
        with patch.object(main, 'verify_firebase_token', side_effect=ValueError("Invalid token")):
            with pytest.raises(HTTPException) as exc_info:
                await verify_auth_header("Bearer invalid-token")
            assert exc_info.value.status_code == 401
    
    def test_verify_and_sync_user_endpoint(self, client, mock_firebase_token):
        """Test verify and sync user endpoint"""
        with patch.object(main, 'verify_firebase_token', return_value=mock_firebase_token):
            with patch.object(main, 'get_or_create_user', new_callable=AsyncMock) as mock_get_user:
                mock_get_user.return_value = {
                    'id': 1,
                    'firebase_uid': mock_firebase_token['uid'],
                    'email': mock_firebase_token['email'],
                    'display_name': 'Test User',
                    'created_at': datetime(2024, 1, 1),
                    'updated_at': datetime(2024, 1, 1)
                }
                
                response = client.post(
                    "/api/auth/verify",
                    json={"id_token": "test-token", "display_name": "Test User"}
                )
                assert response.status_code == 200
                data = response.json()
                assert data["user"]["email"] == mock_firebase_token['email']
    
    def test_get_current_user_endpoint(self, client, mock_firebase_token, mock_user_data, mock_db_pool):
        """Test get current user endpoint"""
        with patch.object(main, 'verify_auth_header', new_callable=AsyncMock) as mock_verify:
            mock_verify.return_value = mock_firebase_token
            pool, conn = mock_db_pool
            conn.fetchrow = AsyncMock(return_value=mock_user_data)
            with mock_db(conn):
                response = client.get(
                    "/api/auth/me",
                    headers={"Authorization": "Bearer test-token"}
                )
                assert response.status_code == 200
                data = response.json()
                assert data["email"] == mock_user_data['email']
    
    def test_get_current_user_not_found(self, client, mock_firebase_token, mock_db_pool):
        """Test get current user when user not found"""
        with patch.object(main, 'verify_auth_header', new_callable=AsyncMock) as mock_verify:
            mock_verify.return_value = mock_firebase_token
            pool, conn = mock_db_pool
            conn.fetchrow = AsyncMock(return_value=None)
            with mock_db(conn):
                response = client.get(
                    "/api/auth/me",
                    headers={"Authorization": "Bearer test-token"}
                )
                assert response.status_code == 404
    
    def test_get_firebase_user_info_endpoint(self, client, mock_firebase_token):
        """Test get Firebase user info endpoint"""
        mock_user_info = {
            'uid': 'test-firebase-uid-123',
            'email': 'test@example.com',
            'email_verified': True
        }
        
        with patch.object(main, 'verify_firebase_token', return_value=mock_firebase_token):
            with patch.object(main, 'get_firebase_user', return_value=mock_user_info):
                response = client.get(
                    "/api/auth/firebase-user/test-firebase-uid-123",
                    headers={"Authorization": "Bearer test-token"}
                )
                assert response.status_code == 200
    
    def test_get_firebase_user_info_forbidden(self, client, mock_firebase_token):
        """Test get Firebase user info for different user"""
        with patch.object(main, 'verify_auth_header', new_callable=AsyncMock) as mock_verify:
            mock_verify.return_value = mock_firebase_token
            
            response = client.get(
                "/api/auth/firebase-user/different-uid",
                headers={"Authorization": "Bearer test-token"}
            )
            assert response.status_code == 403
    
    def test_legacy_login_endpoint(self, client):
        """Test legacy login endpoint"""
        response = client.post("/api/auth/login")
        assert response.status_code == 410
    
    def test_legacy_signup_endpoint(self, client):
        """Test legacy signup endpoint"""
        response = client.post("/api/auth/signup")
        assert response.status_code == 410
    
    @pytest.mark.asyncio
    async def test_verify_and_sync_user_no_email(self, mock_firebase_token):
        """Test verify and sync user when email is missing from token"""
        token_without_email = mock_firebase_token.copy()
        token_without_email.pop('email')
        
        with patch.object(main, 'verify_firebase_token', return_value=token_without_email):
            client = TestClient(app)
            response = client.post(
                "/api/auth/verify",
                json={"id_token": "test-token"}
            )
            assert response.status_code == 400
    
    @pytest.mark.asyncio
    async def test_verify_and_sync_user_exception(self):
        """Test verify and sync user with exception"""
        with patch.object(main, 'verify_firebase_token', side_effect=Exception("Unexpected error")):
            client = TestClient(app)
            response = client.post(
                "/api/auth/verify",
                json={"id_token": "test-token"}
            )
            assert response.status_code == 500
    
    @pytest.mark.asyncio
    async def test_get_current_user_exception(self, mock_firebase_token, mock_db_pool):
        """Test get current user with exception"""
        pool, conn = mock_db_pool
        conn.fetchrow = AsyncMock(side_effect=Exception("Database error"))
        
        with patch.object(main, 'verify_auth_header', new_callable=AsyncMock) as mock_verify:
            mock_verify.return_value = mock_firebase_token
            with mock_db(conn):
                client = TestClient(app)
                response = client.get(
                    "/api/auth/me",
                    headers={"Authorization": "Bearer test-token"}
                )
                assert response.status_code == 500
    
    @pytest.mark.asyncio
    async def test_get_firebase_user_info_exception(self, mock_firebase_token):
        """Test get Firebase user info with exception"""
        with patch.object(main, 'verify_firebase_token', return_value=mock_firebase_token):
            with patch.object(main, 'get_firebase_user', side_effect=ValueError("User not found")):
                client = TestClient(app)
                response = client.get(
                    "/api/auth/firebase-user/test-firebase-uid-123",
                    headers={"Authorization": "Bearer test-token"}
                )
                assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_verify_auth_header_exception(self):
        """Test verify auth header with general exception"""
        with patch.object(main, 'verify_firebase_token', side_effect=Exception("Unexpected error")):
            with pytest.raises(HTTPException) as exc_info:
                await verify_auth_header("Bearer invalid-token")
            assert exc_info.value.status_code == 401
    
    @pytest.mark.asyncio
    async def test_get_or_create_user_with_display_name(self, mock_db_pool, mock_firebase_token):
        """Test get_or_create_user with display_name"""
        pool, conn = mock_db_pool
        new_user = {
            'id': 1,
            'firebase_uid': mock_firebase_token['uid'],
            'email': mock_firebase_token['email'],
            'display_name': 'Custom Name',
            'created_at': datetime(2024, 1, 1),
            'updated_at': datetime(2024, 1, 1)
        }
        conn.fetchrow = AsyncMock(side_effect=[None, new_user])
        
        with mock_db(conn):
            result = await get_or_create_user(
                mock_firebase_token['uid'],
                mock_firebase_token['email'],
                'Custom Name'
            )
            assert result['display_name'] == 'Custom Name'
    
    @pytest.mark.asyncio
    async def test_get_or_create_user_default_display_name(self, mock_db_pool, mock_firebase_token):
        """Test get_or_create_user with default display_name from email"""
        pool, conn = mock_db_pool
        new_user = {
            'id': 1,
            'firebase_uid': mock_firebase_token['uid'],
            'email': 'testuser@example.com',
            'display_name': 'testuser',
            'created_at': datetime(2024, 1, 1),
            'updated_at': datetime(2024, 1, 1)
        }
        conn.fetchrow = AsyncMock(side_effect=[None, new_user])
        
        with mock_db(conn):
            result = await get_or_create_user(
                mock_firebase_token['uid'],
                'testuser@example.com'
            )
            assert result['display_name'] == 'testuser'

