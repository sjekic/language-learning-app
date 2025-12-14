import asyncpg
import os
from typing import Optional
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from local `.env` / `.env.local` if present.
# In containers the app usually runs from `/app`, so paths like `parents[2]`
# can break (IndexError). Container Apps should primarily use real env vars / secrets.
_HERE = Path(__file__).resolve().parent
load_dotenv(_HERE / ".env", override=False)
load_dotenv(_HERE / ".env.local", override=False)

# Database connection pool
pool: Optional[asyncpg.Pool] = None

async def get_db_connection() -> asyncpg.Pool:
    """Get or create database connection pool"""
    global pool
    
    if pool is None:
        database_url = os.getenv("DATABASE_URL")
        
        if not database_url:
            raise ValueError(
                "DATABASE_URL environment variable is not set. "
                "Please create a .env file with DATABASE_URL or set it in your environment."
            )
        
        # Keep min_size small to avoid creating multiple connections during a cold start.
        # Also set an explicit connect timeout so we fail fast instead of hanging until ACA gateway 504.
        connect_timeout = float(os.getenv("DB_POOL_CONNECT_TIMEOUT_SECONDS", "10"))
        pool = await asyncpg.create_pool(
            database_url,
            min_size=int(os.getenv("DB_POOL_MIN_SIZE", "1")),
            max_size=int(os.getenv("DB_POOL_MAX_SIZE", "10")),
            command_timeout=float(os.getenv("DB_COMMAND_TIMEOUT_SECONDS", "60")),
            timeout=connect_timeout,
        )
    
    return pool

async def close_db_connection():
    """Close database connection pool"""
    global pool
    
    if pool is not None:
        await pool.close()
        pool = None

