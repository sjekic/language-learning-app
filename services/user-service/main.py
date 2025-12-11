from fastapi import FastAPI, HTTPException, Depends, status, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
from contextlib import asynccontextmanager
import httpx
import os

from database import get_db_connection, close_db_connection

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
    title="User Service",
    description="User profile management microservice",
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

class UserProfile(BaseModel):
    id: int
    email: str
    display_name: Optional[str]
    created_at: str
    updated_at: str

class UpdateProfileRequest(BaseModel):
    display_name: Optional[str] = None

class UserStats(BaseModel):
    total_books: int
    total_words_learned: int
    favorite_books: int
    languages_learning: list[str]

# ==========================================
# Authentication Dependency
# ==========================================

async def verify_token(authorization: str = Header(...)) -> dict:
    """
    Verify JWT token with auth-service
    """
    try:
        # Extract token from "Bearer <token>"
        if not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization header format"
            )
        
        token = authorization.split(" ")[1]
        
        # Verify with auth service
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
    return {"service": "user-service", "status": "healthy", "timestamp": datetime.utcnow()}

@app.get("/api/users/me", response_model=UserProfile)
async def get_current_user_profile(auth_data: dict = Depends(verify_token)):
    """
    Get current user's profile
    """
    conn = await get_db_connection()
    
    try:
        user_id = auth_data['user']['id']
        
        user = await conn.fetchrow(
            """
            SELECT id, email, display_name, created_at, updated_at
            FROM users
            WHERE id = $1
            """,
            user_id
        )
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return UserProfile(
            id=user['id'],
            email=user['email'],
            display_name=user['display_name'],
            created_at=user['created_at'].isoformat(),
            updated_at=user['updated_at'].isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch user profile: {str(e)}"
        )

@app.put("/api/users/me", response_model=UserProfile)
async def update_user_profile(
    request: UpdateProfileRequest,
    auth_data: dict = Depends(verify_token)
):
    """
    Update current user's profile
    """
    conn = await get_db_connection()
    
    try:
        user_id = auth_data['user']['id']
        
        # Build dynamic update query
        updates = []
        values = []
        param_count = 1
        
        if request.display_name is not None:
            updates.append(f"display_name = ${param_count}")
            values.append(request.display_name)
            param_count += 1
        
        if not updates:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields to update"
            )
        
        updates.append("updated_at = NOW()")
        values.append(user_id)
        
        query = f"""
            UPDATE users
            SET {', '.join(updates)}
            WHERE id = ${param_count}
            RETURNING id, email, display_name, created_at, updated_at
        """
        
        user = await conn.fetchrow(query, *values)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return UserProfile(
            id=user['id'],
            email=user['email'],
            display_name=user['display_name'],
            created_at=user['created_at'].isoformat(),
            updated_at=user['updated_at'].isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update user profile: {str(e)}"
        )

@app.get("/api/users/me/stats", response_model=UserStats)
async def get_user_stats(auth_data: dict = Depends(verify_token)):
    """
    Get user statistics (books, vocabulary, etc.)
    """
    conn = await get_db_connection()
    
    try:
        user_id = auth_data['user']['id']
        
        # Get total books
        total_books = await conn.fetchval(
            "SELECT COUNT(*) FROM user_books WHERE user_id = $1",
            user_id
        )
        
        # Get favorite books count
        favorite_books = await conn.fetchval(
            "SELECT COUNT(*) FROM user_books WHERE user_id = $1 AND is_favorite = TRUE",
            user_id
        )
        
        # Get total vocabulary words
        total_words = await conn.fetchval(
            "SELECT COUNT(DISTINCT word) FROM vocabulary WHERE user_id = $1",
            user_id
        )
        
        # Get languages learning
        languages = await conn.fetch(
            """
            SELECT DISTINCT b.language_code
            FROM books b
            JOIN user_books ub ON b.id = ub.book_id
            WHERE ub.user_id = $1
            """,
            user_id
        )
        
        return UserStats(
            total_books=total_books or 0,
            total_words_learned=total_words or 0,
            favorite_books=favorite_books or 0,
            languages_learning=[lang['language_code'] for lang in languages]
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch user stats: {str(e)}"
        )

@app.delete("/api/users/me")
async def delete_user_account(auth_data: dict = Depends(verify_token)):
    """
    Delete current user's account (soft delete or hard delete)
    """
    conn = await get_db_connection()
    
    try:
        user_id = auth_data['user']['id']
        
        # Delete user (CASCADE will handle related records)
        await conn.execute(
            "DELETE FROM users WHERE id = $1",
            user_id
        )
        
        return {"message": "Account deleted successfully"}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete account: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)

