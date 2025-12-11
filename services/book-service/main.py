from fastapi import FastAPI, HTTPException, Depends, status, Header, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from contextlib import asynccontextmanager
import httpx
import os
import json
import uuid

from database import get_db_connection, close_db_connection
from azure_jobs import trigger_story_generation_job, check_job_status
from blob_storage import upload_to_blob, get_blob_url, delete_from_blob

# Configuration
AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://localhost:8001")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await get_db_connection()
    yield
    # Shutdown
    await close_db_connection()

app = FastAPI(
    title="Book Service",
    description="Book generation and library management microservice",
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

class BookGenerationRequest(BaseModel):
    level: str  # A1, A2, B1, B2, C1, C2
    genre: str  # fantasy, sci-fi, adventure, mystery, slice-of-life
    language: str  # Spanish, French, German, Italian, Japanese, Chinese
    prompt: str
    is_pro: bool = False  # Free = 10 pages, Pro = up to 100 pages

class BookGenerationResponse(BaseModel):
    job_id: str
    status: str
    message: str

class BookJobStatus(BaseModel):
    job_id: str
    status: str  # pending, processing, completed, failed
    progress: Optional[int] = None  # 0-100
    book_id: Optional[int] = None
    error: Optional[str] = None

class Book(BaseModel):
    id: int
    title: str
    description: Optional[str]
    text_blob_url: str
    cover_image_url: Optional[str]
    language_code: str
    level: Optional[str]
    genre: Optional[str]
    is_pro_book: bool
    pages_estimate: Optional[int]
    created_at: str
    updated_at: str
    # User-specific fields from user_books
    is_owner: bool = True
    is_favorite: bool = False
    last_opened_at: Optional[str] = None
    progress_percent: Optional[float] = None

class BookPage(BaseModel):
    page_number: int
    content: str

class BookContent(BaseModel):
    book_id: int
    title: str
    pages: List[BookPage]

class UserBookUpdate(BaseModel):
    is_favorite: Optional[bool] = None
    progress_percent: Optional[float] = None

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
# API Endpoints
# ==========================================

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"service": "book-service", "status": "healthy", "timestamp": datetime.utcnow()}

@app.post("/api/books/generate", response_model=BookGenerationResponse)
async def generate_book(
    request: BookGenerationRequest,
    auth_data: dict = Depends(verify_token)
):
    """
    Trigger Azure Job to generate a new book/story
    This is async - returns a job_id that can be polled for status
    """
    try:
        user_id = auth_data['user']['id']
        
        # Determine page count based on pro status
        pages_estimate = 100 if request.is_pro else 10
        
        # Create job payload
        job_payload = {
            "user_id": user_id,
            "title": request.prompt[:100],  # Use prompt as initial title
            "language_code": request.language.lower()[:10],
            "level": request.level,
            "genre": request.genre,
            "prompt": request.prompt,
            "is_pro_book": request.is_pro,
            "pages_estimate": pages_estimate
        }
        
        # Trigger Azure Container Job
        job_id = await trigger_story_generation_job(job_payload)
        
        return BookGenerationResponse(
            job_id=job_id,
            status="pending",
            message=f"Story generation job started. Use /api/books/jobs/{job_id} to check status."
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger book generation: {str(e)}"
        )

@app.get("/api/books/jobs/{job_id}", response_model=BookJobStatus)
async def get_job_status(
    job_id: str,
    auth_data: dict = Depends(verify_token)
):
    """
    Check the status of a book generation job
    """
    try:
        status_data = await check_job_status(job_id)
        return BookJobStatus(**status_data)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check job status: {str(e)}"
        )

@app.get("/api/books", response_model=List[Book])
async def get_user_books(
    auth_data: dict = Depends(verify_token),
    language: Optional[str] = None,
    level: Optional[str] = None,
    genre: Optional[str] = None,
    favorites_only: bool = False
):
    """
    Get all books for the current user with optional filters
    """
    conn = await get_db_connection()
    
    try:
        user_id = auth_data['user']['id']
        
        # Build query with filters
        query = """
            SELECT 
                b.id, b.title, b.description, b.text_blob_url, b.cover_image_url,
                b.language_code, b.level, b.genre, b.is_pro_book, b.pages_estimate,
                b.created_at, b.updated_at,
                ub.is_owner, ub.is_favorite, ub.last_opened_at, ub.progress_percent
            FROM books b
            JOIN user_books ub ON b.id = ub.book_id
            WHERE ub.user_id = $1
        """
        
        params = [user_id]
        param_count = 2
        
        if language:
            query += f" AND b.language_code = ${param_count}"
            params.append(language.lower())
            param_count += 1
        
        if level:
            query += f" AND b.level = ${param_count}"
            params.append(level)
            param_count += 1
        
        if genre:
            query += f" AND b.genre = ${param_count}"
            params.append(genre)
            param_count += 1
        
        if favorites_only:
            query += " AND ub.is_favorite = TRUE"
        
        query += " ORDER BY b.created_at DESC"
        
        books = await conn.fetch(query, *params)
        
        return [
            Book(
                id=book['id'],
                title=book['title'],
                description=book['description'],
                text_blob_url=book['text_blob_url'],
                cover_image_url=book['cover_image_url'],
                language_code=book['language_code'],
                level=book['level'],
                genre=book['genre'],
                is_pro_book=book['is_pro_book'],
                pages_estimate=book['pages_estimate'],
                created_at=book['created_at'].isoformat(),
                updated_at=book['updated_at'].isoformat(),
                is_owner=book['is_owner'],
                is_favorite=book['is_favorite'],
                last_opened_at=book['last_opened_at'].isoformat() if book['last_opened_at'] else None,
                progress_percent=float(book['progress_percent']) if book['progress_percent'] else None
            )
            for book in books
        ]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch books: {str(e)}"
        )

