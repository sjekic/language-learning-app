import asyncpg
import os
from typing import Optional
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from root .env/.env.local (works no matter where you run from)
_ROOT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(_ROOT_DIR / ".env", override=False)
load_dotenv(_ROOT_DIR / ".env.local", override=False)

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
        
        pool = await asyncpg.create_pool(
            database_url,
            min_size=2,
            max_size=10,
            command_timeout=60
        )
    
    return pool

async def close_db_connection():
    """Close database connection pool"""
    global pool
    
    if pool is not None:
        await pool.close()
        pool = None

