"""
Unit tests for translation-service
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from datetime import datetime
import sys
import os

# Mock dependencies before importing modules that use them
sys.modules['asyncpg'] = MagicMock()
# cachetools is usually available, but mock it if needed
try:
    import cachetools
except ImportError:
    sys.modules['cachetools'] = MagicMock()

# Add translation-service to path (must be first to avoid conflicts)
translation_service_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'services', 'translation-service'))
# Remove any conflicting paths first
if translation_service_path in sys.path:
    sys.path.remove(translation_service_path)
sys.path.insert(0, translation_service_path)

from main import app, get_language_code_mapping, verify_token, translation_cache
import database as translation_database
from contextlib import contextmanager
from contextlib import contextmanager
from fastapi import HTTPException
import httpx

@contextmanager
def mock_auth(response):
    app.dependency_overrides[verify_token] = lambda: response
    yield
    app.dependency_overrides = {}

@contextmanager
def mock_db(conn):
    with patch('main.get_db_connection', new_callable=AsyncMock) as mock_get:
        mock_get.return_value = conn
        yield mock_get


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

@pytest.fixture(autouse=True)
def clear_cache():
    """Clear translation cache before each test"""
    translation_cache.clear()
    yield
    translation_cache.clear()


class TestTranslationServiceDatabase:
    """Tests for translation-service database.py"""
    
    @pytest.mark.asyncio
    async def test_get_db_connection_success(self):
        """Test successful database connection"""
        with patch('asyncpg.create_pool', new_callable=AsyncMock) as mock_create_pool:
            mock_pool = AsyncMock()
            mock_create_pool.return_value = mock_pool
            with patch.dict(os.environ, {'DATABASE_URL': 'postgresql://test:test@localhost/test'}):
                translation_database.pool = None
                result = await translation_database.get_db_connection()
                assert result is not None
    
    @pytest.mark.asyncio
    async def test_get_db_connection_missing_url(self):
        """Test database connection with missing URL"""
        with patch.dict(os.environ, {}, clear=True):
            translation_database.pool = None
            with pytest.raises(ValueError, match="DATABASE_URL"):
                await translation_database.get_db_connection()
    
    @pytest.mark.asyncio
    async def test_get_db_connection_reuse_pool(self):
        """Test database connection reuses existing pool"""
        mock_pool = AsyncMock()
        translation_database.pool = mock_pool
        result = await translation_database.get_db_connection()
        assert result == mock_pool
        translation_database.pool = None  # Reset
    
    @pytest.mark.asyncio
    async def test_close_db_connection(self):
        """Test closing database connection"""
        mock_pool = AsyncMock()
        translation_database.pool = mock_pool
        await translation_database.close_db_connection()
        mock_pool.close.assert_called_once()
        translation_database.pool = None  # Reset
    
    @pytest.mark.asyncio
    async def test_close_db_connection_no_pool(self):
        """Test closing database connection when pool is None"""
        translation_database.pool = None
        await translation_database.close_db_connection()
        assert translation_database.pool is None


class TestTranslationServiceHelpers:
    """Tests for helper functions"""
    
    def test_get_language_code_mapping(self):
        """Test language code mapping"""
        assert get_language_code_mapping('spanish') == 'es'
        assert get_language_code_mapping('french') == 'fr'
        assert get_language_code_mapping('german') == 'de'
        assert get_language_code_mapping('italian') == 'it'
        assert get_language_code_mapping('english') == 'en'
        assert get_language_code_mapping('unknown') == 'un'  # First 2 chars


class TestTranslationServiceEndpoints:
    """Tests for translation-service endpoints"""
    
    def test_root_endpoint(self, client):
        """Test root/health check endpoint"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "translation-service"
        assert data["status"] == "healthy"
    
    def test_translate_word_success(self, client, mock_auth_response):
        """Test translate word successfully"""
        mock_linguee_response = [
            {
                'translations': [
                    {'text': 'hello', 'examples': [{'src': 'Hola mundo', 'dst': 'Hello world'}]},
                    {'text': 'hi'}
                ]
            }
        ]
        
        with mock_auth(mock_auth_response):
            with patch('httpx.AsyncClient') as mock_client:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = mock_linguee_response
                mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
                
                response = client.get(
                    "/api/translate?query=hola&src=es&dst=en",
                    headers={"Authorization": "Bearer test-token"}
                )
                assert response.status_code == 200
                data = response.json()
                assert data["word"] == "hola"
                assert len(data["translations"]) > 0
    
    def test_translate_word_cache_hit(self, client, mock_auth_response):
        """Test translate word with cache hit"""
        # First request to populate cache
        mock_linguee_response = [
            {
                'translations': [{'text': 'hello'}]
            }
        ]
        
        with mock_auth(mock_auth_response):
            with patch('httpx.AsyncClient') as mock_client:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = mock_linguee_response
                mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
                
                # First request
                response1 = client.get(
                    "/api/translate?query=hola&src=es&dst=en",
                    headers={"Authorization": "Bearer test-token"}
                )
                assert response1.status_code == 200
    
    def test_translate_word_no_matches(self, client, mock_auth_response):
        """Test translate word with no matches"""
        mock_linguee_response = []
        
        with mock_auth(mock_auth_response):
            with patch('httpx.AsyncClient') as mock_client:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = mock_linguee_response
                mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
                
                response = client.get(
                    "/api/translate?query=xyz&src=es&dst=en",
                    headers={"Authorization": "Bearer test-token"}
                )
                assert response.status_code == 200
                data = response.json()
                assert "[Translation not found" in data["translations"][0]
    
    def test_save_vocabulary_word_new(self, client, mock_auth_response, mock_db_pool):
        """Test save new vocabulary word"""
        pool, conn = mock_db_pool
        conn.fetchrow = AsyncMock(return_value=None)  # Word doesn't exist
        
        new_vocab = {
            'id': 1,
            'user_id': 1,
            'book_id': 1,
            'language_code': 'es',
            'word': 'hola',
            'translation': 'hello',
            'hover_count': 1,
            'last_seen_at': datetime(2024, 1, 1),
            'created_at': datetime(2024, 1, 1)
        }
        conn.fetchrow = AsyncMock(side_effect=[None, new_vocab])
        
        with mock_auth(mock_auth_response):
            with mock_db(conn):
                response = client.post(
                    "/api/vocabulary",
                    json={
                        "word": "hola",
                        "translation": "hello",
                        "language_code": "es",
                        "book_id": 1
                    },
                    headers={"Authorization": "Bearer test-token"}
                )
                assert response.status_code == 201
                data = response.json()
                assert data["word"] == "hola"
    
    def test_save_vocabulary_word_existing(self, client, mock_auth_response, mock_db_pool):
        """Test save existing vocabulary word (increment hover_count)"""
        pool, conn = mock_db_pool
        existing = {'id': 1, 'hover_count': 5}
        updated_vocab = {
            'id': 1,
            'user_id': 1,
            'book_id': 1,
            'language_code': 'es',
            'word': 'hola',
            'translation': 'hello',
            'hover_count': 6,
            'last_seen_at': datetime(2024, 1, 1),
            'created_at': datetime(2024, 1, 1)
        }
        conn.fetchrow = AsyncMock(side_effect=[existing, updated_vocab])
        
        with mock_auth(mock_auth_response):
            with mock_db(conn):
                response = client.post(
                    "/api/vocabulary",
                    json={
                        "word": "hola",
                        "translation": "hello",
                        "language_code": "es",
                        "book_id": 1
                    },
                    headers={"Authorization": "Bearer test-token"}
                )
                assert response.status_code == 201
                data = response.json()
                assert data["hover_count"] == 6
    
    def test_get_vocabulary_words(self, client, mock_auth_response, mock_db_pool):
        """Test get vocabulary words"""
        pool, conn = mock_db_pool
        mock_words = [
            {
                'id': 1,
                'user_id': 1,
                'book_id': 1,
                'language_code': 'es',
                'word': 'hola',
                'translation': 'hello',
                'hover_count': 5,
                'last_seen_at': datetime(2024, 1, 1),
                'created_at': datetime(2024, 1, 1)
            }
        ]
        conn.fetch = AsyncMock(return_value=mock_words)
        
        with mock_auth(mock_auth_response):
            with mock_db(conn):
                response = client.get(
                    "/api/vocabulary",
                    headers={"Authorization": "Bearer test-token"}
                )
                assert response.status_code == 200
                data = response.json()
                assert len(data) == 1
                assert data[0]["word"] == "hola"
    
    def test_get_vocabulary_words_with_filters(self, client, mock_auth_response, mock_db_pool):
        """Test get vocabulary words with filters"""
        pool, conn = mock_db_pool
        conn.fetch = AsyncMock(return_value=[])
        
        with mock_auth(mock_auth_response):
            with mock_db(conn):
                response = client.get(
                    "/api/vocabulary?book_id=1&language=spanish&limit=50&offset=0",
                    headers={"Authorization": "Bearer test-token"}
                )
                assert response.status_code == 200
    
    def test_delete_vocabulary_word(self, client, mock_auth_response, mock_db_pool):
        """Test delete vocabulary word"""
        pool, conn = mock_db_pool
        conn.execute = AsyncMock(return_value="DELETE 1")
        
        with mock_auth(mock_auth_response):
            with mock_db(conn):
                response = client.delete(
                    "/api/vocabulary/1",
                    headers={"Authorization": "Bearer test-token"}
                )
                assert response.status_code == 200
    
    def test_delete_vocabulary_word_not_found(self, client, mock_auth_response, mock_db_pool):
        """Test delete vocabulary word that doesn't exist"""
        pool, conn = mock_db_pool
        conn.execute = AsyncMock(return_value="DELETE 0")
        
        with mock_auth(mock_auth_response):
            with mock_db(conn):
                response = client.delete(
                    "/api/vocabulary/999",
                    headers={"Authorization": "Bearer test-token"}
                )
                assert response.status_code == 404
    
    def test_get_vocabulary_stats(self, client, mock_auth_response, mock_db_pool):
        """Test get vocabulary statistics"""
        pool, conn = mock_db_pool
        conn.fetchval = AsyncMock(return_value=100)
        conn.fetch = AsyncMock(side_effect=[
            [{'language_code': 'es', 'count': 50}, {'language_code': 'fr', 'count': 50}],
            [
                {'word': 'hola', 'translation': 'hello', 'language_code': 'es', 'hover_count': 10}
            ]
        ])
        
        with mock_auth(mock_auth_response):
            with mock_db(conn):
                response = client.get(
                    "/api/vocabulary/stats",
                    headers={"Authorization": "Bearer test-token"}
                )
                assert response.status_code == 200
                data = response.json()
                assert data["total_words"] == 100
                assert len(data["by_language"]) == 2
    
    def test_translate_word_http_error(self, client, mock_auth_response):
        """Test translate word when HTTP error occurs"""
        import httpx
        
        with mock_auth(mock_auth_response):
            with patch('httpx.AsyncClient') as mock_client:
                mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                    side_effect=httpx.HTTPError("Connection error")
                )
                
                response = client.get(
                    "/api/translate?query=hola&src=es&dst=en",
                    headers={"Authorization": "Bearer test-token"}
                )
                assert response.status_code == 503
    
    def test_translate_word_api_error(self, client, mock_auth_response):
        """Test translate word when API returns error"""
        with mock_auth(mock_auth_response):
            with patch('httpx.AsyncClient') as mock_client:
                mock_response = Mock()
                mock_response.status_code = 500
                mock_response.text = "Internal Server Error"
                mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
                
                response = client.get(
                    "/api/translate?query=hola&src=es&dst=en",
                    headers={"Authorization": "Bearer test-token"}
                )
                assert response.status_code == 500
    
    def test_translate_word_other_results(self, client, mock_auth_response):
        """Test translate word with other_results"""
        mock_linguee_response = [
            {
                'translations': [
                    {'text': 'hello'},
                    {'text': 'hi'}
                ]
            }
        ]
        
        with mock_auth(mock_auth_response):
            with patch('httpx.AsyncClient') as mock_client:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = mock_linguee_response
                mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
                
                response = client.get(
                    "/api/translate?query=hola&src=es&dst=en",
                    headers={"Authorization": "Bearer test-token"}
                )
                assert response.status_code == 200
                data = response.json()
                assert len(data["translations"]) > 0
    
    def test_translate_word_with_examples(self, client, mock_auth_response):
        """Test translate word with examples"""
        mock_linguee_response = [
            {
                'translations': [
                    {
                        'text': 'hello',
                        'examples': [
                            {'src': 'Hola mundo', 'dst': 'Hello world'},
                            {'src': 'Hola amigo', 'dst': 'Hello friend'}
                        ]
                    }
                ]
            }
        ]
        
        with mock_auth(mock_auth_response):
            with patch('httpx.AsyncClient') as mock_client:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = mock_linguee_response
                mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
                
                response = client.get(
                    "/api/translate?query=hola&src=es&dst=en",
                    headers={"Authorization": "Bearer test-token"}
                )
                assert response.status_code == 200
                data = response.json()
                assert data["examples"] is not None
                assert len(data["examples"]) == 2
    
    def test_save_vocabulary_word_exception(self, client, mock_auth_response, mock_db_pool):
        """Test save vocabulary word with exception"""
        pool, conn = mock_db_pool
        conn.fetchrow = AsyncMock(side_effect=Exception("Database error"))
        
        with mock_auth(mock_auth_response):
            with mock_db(conn):
                response = client.post(
                    "/api/vocabulary",
                    json={
                        "word": "hola",
                        "translation": "hello",
                        "language_code": "es",
                        "book_id": 1
                    },
                    headers={"Authorization": "Bearer test-token"}
                )
                assert response.status_code == 500
    
    def test_get_vocabulary_words_exception(self, client, mock_auth_response, mock_db_pool):
        """Test get vocabulary words with exception"""
        pool, conn = mock_db_pool
        conn.fetch = AsyncMock(side_effect=Exception("Database error"))
        
        with mock_auth(mock_auth_response):
            with mock_db(conn):
                response = client.get(
                    "/api/vocabulary",
                    headers={"Authorization": "Bearer test-token"}
                )
                assert response.status_code == 500
    
    def test_get_vocabulary_stats_exception(self, client, mock_auth_response, mock_db_pool):
        """Test get vocabulary stats with exception"""
        pool, conn = mock_db_pool
        conn.fetchval = AsyncMock(side_effect=Exception("Database error"))
        
        with mock_auth(mock_auth_response):
            with mock_db(conn):
                response = client.get(
                    "/api/vocabulary/stats",
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