@app.get("/api/books/{book_id}", response_model=Book)
async def get_book_details(
    book_id: int,
    auth_data: dict = Depends(verify_token)
):
    """
    Get details of a specific book
    """
    conn = await get_db_connection()
    
    try:
        user_id = auth_data['user']['id']
        
        book = await conn.fetchrow(
            """
            SELECT 
                b.id, b.title, b.description, b.text_blob_url, b.cover_image_url,
                b.language_code, b.level, b.genre, b.is_pro_book, b.pages_estimate,
                b.created_at, b.updated_at,
                ub.is_owner, ub.is_favorite, ub.last_opened_at, ub.progress_percent
            FROM books b
            JOIN user_books ub ON b.id = ub.book_id
            WHERE b.id = $1 AND ub.user_id = $2
            """,
            book_id,
            user_id
        )
        
        if not book:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Book not found or access denied"
            )
        
        # Update last_opened_at
        await conn.execute(
            """
            UPDATE user_books
            SET last_opened_at = NOW()
            WHERE user_id = $1 AND book_id = $2
            """,
            user_id,
            book_id
        )
        
        return Book(
            id=book['id'],
            title=book['title'],
            description=book['description'],
            text_blob_url=book['text_blob_url'],
            cover_image_url=book['cover_image_url'],
            language_code=book['language_code'],
            level=book['level'],
            genre=book['genre'],
            is_pro_book=book['is_pro_book'],
            pages_estimate=book['pages_estimate'],
            created_at=book['created_at'].isoformat(),
            updated_at=book['updated_at'].isoformat(),
            is_owner=book['is_owner'],
            is_favorite=book['is_favorite'],
            last_opened_at=datetime.utcnow().isoformat(),
            progress_percent=float(book['progress_percent']) if book['progress_percent'] else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch book details: {str(e)}"
        )

@app.get("/api/books/{book_id}/content", response_model=BookContent)
async def get_book_content(
    book_id: int,
    auth_data: dict = Depends(verify_token)
):
    """
    Get the full content of a book (download from blob storage and parse)
    """
    conn = await get_db_connection()
    
    try:
        user_id = auth_data['user']['id']
        
        # Verify access
        book = await conn.fetchrow(
            """
            SELECT b.id, b.title, b.text_blob_url
            FROM books b
            JOIN user_books ub ON b.id = ub.book_id
            WHERE b.id = $1 AND ub.user_id = $2
            """,
            book_id,
            user_id
        )
        
        if not book:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Book not found or access denied"
            )
        
        # Download content from blob storage
        blob_url = book['text_blob_url']
        
        # Fetch content from blob storage
        async with httpx.AsyncClient() as client:
            response = await client.get(blob_url)
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to fetch book content from storage"
                )
            
            content_data = response.json()
        
        # Parse pages
        pages = [
            BookPage(page_number=page['id'], content=page['content'])
            for page in content_data.get('pages', [])
        ]
        
        return BookContent(
            book_id=book['id'],
            title=book['title'],
            pages=pages
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch book content: {str(e)}"
        )

@app.put("/api/books/{book_id}", response_model=Book)
async def update_user_book(
    book_id: int,
    request: UserBookUpdate,
    auth_data: dict = Depends(verify_token)
):
    """
    Update user-specific book data (favorite, progress)
    """
    conn = await get_db_connection()
    
    try:
        user_id = auth_data['user']['id']
        
        # Build update query
        updates = []
        values = []
        param_count = 1
        
        if request.is_favorite is not None:
            updates.append(f"is_favorite = ${param_count}")
            values.append(request.is_favorite)
            param_count += 1
        
        if request.progress_percent is not None:
            updates.append(f"progress_percent = ${param_count}")
            values.append(request.progress_percent)
            param_count += 1
        
        if not updates:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields to update"
            )
        
        values.extend([user_id, book_id])
        
        query = f"""
            UPDATE user_books
            SET {', '.join(updates)}
            WHERE user_id = ${param_count} AND book_id = ${param_count + 1}
        """
        
        await conn.execute(query, *values)
        
        # Return updated book
        return await get_book_details(book_id, auth_data)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update book: {str(e)}"
        )

@app.delete("/api/books/{book_id}")
async def delete_book(
    book_id: int,
    auth_data: dict = Depends(verify_token)
):
    """
    Delete a book (only if user is owner)
    """
    conn = await get_db_connection()
    
    try:
        user_id = auth_data['user']['id']
        
        # Check if user is owner
        user_book = await conn.fetchrow(
            """
            SELECT ub.is_owner, b.text_blob_url, b.cover_image_url
            FROM user_books ub
            JOIN books b ON ub.book_id = b.id
            WHERE ub.user_id = $1 AND ub.book_id = $2
            """,
            user_id,
            book_id
        )
        
        if not user_book:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Book not found"
            )
        
        if not user_book['is_owner']:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the owner can delete this book"
            )
        
        # Delete from blob storage
        if user_book['text_blob_url']:
            await delete_from_blob(user_book['text_blob_url'])
        
        if user_book['cover_image_url']:
            await delete_from_blob(user_book['cover_image_url'])
        
        # Delete from database (CASCADE will handle user_books and vocabulary)
        await conn.execute(
            "DELETE FROM books WHERE id = $1",
            book_id
        )
        
        return {"message": "Book deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete book: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)

