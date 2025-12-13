"""
Shared pytest fixtures and utilities for all tests
"""
import os

# Set test environment variables FIRST - before any module imports
# These are required for service modules like database.py to pass validation
# The values don't matter because asyncpg/Azure are mocked - they just need to exist
os.environ.setdefault('DATABASE_URL', 'postgresql://test:test@localhost/test')
os.environ.setdefault('FIREBASE_SERVICE_ACCOUNT_KEY', '{"type": "service_account", "project_id": "test"}')
os.environ.setdefault('AZURE_STORAGE_CONNECTION_STRING', 'DefaultEndpointsProtocol=https;AccountName=test;AccountKey=test;EndpointSuffix=core.windows.net')
os.environ.setdefault('AZURE_STORAGE_ACCOUNT_NAME', 'test-account')
os.environ.setdefault('AZURE_STORAGE_CONTAINER_NAME', 'test-container')
os.environ.setdefault('AZURE_STORAGE_COVER_CONTAINER', 'test-covers')
os.environ.setdefault('AUTH_SERVICE_URL', 'http://auth-service')
os.environ.setdefault('DEV_MODE', 'true')

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from typing import AsyncGenerator
from datetime import datetime

# Try to import asyncpg, but don't fail if it's not installed
try:
    import asyncpg
except ImportError:
    asyncpg = None


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_db_pool():
    """Mock database connection pool"""
    # Create a mock spec if asyncpg is available, otherwise just use Mock
    spec = asyncpg.Pool if asyncpg else None
    pool = AsyncMock(spec=spec)
    conn = AsyncMock()
    
    # Mock connection methods
    conn.fetchrow = AsyncMock()
    conn.fetch = AsyncMock()
    conn.fetchval = AsyncMock()
    conn.execute = AsyncMock()
    
    # Mock pool.acquire to return connection
    async def acquire():
        return conn
    
    pool.acquire = acquire
    pool.fetchrow = AsyncMock()
    pool.fetch = AsyncMock()
    pool.fetchval = AsyncMock()
    pool.execute = AsyncMock()
    
    return pool, conn


@pytest.fixture
def mock_firebase_token():
    """Mock Firebase token data"""
    return {
        'uid': 'test-firebase-uid-123',
        'email': 'test@example.com',
        'email_verified': True,
        'name': 'Test User'
    }


@pytest.fixture
def mock_user_data():
    """Mock user data from database"""
    return {
        'id': 1,
        'firebase_uid': 'test-firebase-uid-123',
        'email': 'test@example.com',
        'display_name': 'Test User',
        'created_at': datetime(2024, 1, 1, 12, 0, 0),
        'updated_at': datetime(2024, 1, 1, 12, 0, 0)
    }


@pytest.fixture
def mock_auth_response():
    """Mock auth service response"""
    return {
        'user': {
            'id': 1,
            'firebase_uid': 'test-firebase-uid-123',
            'email': 'test@example.com',
            'display_name': 'Test User'
        },
        'message': 'User verified and synchronized'
    }


@pytest.fixture
def mock_httpx_client():
    """Mock httpx client for HTTP requests"""
    client = AsyncMock()
    response = Mock()
    response.status_code = 200
    response.json = Mock(return_value={})
    response.text = ""
    response.content = b""
    client.get = AsyncMock(return_value=response)
    client.post = AsyncMock(return_value=response)
    return client


@pytest.fixture
def mock_azure_blob_client():
    """Mock Azure Blob Storage client"""
    blob_client = AsyncMock()
    blob_client.upload_blob = AsyncMock()
    blob_client.download_blob = AsyncMock()
    blob_client.delete_blob = AsyncMock()
    blob_client.url = "https://test.blob.core.windows.net/container/blob"
    return blob_client


@pytest.fixture
def mock_azure_container_client():
    """Mock Azure Container client"""
    container_client = AsyncMock()
    container_client.get_container_properties = AsyncMock()
    container_client.create_container = AsyncMock()
    return container_client


@pytest.fixture
def mock_azure_blob_service_client(mock_azure_blob_client, mock_azure_container_client):
    """Mock Azure Blob Service Client"""
    service_client = Mock()
    service_client.get_blob_client = Mock(return_value=mock_azure_blob_client)
    service_client.get_container_client = Mock(return_value=mock_azure_container_client)
    return service_client

