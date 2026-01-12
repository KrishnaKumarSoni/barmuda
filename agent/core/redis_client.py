# redis_client.py
import os
import redis.asyncio as redis
from dotenv import load_dotenv

load_dotenv()

# Default to localhost if not set in .env
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

def get_redis_client():
    """Creates and returns a new async Redis client."""
    # We do not use decode_responses=True because LangGraph checkpointers 
    # handle serialization (usually msgpack/json) internally.
    return redis.Redis.from_url(REDIS_URL)

# Create a shared async Redis client (Legacy/Global use)
redis_client = get_redis_client()
