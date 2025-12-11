from fastapi import FastAPI, HTTPException, Depends, status, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from contextlib import asynccontextmanager
import httpx
import os
from cachetools import TTLCache

from database import get_db_connection, close_db_connection

# Configuration
AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://localhost:8001")
LINGUEE_API_URL = os.getenv("LINGUEE_API_URL", "https://linguee-api.fly.dev/api/v2/translations")

# Translation cache (TTL: 1 hour, max 1000 entries)
translation_cache = TTLCache(maxsize=1000, ttl=3600)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await get_db_connection()
    yield
    # Shutdown
    await close_db_connection()

app = FastAPI(
    title="Translation Service",
    description="Word translation and vocabulary tracking microservice",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# Pydantic Models
# ==========================================

class TranslationRequest(BaseModel):
    word: str
    source_lang: str  # e.g., 'es' for Spanish
    target_lang: str = 'en'  # Default to English

class Translation(BaseModel):
    word: str
    translations: List[str]
    source_lang: str
    target_lang: str
    examples: Optional[List[dict]] = None

class VocabularyWord(BaseModel):
    id: int
    word: str
    translation: str
    language_code: str
    book_id: int
    hover_count: int
    last_seen_at: Optional[str]
    created_at: str

class SaveVocabularyRequest(BaseModel):
    word: str
    translation: str
    language_code: str
    book_id: int

# ==========================================
# Authentication Dependency
# ==========================================

async def verify_token(authorization: str = Header(...)) -> dict:
    """
    Verify JWT token with auth-service
    """
    try:
        if not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization header format"
            )
        
        token = authorization.split(" ")[1]
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{AUTH_SERVICE_URL}/api/auth/token/verify",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or expired token"
                )
            
            return response.json()
    
    except httpx.HTTPError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service unavailable"
        )

# ==========================================
# Helper Functions
# ==========================================

def get_language_code_mapping(language: str) -> str:
    """
    Map common language names to Linguee language codes
    """
    mapping = {
        'spanish': 'es',
        'french': 'fr',
        'german': 'de',
        'italian': 'it',
        'portuguese': 'pt',
        'russian': 'ru',
        'japanese': 'ja',
        'chinese': 'zh',
        'english': 'en'
    }
    return mapping.get(language.lower(), language.lower()[:2])

# ==========================================
# API Endpoints
# ==========================================

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "service": "translation-service",
        "status": "healthy",
        "timestamp": datetime.utcnow(),
        "cache_size": len(translation_cache)
    }

