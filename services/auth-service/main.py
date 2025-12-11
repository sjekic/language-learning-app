from fastapi import FastAPI, HTTPException, Depends, status, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
from contextlib import asynccontextmanager

from database import get_db_connection, close_db_connection
from firebase_config import initialize_firebase, verify_firebase_token, get_firebase_user

#asdfhjslfkjsakjhkjsafdsda
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await get_db_connection()
    initialize_firebase()
    yield
    # Shutdown
    await close_db_connection()

app = FastAPI(
    title="Auth Service (Firebase)",
    description="Firebase Authentication integration for language learning app",
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

class FirebaseAuthRequest(BaseModel):
    """Request with Firebase ID token"""
    id_token: str
    display_name: Optional[str] = None

class UserResponse(BaseModel):
    """User information response"""
    id: int
    firebase_uid: str
    email: str
    display_name: Optional[str]
    created_at: str
    updated_at: str

class AuthResponse(BaseModel):
    """Authentication response with user data"""
    user: UserResponse
    message: str

# ==========================================
# Utility Functions
# ==========================================

async def get_or_create_user(firebase_uid: str, email: str, display_name: Optional[str] = None) -> dict:
    """
    Get user from database or create if doesn't exist
    """
    conn = await get_db_connection()
    
    # Check if user exists
    user = await conn.fetchrow(
        "SELECT id, firebase_uid, email, display_name, created_at, updated_at FROM users WHERE firebase_uid = $1",
        firebase_uid
    )
    
    if user:
        return dict(user)
    
    # Create new user
    user = await conn.fetchrow(
        """
        INSERT INTO users (firebase_uid, email, display_name, created_at, updated_at)
        VALUES ($1, $2, $3, NOW(), NOW())
        RETURNING id, firebase_uid, email, display_name, created_at, updated_at
        """,
        firebase_uid,
        email,
        display_name or email.split('@')[0]
    )
    
    return dict(user)

async def verify_auth_header(authorization: str = Header(...)) -> dict:
    """
    Verify Firebase ID token from Authorization header
    Returns Firebase user data
    """
    try:
        # Extract token from "Bearer <token>"
        if not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization header format. Expected 'Bearer <token>'"
            )
        
        id_token = authorization.split(" ")[1]
        
        # Verify with Firebase
        decoded_token = verify_firebase_token(id_token)
        
        return decoded_token
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}"
        )

# ==========================================
# API Endpoints
# ==========================================

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "service": "auth-service (Firebase)",
        "status": "healthy",
        "timestamp": datetime.utcnow(),
        "auth_provider": "Firebase Authentication"
    }

@app.post("/api/auth/verify", response_model=AuthResponse)
async def verify_and_sync_user(request: FirebaseAuthRequest):
    """
    Verify Firebase ID token and sync user with database.
    
    This endpoint:
    1. Verifies the Firebase ID token
    2. Gets user info from Firebase
    3. Creates/updates user in PostgreSQL
    4. Returns user data
    
    Frontend flow:
    1. User signs up/logs in with Firebase SDK
    2. Frontend gets ID token from Firebase
    3. Frontend calls this endpoint with the token
    4. Backend verifies token and syncs user to database
    """
    try:
        # Verify Firebase token
        print(f"🔍 Attempting to verify token (first 20 chars): {request.id_token[:20]}...")
        decoded_token = verify_firebase_token(request.id_token)
        print(f"✅ Token verified successfully for user: {decoded_token.get('email')}")
        
        firebase_uid = decoded_token['uid']
        email = decoded_token.get('email')
        
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email not found in Firebase token"
            )
        
        # Get or create user in database
        display_name = request.display_name or decoded_token.get('name') or email.split('@')[0]
        user = await get_or_create_user(firebase_uid, email, display_name)
        
        return AuthResponse(
            user=UserResponse(
                id=user['id'],
                firebase_uid=user['firebase_uid'],
                email=user['email'],
                display_name=user['display_name'],
                created_at=user['created_at'].isoformat(),
                updated_at=user['updated_at'].isoformat()
            ),
            message="User verified and synchronized"
        )
        
    except ValueError as e:
        print(f"❌ Token verification failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Unexpected error in verify_and_sync_user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to verify user: {str(e)}"
        )

@app.get("/api/auth/me", response_model=UserResponse)
async def get_current_user(firebase_data: dict = Depends(verify_auth_header)):
    """
    Get current authenticated user information
    
    Requires: Authorization header with Firebase ID token
    """
    conn = await get_db_connection()
    
    try:
        firebase_uid = firebase_data['uid']
        
        user = await conn.fetchrow(
            """
            SELECT id, firebase_uid, email, display_name, created_at, updated_at
            FROM users
            WHERE firebase_uid = $1
            """,
            firebase_uid
        )
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found in database. Please call /api/auth/verify first."
            )
        
        return UserResponse(
            id=user['id'],
            firebase_uid=user['firebase_uid'],
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
            detail=f"Failed to fetch user: {str(e)}"
        )

@app.post("/api/auth/token/verify")
async def verify_token_only(firebase_data: dict = Depends(verify_auth_header)):
    """
    Simple token verification endpoint (for other services)
    
    Returns basic user info without database lookup
    """
    return {
        "valid": True,
        "user": {
            "firebase_uid": firebase_data['uid'],
            "email": firebase_data.get('email'),
            "email_verified": firebase_data.get('email_verified', False)
        }
    }

@app.get("/api/auth/firebase-user/{uid}")
async def get_firebase_user_info(
    uid: str,
    firebase_data: dict = Depends(verify_auth_header)
):
    """
    Get Firebase user information (admin only or self)
    
    Requires: Authorization header with Firebase ID token
    """
    # Only allow users to query their own info (unless admin)
    if firebase_data['uid'] != uid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot access other user's information"
        )
    
    try:
        user_info = get_firebase_user(uid)
        return user_info
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )

# ==========================================
# Legacy Compatibility Endpoints
# (for services that haven't been updated yet)
# ==========================================

@app.post("/api/auth/login")
async def login_legacy():
    """
    Legacy endpoint - Firebase handles authentication on client side
    """
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="This endpoint is deprecated. Use Firebase Authentication SDK on the client side, then call /api/auth/verify with the ID token."
    )

@app.post("/api/auth/signup")
async def signup_legacy():
    """
    Legacy endpoint - Firebase handles authentication on client side
    """
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="This endpoint is deprecated. Use Firebase Authentication SDK on the client side, then call /api/auth/verify with the ID token."
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