@app.get("/api/test-linguee")
async def test_linguee():
    """Test the Linguee API directly"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                LINGUEE_API_URL,
                params={
                    "query": "hello",
                    "src": "en",
                    "dst": "es",
                    "guess_direction": False
                }
            )
            
            return {
                "status_code": response.status_code,
                "linguee_api_url": LINGUEE_API_URL,
                "response_preview": response.text[:500] if response.text else "empty",
                "response_data": response.json() if response.status_code == 200 else None
            }
    except Exception as e:
        return {
            "error": str(e),
            "linguee_api_url": LINGUEE_API_URL
        }

@app.get("/api/translate", response_model=Translation)
async def translate_word(
    query: str = Query(..., description="Word or phrase to translate"),
    src: str = Query(..., description="Source language code (e.g., 'es', 'fr')"),
    dst: str = Query("en", description="Destination language code (default: 'en')"),
    auth_data: dict = Depends(verify_token)
):
    """
    Translate a word or phrase from source language to target language.
    Uses Linguee API for high-quality contextual translations.
    """
    
    # Check cache first
    cache_key = f"{src}:{dst}:{query.lower()}"
    
    if cache_key in translation_cache:
        print(f"[CACHE HIT] {cache_key}")
        return translation_cache[cache_key]
    
    try:
        # Call Linguee API
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                LINGUEE_API_URL,
                params={
                    "query": query,
                    "src": src,
                    "dst": dst,
                    "guess_direction": False
                }
            )
            
            if response.status_code != 200:
                print(f"[LINGUEE API ERROR] Status: {response.status_code}, Response: {response.text}")
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Translation API error: {response.text}"
                )
            
            data = response.json()
            print(f"[LINGUEE API RESPONSE] Query: {query}, Response type: {type(data)}, Length: {len(data) if isinstance(data, list) else 'N/A'}")
        
        # Parse Linguee response
        # The API returns an array of word entries
        translations = []
        examples = []
        
        if isinstance(data, list) and len(data) > 0:
            print(f"[PARSE] Found {len(data)} word entries")
            
            # Iterate through word entries (prioritize featured entries)
            for entry in data:
                if 'translations' in entry:
                    for trans in entry['translations']:
                        if 'text' in trans:
                            translations.append(trans['text'])
                        
                        # Collect examples from translations
                        if 'examples' in trans and trans['examples']:
                            for example in trans['examples'][:2]:  # Max 2 per translation
                                if 'src' in example and 'dst' in example:
                                    examples.append({
                                        'source': example['src'],
                                        'target': example['dst']
                                    })
                                    if len(examples) >= 3:  # Max 3 total examples
                                        break
                        
                        if len(examples) >= 3:
                            break
                
                # Stop after first entry if we have enough translations
                if len(translations) >= 5:
                    break
        
        # Fallback if no translations found
        if not translations:
            print(f"[PARSE] No translations found. Response preview: {str(data)[:500]}")
            translations = [f"[Translation not found for '{query}']"]
        else:
            print(f"[PARSE] Successfully extracted {len(translations)} translations")
        
        result = Translation(
            word=query,
            translations=translations[:5],  # Limit to top 5 translations
            source_lang=src,
            target_lang=dst,
            examples=examples if examples else None
        )
        
        # Cache the result
        translation_cache[cache_key] = result
        
        return result
        
    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Translation service unavailable: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Translation failed: {str(e)}"
        )

@app.post("/api/vocabulary", response_model=VocabularyWord, status_code=status.HTTP_201_CREATED)
async def save_vocabulary_word(
    request: SaveVocabularyRequest,
    auth_data: dict = Depends(verify_token)
):
    """
    Save a word to user's vocabulary list.
    If word already exists, increment hover_count.
    """
    conn = await get_db_connection()
    
    try:
        user_id = auth_data['user']['id']
        
        # Check if word already exists
        existing = await conn.fetchrow(
            """
            SELECT id, hover_count
            FROM vocabulary
            WHERE user_id = $1 AND book_id = $2 AND language_code = $3 AND word = $4
            """,
            user_id,
            request.book_id,
            request.language_code,
            request.word
        )
        
        if existing:
            # Update existing word
            vocab = await conn.fetchrow(
                """
                UPDATE vocabulary
                SET 
                    translation = $1,
                    hover_count = hover_count + 1,
                    last_seen_at = NOW(),
                    updated_at = NOW()
                WHERE id = $2
                RETURNING id, user_id, book_id, language_code, word, translation, 
                          hover_count, last_seen_at, created_at
                """,
                request.translation,
                existing['id']
            )
        else:
            # Insert new word
            vocab = await conn.fetchrow(
                """
                INSERT INTO vocabulary 
                    (user_id, book_id, language_code, word, translation, hover_count, last_seen_at, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, 1, NOW(), NOW(), NOW())
                RETURNING id, user_id, book_id, language_code, word, translation, 
                          hover_count, last_seen_at, created_at
                """,
                user_id,
                request.book_id,
                request.language_code,
                request.word,
                request.translation
            )
        
        return VocabularyWord(
            id=vocab['id'],
            word=vocab['word'],
            translation=vocab['translation'],
            language_code=vocab['language_code'],
            book_id=vocab['book_id'],
            hover_count=vocab['hover_count'],
            last_seen_at=vocab['last_seen_at'].isoformat() if vocab['last_seen_at'] else None,
            created_at=vocab['created_at'].isoformat()
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save vocabulary word: {str(e)}"
        )

@app.get("/api/vocabulary", response_model=List[VocabularyWord])
async def get_vocabulary_words(
    auth_data: dict = Depends(verify_token),
    book_id: Optional[int] = None,
    language: Optional[str] = None,
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0)
):
    """
    Get user's vocabulary words with optional filters.
    """
    conn = await get_db_connection()
    
    try:
        user_id = auth_data['user']['id']
        
        # Build query
        query = """
            SELECT id, user_id, book_id, language_code, word, translation,
                   hover_count, last_seen_at, created_at
            FROM vocabulary
            WHERE user_id = $1
        """
        
        params = [user_id]
        param_count = 2
        
        if book_id is not None:
            query += f" AND book_id = ${param_count}"
            params.append(book_id)
            param_count += 1
        
        if language:
            query += f" AND language_code = ${param_count}"
            params.append(get_language_code_mapping(language))
            param_count += 1
        
        query += f" ORDER BY last_seen_at DESC LIMIT ${param_count} OFFSET ${param_count + 1}"
        params.extend([limit, offset])
        
        words = await conn.fetch(query, *params)
        
        return [
            VocabularyWord(
                id=word['id'],
                word=word['word'],
                translation=word['translation'],
                language_code=word['language_code'],
                book_id=word['book_id'],
                hover_count=word['hover_count'],
                last_seen_at=word['last_seen_at'].isoformat() if word['last_seen_at'] else None,
                created_at=word['created_at'].isoformat()
            )
            for word in words
        ]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch vocabulary: {str(e)}"
        )

@app.delete("/api/vocabulary/{vocab_id}")
async def delete_vocabulary_word(
    vocab_id: int,
    auth_data: dict = Depends(verify_token)
):
    """
    Delete a vocabulary word from user's list.
    """
    conn = await get_db_connection()
    
    try:
        user_id = auth_data['user']['id']
        
        # Delete word (ensure it belongs to the user)
        result = await conn.execute(
            "DELETE FROM vocabulary WHERE id = $1 AND user_id = $2",
            vocab_id,
            user_id
        )
        
        if result == "DELETE 0":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vocabulary word not found"
            )
        
        return {"message": "Vocabulary word deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete vocabulary word: {str(e)}"
        )

@app.get("/api/vocabulary/stats")
async def get_vocabulary_stats(auth_data: dict = Depends(verify_token)):
    """
    Get vocabulary statistics for the user.
    """
    conn = await get_db_connection()
    
    try:
        user_id = auth_data['user']['id']
        
        # Total words
        total_words = await conn.fetchval(
            "SELECT COUNT(DISTINCT word) FROM vocabulary WHERE user_id = $1",
            user_id
        )
        
        # Words by language
        by_language = await conn.fetch(
            """
            SELECT language_code, COUNT(DISTINCT word) as count
            FROM vocabulary
            WHERE user_id = $1
            GROUP BY language_code
            ORDER BY count DESC
            """,
            user_id
        )
        
        # Most reviewed words
        most_reviewed = await conn.fetch(
            """
            SELECT word, translation, language_code, hover_count
            FROM vocabulary
            WHERE user_id = $1
            ORDER BY hover_count DESC
            LIMIT 10
            """,
            user_id
        )
        
        return {
            "total_words": total_words or 0,
            "by_language": [
                {"language": row['language_code'], "count": row['count']}
                for row in by_language
            ],
            "most_reviewed": [
                {
                    "word": row['word'],
                    "translation": row['translation'],
                    "language": row['language_code'],
                    "hover_count": row['hover_count']
                }
                for row in most_reviewed
            ]
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch vocabulary stats: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004)

